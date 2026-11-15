"""RAMP tournament sites (backend/adapters/rampt.py): the page text is read into games.

Run: .venv/bin/python tests/test_rampt.py     (no network: the pages are the samples below)
"""
import asyncio, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from backend.adapters import rampt as R                           # noqa: E402
from backend import lookup                                        # noqa: E402

failures = []


def check(label, condition, detail=""):
    print(("ok   " if condition else "FAIL ") + label + (f"  [{detail}]" if detail and not condition else ""))
    if not condition:
        failures.append(label)


# the front page of hockeyintherockiestournaments.com (one division's menu, shortened)
MENU = ''.join(f'<button aria-controls="assoc-menu-text-2096"><span>{n}</span> <svg></svg></button> <div id="accordion-menu-drawer-{d}">'
               f'<a href="/division/2096/{d}/masterschedule">Schedule</a><a href="/division/2096/{d}/standings">Standings</a></div>'
               for n, d in (("U11 AA", 35656), ("U13 AA", 35657), ("U15 AA", 35658), ("U16 AA", 35659), ("U18 AA", 35660)))
HOME = '<a href="/division/2096/35656/game/view/2099328"><h1>Live Game</h1></a><span class="x">Menu</span>' + MENU
OLD_HOME = '<button aria-controls="assoc-menu-text-812"><span>U16 Red</span></button><button aria-controls="assoc-menu-text-813"><span>U15 Blue</span></button>'
TICKER = "‹\nSUN.\nNOV.\n15\n7:15 a.m.\nU11 AA\n U11 AA Knights\n Sturgeon Sting\n0\n0\nLIVE GAME\nSUN.\nNOV.\n15\n12:15 p.m.\nU16 AA\n PAC Saints\n U16 AA Bow Valley Timberwolves\n0\n0\nLIVE GAME"
ROWS = [["/division/2096/35659/game/view/2099352", TICKER],
        ["/division/2096/35659/game/view/2099346", "LEAGUE GAME\n5:30\nPM\nU16 AA\n6\nRound Robin\n Fri, Nov. 13, 2026 5:30 p.m.\nU16 AA Bow Valley Timberwolves\n\n2 - 6\n\nFinal - SO\n\nCalgary Royals\nSLS Centre - Totem 1\nRESULTS"],
        ["/division/2096/35659/game/view/2099347", "LEAGUE GAME\n7:45\nPM\nU16 AA\n9\nRound Robin\n Fri, Nov. 13, 2026 7:45 p.m.\nPAC Saints\n\n3 - 5\n\nFinal\n\nNorth West Stars\nSLS Centre - Totem 1\nRESULTS"],
        ["/division/2096/35659/game/view/2099348", "LEAGUE GAME\n11:30\nAM\nU16 AA\n18\nRound Robin\n Sat, Nov. 14, 2026 11:30 a.m.\nPAC Saints\n\n3 - 6\n\nFinal\n\nCalgary Royals\nSLS Centre - Totem 2\nRESULTS"],
        ["/division/2096/35660/game/view/2099999", "LEAGUE GAME\n7:45\nPM\nU18 AA\n9\nRound Robin\n Fri, Nov. 13, 2026 7:45 p.m.\nPAC Saints\n\n1 - 0\n\nFinal\n\nNorth West Stars\nRink\nRESULTS"]]

d = R.divisions(HOME)
check("the five divisions are read with their tournament number and name", d.get("35659") == ("2096", "U16 AA") and len(d) == 5 and d["35656"][1] == "U11 AA", str(d))
check("the older menu (tournamentsgurus.com) is still read", R.divisions(OLD_HOME) == {"812": ("0", "U16 Red"), "813": ("0", "U15 Blue")})
g = R.parse_row(*ROWS[2])
check("a row with a short date ('Fri, Nov. 13, 2026 7:45 p.m.') is read",
      g and g["date"] == "2026-11-13" and g["time"] == "19:45" and g["home"] == "PAC Saints" and g["away"] == "North West Stars" and g["score"] == "3-5", str(g))
g = R.parse_row(*ROWS[1])
check("'Final - SO' is not taken for the away team", g and g["away"] == "Calgary Royals" and g["home"] == "U16 AA Bow Valley Timberwolves", str(g))
check("the game ticker at the top of the page is not a game", R.parse_row(*ROWS[0]) is None)
g = R.parse_row("/division/0/812/game/view/1", "Game 12\nFriday, September 4, 2026 7:40 pm\nSemi Final\nWoodbridge Wolfpack\n4 - 2\nFinal\nNJ Rockets\nRink 2")
check("the long date of the older sites is still read", g and g["date"] == "2026-09-04" and g["time"] == "19:40" and g["home"] == "Woodbridge Wolfpack" and g["away"].startswith("New Jersey Rockets"), str(g))
check("month short forms", R.month("Nov") == 11 and R.month("Sept") == 9 and R.month("November") == 11 and R.month("Xyz") is None)
check("a subdomain entry and an own-address entry both give a site",
      R.site_of("eakickoff")["base"] == "https://eakickoff.tournamentsgurus.com"
      and R.site_of({"base": "https://hockeyintherockiestournaments.com/", "tz": "America/Edmonton"}) ==
      dict(base="https://hockeyintherockiestournaments.com", tz="America/Edmonton", name="hockeyintherockiestournaments.com"))

# the whole reader, with the two pages replaced by the samples
asked = []


async def fake_text(url, **kw):
    asked.append(url)
    return HOME


async def fake_page(url, **kw):
    asked.append(url)
    return [r for r in ROWS if "/35659/" in url and "/35659/" in r[0] or "/35660/" in url and "/35660/" in r[0]]


R.get_text, R.browser_page = fake_text, fake_page
HEADER = "[2287723] PAC Saints U16 AA 0 - 0 North West Stars U16 AA | Rockies Tournament | 2026-11-14T04:45:00 | RL:8"
parsed = lookup.parse_header(HEADER)
a = R.RampTournament()
check("the reader takes the 'Rockies Tournament' header", a.applies(parsed, None, {}))
check("and leaves other competitions alone", not a.applies(lookup.parse_header("[1] A 0 - 0 B | USA Hockey 16U | 2026-11-14T04:45:00"), None, {}))
out = asyncio.run(a.find(parsed, None, {}))
urls = [c["url"] for c in out]
check("only the U16 division's schedule is opened", [u for u in asked if "masterschedule" in u] == ["https://hockeyintherockiestournaments.com/division/2096/35659/masterschedule"], str(asked))
check("the analyst's game is among the answers", "https://hockeyintherockiestournaments.com/division/2096/35659/game/view/2099347" in urls, str(urls))
best = max(out, key=lambda c: c.get("confidence", 0)) if out else {}
check("and it is the best one, with both teams matched", best.get("url", "").endswith("/2099347") and min(best.get("team_scores", [0])) >= 0.9, str({k: best.get(k) for k in ("url", "confidence", "team_scores")}))
check("the U18 game of the same two clubs is not offered", not any("/35660/" in u for u in urls))
# 01:45 UTC with a time-zone list that has Alberta on UTC-6 all year (the header says 04:45 Moscow = 01:45 UTC), 02:45 with an older list
check("the start time is turned from Alberta time to UTC", (best.get("start_utc") or "")[:16] in ("2026-11-14T01:45", "2026-11-14T02:45"), str(best.get("start_utc")))

print()
print("ALL PASS" if not failures else f"{len(failures)} FAILED: " + "; ".join(failures))
sys.exit(1 if failures else 0)
