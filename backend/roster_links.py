"""Roster links the analysts used, learned from the RTT sheet.

The Progress sheet has, per game, a roster link for each team (Team 1 Link / Team 2 Link) when
the analyst found one: a GameSheet or EliteProspects team page, a league roster page, the club's
own site. They are the best first place to look when a game has no match report, so every Admin
Apply keeps each team's latest links (screenshots are left out: prnt.sc and the like can't be
read) in data/roster_links.json:

    {"teams": {"<team key>": [{"url": ..., "date": "2026-11-21", "name": "<header name>"}, ...]}}

The team key is the header's team name in lower case without punctuation, so "Buffalo Jr. Sabres
16U AAA" and "Buffalo Jr Sabres 16U AAA" share one entry."""
from __future__ import annotations
import json, re, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILE = ROOT / "data" / "roster_links.json"
IMAGE_HOSTS = re.compile(r"prnt\.sc|prntscr\.com|skrinshoter|ibb\.co|imgur\.com|lightshot|gyazo|snipboard", re.I)
SHOT = re.compile(r"prnt\.sc|skrinshoter|ibb\.co|imgur\.com|lightshot|gyazo|snipboard|drive\.google|docs\.google|"
                  r"dropbox|wetransfer|\.png\b|\.jpe?g\b", re.I)
SPORDLE = re.compile(r"page\.spordle\.com/([\w-]+)/schedule/\d+|pdf\.play\.spordle\.com/game/\d+", re.I)
URL = re.compile(r"https?://[^\s,;\"'<>]+")
KEEP = 3                      # links per team, newest first
VERSION = 5                   # raise when build() changes: servers rebuild the file at startup
_cache: dict = {"mtime": None, "teams": {}}


def _url(u: str) -> str:
    """A link as filed: no final '.', ')' or '/' (the same page written two ways is one link)."""
    u = u.rstrip(".)")
    return u.rstrip("/") if u.count("/") > 3 else u


def key(name: str) -> str:
    return " ".join(re.sub(r"[^\w ]+", " ", (name or "").lower()).split())


def build(path: Path | None = None, log=print) -> dict:
    """Read the Progress sheet and return {team key: [links, newest first]}."""
    from . import sheet, lookup
    teams: dict = {}
    shot_teams: dict = {}
    spordle: dict = {}
    n = shots = 0
    for r in sheet.rows(path or sheet.PROGRESS):
        try:
            p = lookup.parse_header(r["header"] or "")
        except Exception:
            p = None
        if not p or not p.get("date"):
            continue
        # the protocol on Spordle (sites that block automatic reading): both teams' games are there
        sp = SPORDLE.search(str(r.get("link") or ""))
        if sp:
            for t in ("t1", "t2"):
                e = spordle.setdefault(key(p[t]), dict(org=None, games=0, last=p["date"]))
                e["games"] += 1
                e["last"] = max(e["last"], p["date"])
                if sp.group(1) and (not e["org"] or p["date"] >= e.get("org_date", "")):
                    e.update(org=sp.group(1).lower(), org_date=p["date"])
        both = [{_url(u) for u in URL.findall(str(r.get(c) or ""))} for c in ("l1", "l2")]
        for col, t in (("l1", "t1"), ("l2", "t2")):
            for u in URL.findall(str(r.get(col) or "")):
                u = _url(u)
                if u in both[0] and u in both[1]:
                    continue            # the same link pasted for both teams: whose roster it is, is not known
                if SHOT.search(u):
                    shots += 1
                    if IMAGE_HOSTS.search(u):
                        # a roster screenshot: not readable as a page, but the tagger can open it
                        sl = shot_teams.setdefault(key(p[t]), [])
                        if u not in [x["url"] for x in sl]:
                            sl.append(dict(url=u, date=p["date"], name=p[t]))
                    continue
                n += 1
                lst = teams.setdefault(key(p[t]), [])
                hit = next((x for x in lst if x["url"].rstrip("/") == u.rstrip("/")), None)   # with or without a final /
                if hit:
                    hit["date"] = max(hit["date"], p["date"])
                    hit["uses"] += 1
                else:
                    lst.append(dict(url=u, date=p["date"], name=p[t], uses=1))
    # a link filed under several teams belongs to the team it was used for most (a slip in one row
    # gave another team's page); a tie leaves it with none
    owners: dict = {}
    for k, lst in teams.items():
        for x in lst:
            owners.setdefault(x["url"], []).append((x["uses"], k))
    for u, ks in owners.items():
        if len(ks) > 1:
            ks.sort(reverse=True)
            keep = ks[0][1] if ks[0][0] > ks[1][0] else None
            for _, k in ks:
                if k != keep:
                    teams[k] = [x for x in teams[k] if x["url"] != u]
    teams = {k: v for k, v in teams.items() if v}
    for k, lst in teams.items():
        lst.sort(key=lambda x: x["date"], reverse=True)
        del lst[KEEP:]
    for k, lst in shot_teams.items():
        lst.sort(key=lambda x: x["date"], reverse=True)
        del lst[2:]
    log(f"roster links: {n} links for {len(teams)} teams; {shots} screenshots ({len(shot_teams)} teams) kept to open")
    log(f"spordle: {len(spordle)} teams play on Spordle sites, {sum(1 for x in spordle.values() if x['org'])} with their association's page")
    return dict(v=VERSION, built=datetime.datetime.now().isoformat(timespec="seconds"), teams=teams, shots=shot_teams, spordle=spordle)


