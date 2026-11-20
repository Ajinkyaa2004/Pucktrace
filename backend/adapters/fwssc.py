"""Female World Sport School Challenge (fwssc.bhblazershockey.com): a girls' U18 tournament hosted
by Balmoral Hall School in Winnipeg every November. One page, /schedule, lists every game as a
table row under a table per day ("Thursday, November 12, 2026"): the start time (Winnipeg time),
home team, score, away team and the pool or round. Report (the page analysts use):
https://fwssc.bhblazershockey.com/schedule/game/{id}/{slug}, with the box score and line-ups.

Headers name the event "Female World Sport School Classic"; the teams carry their age group
("Westman Wildcats U18 AAA"), the site does not ("Westman Wildcats")."""
from __future__ import annotations
import datetime, html, re
from ..fetch import get_text
from .base import Adapter, score_candidate, local_to_utc

BASE = "https://fwssc.bhblazershockey.com"
# Winnipeg in November is UTC-6 (two sheet games: 7:00 PM = 04:00 Moscow, 8:15 AM = 17:15 Moscow).
# Some time-zone tables now give Manitoba UTC-5 all year; the tournament is always in November, so
# Regina's fixed UTC-6 is used to stay right whichever table a server has.
TZ = "America/Regina"
LEAGUE = "Female World Sport School Challenge"
TABLE = re.compile(r'<th[^>]*class="time-and-place"[^>]*>\s*([^<]+?)\s*</th>(.*?)</table>', re.S)
ROW = re.compile(r'<tr>(.*?)</tr>', re.S)
CELL = re.compile(r'<td[^>]*>(.*?)</td>', re.S)
LINK = re.compile(r'href="(/schedule/game/(\d+)[^"]*)"[^>]*>\s*(\d{1,2}):(\d{2})\s*([AP]M)', re.I)


def _text(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", s or "")).split("@")[0].strip()


def parse(page: str) -> list[dict]:
    """One dict per game: id, url, date, time (local, 24 h), home, away, score, round."""
    out = []
    for day, body in TABLE.findall(page or ""):
        try:
            date = datetime.datetime.strptime(html.unescape(day).strip(), "%A, %B %d, %Y").date().isoformat()
        except ValueError:
            continue
        for row in ROW.findall(body):
            cells = CELL.findall(row)
            m = LINK.search(row)
            if not m or len(cells) < 5:
                continue
            home, away = " ".join(_text(cells[2]).split()), " ".join(_text(cells[4]).split())
            if not home or not away:                  # skills competition and other non-games
                continue
            hh = int(m.group(3)) % 12 + (12 if m.group(5).upper() == "PM" else 0)
            sc = re.search(r"(\d+)\s*-\s*(\d+)", _text(cells[3]))
            out.append(dict(id=m.group(2), url=BASE + html.unescape(m.group(1)), date=date, time=f"{hh:02d}:{m.group(4)}",
                            home=home, away=away, score=f"{sc.group(1)}-{sc.group(2)}" if sc else None,
                            round=_text(cells[5]) if len(cells) > 5 else ""))
    return out


class FWSSC(Adapter):
    name = "fwssc"
    site = "fwssc.bhblazershockey.com"

    def applies(self, parsed, tm, kb):
        c = parsed["comp"].lower()
        return "world sport school" in c or "fwssc" in c

    async def find(self, parsed, tm, kb):
        page = await get_text(f"{BASE}/schedule", ttl=1800, timeout=30)
        d0 = datetime.date.fromisoformat(parsed["date"])
        near = {(d0 + datetime.timedelta(days=k)).isoformat() for k in (-1, 0, 1)}
        out = []
        for g in parse(page or ""):
            if g["date"] not in near:
                continue
            cand = dict(source=self.name, site=self.site, league=LEAGUE, home=g["home"], away=g["away"], date=g["date"],
                        time=g["time"], score=g["score"], status="final" if g["score"] else None, kind="protocol",
                        adapter=self.name, url=g["url"], start_utc=local_to_utc(g["date"], g["time"], TZ))
            score_candidate(cand, parsed, "U18")
            if min(cand["team_scores"]) >= 0.6:
                out.append(cand)
        return out
