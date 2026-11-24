"""Teams whose games are on Spordle (page.spordle.com association pages, pdf.play.spordle.com match
sheets). Spordle blocks automatic reading (a security checkpoint on every page, and its data
service answers only its own page's queries), so PuckTrace can't find the game itself. When the
analysts found a header team's games on Spordle (RTT sheet, data/roster_links.json "spordle"),
the answer says where to look:

    This game is on Spordle, which PuckTrace can't read. Open Thunder Bay Minor Hockey Association
    -> Schedule and look for Thunder Bay Queens vs South End, Sun 22 Nov, 3:00 PM Thunder Bay time.

with the association's schedule to open and a box for the game number, which becomes the match
sheet link (pdf.play.spordle.com/game/<number>). RSEQ and LHEQ have their own entry (blocked.py)."""
from __future__ import annotations
import re
from .base import Adapter, header_utc
from .blocked import league_for

PDF = "https://pdf.play.spordle.com/game/"
# the association's time zone from its page name (Spordle associations are Canadian)
ZONES = [
    (r"thunder-bay|kenora|dryden|northwestern-ontario|\bhno\b", "America/Toronto", "Thunder Bay"),
    (r"pacific|viaha|pcaha|comox|capital-region|vancouver|island|okanagan|kootenay|\bbc\b|bchockey|cariboo|fraser"
     r"|nanaimo|abbotsford|surrey|chilliwack|juan-de-fuca|jdf|victoria|delta|richmond|burnaby|kelowna|tri-cities"
     r"|prince-george|north-shore|langley|coquitlam|kamloops|seattle|south-valley",
     "America/Vancouver", "Pacific"),
    (r"new-brunswick|nouveau-brunswick|nova-scotia|\bpei\b|prince-edward|moncton|fredericton|saint-john|halifax|maritime",
     "America/Halifax", "Atlantic"),
    (r"newfoundland|\bnl\b|st-john-s", "America/St_Johns", "Newfoundland"),
    (r"manitoba|winnipeg|brandon", "America/Winnipeg", "Winnipeg"),
    (r"saskatchewan|regina|saskatoon", "America/Regina", "Saskatchewan"),
    (r"alberta|calgary|edmonton|red-deer|lethbridge", "America/Edmonton", "Alberta"),
    (r"quebec|qu-bec|montreal|laval|gatineau|sherbrooke|lheq|rseq|feminin|ontario|ottawa|toronto|sudbury|nickel",
     "America/Toronto", "Eastern"),
]


def zone(org: str | None, comp: str = "") -> tuple[str, str] | None:
    hay = f"{org or ''} {comp}".lower().replace(" ", "-")
    for pat, tz, label in ZONES:
        if re.search(pat, hay):
            return tz, label
    return None


def org_name(slug: str) -> str:
    small = {"of", "and", "de", "du", "la", "le", "des", "et"}
    words = slug.replace("-", " ").split()
    up = {"aaa", "aa", "mha", "ha", "u13", "u15", "u18", "pcaha", "viaha", "bc", "pei", "hno"}
    return " ".join(w.upper() if w in up else (w if i and w in small else w.capitalize()) for i, w in enumerate(words))


def local_when(parsed: dict, tz: str, label: str) -> str | None:
    hu = header_utc(parsed)
    if not hu:
        return None
    import datetime
    from zoneinfo import ZoneInfo
    t = hu.replace(tzinfo=datetime.timezone.utc).astimezone(ZoneInfo(tz))
    return f"{t:%a} {t.day} {t:%b}, {t.hour % 12 or 12}:{t:%M} {'AM' if t.hour < 12 else 'PM'} {label} time"


def teams_on_spordle(parsed: dict) -> list[dict]:
    from .. import roster_links
    out = []
    for k in ("t1", "t2"):
        e = roster_links.spordle(parsed.get(k) or "")
        # one shared game with a Spordle team doesn't put a team on Spordle: its association page,
        # or at least two of its games there, does
        if e and (e.get("org") or e.get("games", 0) >= 2):
            out.append(dict(e, team=parsed[k]))
    return out


class Spordle(Adapter):
    name = "spordle"
    site = "page.spordle.com"

    def applies(self, parsed, tm, kb):
        return league_for(parsed) is None and bool(teams_on_spordle(parsed))

    async def find(self, parsed, tm, kb):
        on = teams_on_spordle(parsed)
        org = next((x["org"] for x in on if x.get("org")), None)
        z = zone(org, parsed.get("comp") or "") or zone(None, f"{parsed['t1']} {parsed['t2']}")
        when = local_when(parsed, *z) if z else None
        where = f"{org_name(org)} → Schedule" if org else "the home team's association page on Spordle"
        url = f"https://page.spordle.com/{org}/schedule" if org else "https://page.spordle.com/"
        msg = (f"This game is on Spordle, which PuckTrace can't read. Open {where} and look for "
               f"{parsed['t1']} vs {parsed['t2']}, {when or parsed['date']}.")
        return [dict(source=self.name, adapter=self.name, site="page.spordle.com", league=org_name(org) if org else "Spordle",
                     home=parsed["t1"], away=parsed["t2"], date=parsed["date"], when=when, kind="schedule", url=url,
                     confidence=0.5, team_scores=[0.0, 0.0], blocked="page.spordle.com", pdf=PDF, spordle=True,
                     message=msg, reasons=[msg])]