def save(data: dict) -> None:
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(FILE)


def links(team_name: str, date: str | None = None) -> list[dict]:
    """The analysts' roster links for this team, newest first; with a date, only links used in the
    same season (1 July to 30 June), so last season's page is never offered."""
    try:
        m = FILE.stat().st_mtime
        if m != _cache["mtime"]:
            d = json.loads(FILE.read_text(encoding="utf-8"))
            _cache.update(mtime=m, teams=d.get("teams") or {}, shots=d.get("shots") or {}, spordle=d.get("spordle") or {})
    except Exception:
        return []
    return _season(_cache["teams"].get(key(team_name)) or [], date)


def screenshots(team_name: str, date: str | None = None) -> list[dict]:
    """The analysts' roster screenshots for this team this season, newest first (at most 2)."""
    links(team_name, date)                  # loads the file
    return _season(_cache.get("shots", {}).get(key(team_name)) or [], date)


def _season(lst: list, date: str | None) -> list:
    if date:
        d = datetime.date.fromisoformat(date)
        start = f"{d.year if d.month >= 7 else d.year - 1}-07-01"
        end = f"{int(start[:4]) + 1}-07-01"
        lst = [x for x in lst if start <= x["date"] < end]
    return lst


def stale() -> bool:
    """True when the file is missing or was built by an older build()."""
    try:
        return json.loads(FILE.read_text(encoding="utf-8")).get("v") != VERSION
    except Exception:
        return True


def stats() -> dict:
    try:
        d = json.loads(FILE.read_text(encoding="utf-8"))
        return dict(teams=len(d.get("teams") or {}), built=d.get("built"), v=d.get("v"))
    except Exception as e:
        return dict(teams=0, error=str(e)[:80])


def spordle(team_name: str) -> dict | None:
    """{org: association page name or None, games, last} when the analysts found this team's games
    on Spordle (page.spordle.com / pdf.play.spordle.com)."""
    links(team_name)                        # loads the file
    sp = _cache.get("spordle") or {}
    e = sp.get(key(team_name))
    if not e or e.get("org"):
        return e
    # no association page for this team itself: the association whose page name carries the
    # team's town ("Thunder Bay Queens" -> thunder-bay-minor-hockey-association)
    words = re.findall(r"[a-z]+", team_name.lower())
    best = None
    for org in {x["org"] for x in sp.values() if x.get("org")}:
        parts = org.split("-")
        for n in (3, 2, 1):
            town = words[:n]
            if len(town) == n and parts[:n] == town and (n > 1 or len(town[0]) >= 5):
                if not best or n > best[0]:
                    best = (n, org)
                break
    return dict(e, org=best[1], org_from="name") if best else e
