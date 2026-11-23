"""The league website's game page next to a HockeyTech report (backend/gamecenter.py).

Run: .venv/bin/python tests/test_gamecenter.py
"""
import pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from backend import gamecenter as G                              # noqa: E402

failures = []


def check(label, condition, detail=""):
    print(("ok   " if condition else "FAIL ") + label + (f"  [{detail}]" if detail and not condition else ""))
    if not condition:
        failures.append(label)


R = "https://lscluster.hockeytech.com/game_reports/official-game-report.php?lang_id=1&client_code={cc}&game_id={g}"
u = G.link(R.format(cc="hockeyalberta", g=27284), "AEHL U16 AA AEHL U16 AA 2026-27 Regular Season")
check("[2297911] GPAC Storm - Fort Saskatchewan (AEHL U16 AA): aehlu16aa.ca game center",
      u == "https://www.aehlu16aa.ca/stats/game-center/27284", str(u))
u = G.link(R.format(cc="hockeyalberta", g=30001), "AEHL U16 AA AEHL U16 AA 2027 Playoffs")
check("the same league in another season part (playoffs) keeps its site", u == "https://www.aehlu16aa.ca/stats/game-center/30001", str(u))
u = G.link(R.format(cc="hockeyalberta", g=1), "AEHL U15 AA AEHL U15 AA 2026-27 Regular Season")
check("another Alberta league gets its own site", u == "https://www.aehlu15aa.ca/stats/game-center/1", str(u))
check("an Alberta league not learned yet: no guess", G.link(R.format(cc="hockeyalberta", g=1), "Some New League") is None)
check("OHL: chl.ca game centre", G.link(R.format(cc="ohl", g=29224), "") == "https://chl.ca/ohl/gamecentre/29224/")
check("a GameSheet game has none (its link is already the game page)", G.link("https://gamesheetstats.com/seasons/15447/games/3182642") is None)
res = {"auto": {"best": {"url": R.format(cc="whl", g=5), "league": "x"}, "candidates": [{"url": R.format(cc="bchl", g=7)}]}}
G.annotate(res)
check("a search result gets the links added", res["auto"]["best"].get("game_center") == "https://chl.ca/whl/gamecentre/5/"
      and res["auto"]["candidates"][0].get("game_center") == "https://bchl.ca/stats/game-center/7", str(res))

T = "https://stats.blackbear.timetoscore.com/oss-scoresheet?game_id={g}&mode=display"
check("TimeToScore AGHF game 80541: the girls' federation game center",
      G.link(T.format(g=80541), "AGHF 14U Diamond") == "https://atlanticgirlshockeyfederation.com/gamecenter-2526/?game=80541&league=3")
check("TimeToScore THF: tier1hockeyfederation.com", G.link(T.format(g=94943), "THF 16U") == "https://www.tier1hockeyfederation.com/gamecenter-widget/?game=94943&league=5")
check("NGHL Blue division: its own page", "game-center-blue" in (G.link(T.format(g=86980), "NGHL - Blue 19U") or ""))
check("USPHL Premier", G.link("https://stats.usphl.timetoscore.com/oss-scoresheet?game_id=26155&mode=display", "Premier Junior") == "https://usphl.com/premier/game-center/?game_id=26155")
check("a TimeToScore league without a known site: none", G.link("https://stats.caha.timetoscore.com/oss-scoresheet?game_id=1&mode=display", "CAHA 14U AA") is None)

print("\nALL PASS" if not failures else f"\n{len(failures)} FAILED")
sys.exit(1 if failures else 0)
