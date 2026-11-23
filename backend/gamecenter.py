"""The league website's game page for a HockeyTech game report.

A HockeyTech report (lscluster.hockeytech.com/game_reports/official-game-report.php?client_code=X&game_id=N)
has the same game on the league's own site, which analysts often link instead:
    hockeyalberta, AEHL U16 AA  ->  https://www.aehlu16aa.ca/stats/game-center/N
    ohl                         ->  https://chl.ca/ohl/gamecentre/N/
data/gamecenter.json holds, per client and league (as the game list names it), the page address,
learned from the analysts' links in the RTT sheet (where their game number is HockeyTech's).
A league is matched without its season words, so next season and the playoffs keep their site."""
from __future__ import annotations
import json, re
from pathlib import Path

FILE = Path(__file__).resolve().parent.parent / "data" / "gamecenter.json"
REPORT = re.compile(r"hockeytech\.com/game_reports/official-game-report\.php\?.*?client_code=([\w-]+).*?game_id=(\d+)", re.I)
SEASON_WORDS = re.compile(r"\b(\d{2,4}(\s*[-/]\s*\d{2,4})?|regular|season|pre-?season|exhibition|exhib|playoffs?|"
                          r"post-?season|sept?|mar|to|the|\d+)\b", re.I)
_data: dict = {}


def _norm(league: str) -> str:
    return " ".join(SEASON_WORDS.sub(" ", (league or "").lower()).replace("|", " ").split())


def _load() -> dict:
    if not _data:
        try:
            d = json.loads(FILE.read_text(encoding="utf-8"))
        except Exception:
            d = {}
        by = {}
        for key, url in (d.get("leagues") or {}).items():
            cc, lg = key.split("|", 1)
            by.setdefault((cc, _norm(lg)), url)
        _data.update(leagues=by, clients=d.get("clients") or {})
    return _data


def link(report_url: str, league: str = "") -> str | None:
    """The league site's game page for a HockeyTech report, or None when the site is not known."""
    m = REPORT.search(report_url or "")
    if not m:
        return None
    cc, gid = m.group(1).lower(), m.group(2)
    d = _load()
    url = d["leagues"].get((cc, _norm(league))) or d["clients"].get(cc)
    return url.replace("{id}", gid) if url else None


def annotate(obj, _depth: int = 0):
    """Add `game_center` to every result entry (a dict with a HockeyTech report `url`) in a search
    result, in place. Cheap: a dictionary lookup per entry, no network."""
    if _depth > 6:
        return obj
    if isinstance(obj, dict):
        u = obj.get("url")
        if isinstance(u, str) and "hockeytech.com/game_reports" in u and not obj.get("game_center"):
            g = link(u, obj.get("league") or "")
            if g:
                obj["game_center"] = g
        for v in obj.values():
            if isinstance(v, (dict, list)):
                annotate(v, _depth + 1)
    elif isinstance(obj, list):
        for v in obj:
            annotate(v, _depth + 1)
    return obj
