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
SHOT = re.compile(r"prnt\.sc|skrinshoter|ibb\.co|imgur\.com|lightshot|gyazo|snipboard|drive\.google|docs\.google|"
                  r"dropbox|wetransfer|\.png\b|\.jpe?g\b", re.I)
URL = re.compile(r"https?://[^\s,;\"'<>]+")
KEEP = 3                      # links per team, newest first
VERSION = 3                   # raise when build() changes: servers rebuild the file at startup
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
    n = shots = 0
    for r in sheet.rows(path or sheet.PROGRESS):
        try:
            p = lookup.parse_header(r["header"] or "")
        except Exception:
            p = None
        if not p or not p.get("date"):
            continue
        both = [{_url(u) for u in URL.findall(str(r.get(c) or ""))} for c in ("l1", "l2")]
        for col, t in (("l1", "t1"), ("l2", "t2")):
            for u in URL.findall(str(r.get(col) or "")):
                u = _url(u)
                if u in both[0] and u in both[1]:
                    continue            # the same link pasted for both teams: whose roster it is, is not known
                if SHOT.search(u):
                    shots += 1
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
    log(f"roster links: {n} links for {len(teams)} teams ({shots} screenshots left out)")
    return dict(v=VERSION, built=datetime.datetime.now().isoformat(timespec="seconds"), teams=teams)


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
            _cache.update(mtime=m, teams=json.loads(FILE.read_text(encoding="utf-8")).get("teams") or {})
    except Exception:
        return []
    lst = _cache["teams"].get(key(team_name)) or []
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
