"""Rosters read ahead of time from the analysts' roster links (RTT sheet).

The office PC goes through every team's roster links of this season (data/roster_links.json), one
page at a time, only while no search or roster job is running, and keeps what it read in
data/roster_store.json:

    {"teams": {"<team key>": {"name": ..., "url": ..., "source": ..., "season": "2026-27",
                              "read": "2026-11-24T12:00", "proper": true,
                              "players": [{"number": "9", "name": "Jakob Estermann", "pos": "F", "birth_year": 2010}]}},
     "pass": {"started": ..., "done": n, "total": n, "finished": ...}}

A team is read again after REFRESH_DAYS (rosters change during the season). A roster check then
answers from the store at once, the live read only for teams not stored yet."""
from __future__ import annotations
import asyncio, datetime, json, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILE = ROOT / "data" / "roster_store.json"
REFRESH_DAYS = 7
GAP = 2.0                     # seconds between pages
STATE = dict(running=False, done=0, total=0, ok=0, started=None, last=None)
_mem: dict = {"mtime": None, "data": {"teams": {}}}


def load() -> dict:
    try:
        m = FILE.stat().st_mtime
        if m != _mem["mtime"]:
            _mem.update(mtime=m, data=json.loads(FILE.read_text(encoding="utf-8")))
    except Exception:
        pass
    return _mem["data"]


def save(d: dict) -> None:
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(FILE)
    _mem.update(mtime=FILE.stat().st_mtime, data=d)


def get(team_name: str, date: str) -> dict | None:
    """The stored roster of this team for the game's season, if one was read."""
    from . import roster_links
    from .roster_sources import season_label, season_start
    r = (load().get("teams") or {}).get(roster_links.key(team_name))
    if r and r.get("season") == season_label(season_start(date)) and r.get("players"):
        return r
    return None


def stats() -> dict:
    t = load().get("teams") or {}
    return dict(teams=len(t), proper=sum(1 for x in t.values() if x.get("proper")),
                players=sum(len(x.get("players") or []) for x in t.values()), **{k: STATE[k] for k in ("running", "done", "total", "ok")})


async def harvest(busy=lambda: False, log=print) -> dict:
    """One pass over every team's roster links of this season; reads only what is missing or older
    than REFRESH_DAYS. Waits while `busy()` (searches first)."""
    from . import roster_links
    from .roster_sources import _read_link, proper, season_label, season_start, _GS_BROWSER
    if STATE["running"]:
        return stats()
    today = datetime.date.today().isoformat()
    cur = season_label(season_start(today))
    data = load()
    data = dict(data, teams=dict(data.get("teams") or {}))
    roster_links.links("x")                                    # load the links file
    teams = roster_links._cache.get("teams") or {}
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=REFRESH_DAYS)).isoformat(timespec="minutes")
    todo = []
    for k, lst in teams.items():
        lst = roster_links._season(lst, today)
        old = data["teams"].get(k)
        if lst and not (old and old.get("season") == cur and (old.get("read") or "") >= cutoff):
            todo.append((k, lst))
    STATE.update(running=True, done=0, ok=0, total=len(todo), started=time.time())
    log(f"roster store: {len(todo)} teams to read")
    try:
        for i, (k, lst) in enumerate(todo):
            while busy():
                await asyncio.sleep(5)
            best = None
            for x in lst:                                      # newest link first; the first proper roster wins
                try:
                    _GS_BROWSER.set(True)
                    r = await asyncio.wait_for(_read_link(x["url"], today), timeout=40)
                except Exception:
                    r = None
                await asyncio.sleep(GAP)
                if not r or not r.get("players"):
                    continue
                cand = dict(name=x["name"], url=r.get("url") or x["url"], link=x["url"], source=r.get("source"),
                            season=r.get("season") or cur, read=datetime.datetime.now().isoformat(timespec="minutes"),
                            proper=proper(r["players"]), players=r["players"][:60], note=r.get("note", ""), used=x["date"])
                if cand["season"] != cur:
                    continue
                if not best or (cand["proper"] and not best["proper"]):
                    best = cand
                if best["proper"]:
                    break
            if best:
                data["teams"][k] = best
                STATE["ok"] += 1
            STATE["done"] = i + 1
            if (i + 1) % 25 == 0 or i + 1 == len(todo):
                save(data)
                log(f"roster store: {i + 1}/{len(todo)} read, {STATE['ok']} rosters")
    finally:
        STATE.update(running=False, last=time.time())
        save(data)
    return stats()
