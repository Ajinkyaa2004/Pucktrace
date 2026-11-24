"""Roster links from the RTT sheet (backend/roster_links.py, roster_sources.from_sheet_links).

Run: .venv/bin/python tests/test_roster_links.py      (no network: readers are faked)
"""
import asyncio, json, pathlib, sys, tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from backend import roster_links as L, roster_sources as S      # noqa: E402

failures = []


def check(label, condition, detail=""):
    print(("ok   " if condition else "FAIL ") + label + (f"  [{detail}]" if detail and not condition else ""))
    if not condition:
        failures.append(label)


tmp = pathlib.Path(tempfile.mkdtemp()) / "roster_links.json"
L.FILE = tmp
tmp.write_text(json.dumps({"teams": {
    "buffalo jr sabres 16u aaa": [
        {"url": "https://gamesheetstats.com/seasons/15483/teams/556677/roster", "date": "2026-11-20", "name": "Buffalo Jr. Sabres 16U AAA"},
        {"url": "https://www.eliteprospects.com/team/42154/buffalo-jr-sabres-16u-aaa", "date": "2026-02-01", "name": "x"}],
    "waterloo ravens u18aa": [{"url": "https://www.thehockeyobserver.com/waterloo-ravens-u18aa/", "date": "2026-10-04", "name": "x"}]}}))

check("the same team written another way finds its links", len(L.links("Buffalo Jr Sabres 16U AAA", "2026-11-22")) == 1)
check("last season's link is not offered", all(x["date"] >= "2026-07-01" for x in L.links("Buffalo Jr. Sabres 16U AAA", "2026-11-22")))
check("a team with no link: none", L.links("Nobody 12U", "2026-11-22") == [])

check("proper: numbers and full names", S.proper([dict(number=str(i), name=f"First Last{i}") for i in range(15)]))
check("not proper: names without numbers", not S.proper([dict(number=None, name=f"First Last{i}") for i in range(15)]))
check("not proper: last names only", not S.proper([dict(number=str(i), name=f"Last{i}") for i in range(15)]))


async def fake_gs(sid, tid, date):
    return dict(url=f"https://gamesheetstats.com/seasons/{sid}/teams/{tid}/roster", source="GameSheet", season="2026-27",
                players=[dict(number=str(i), name=f"Player Number{i}", pos="F", birth_year=2010) for i in range(1, 19)],
                team="Buffalo Jr. Sabres", league="", note="GameSheet roster, 18 players")


async def fake_page(url, browser=None):
    return dict(players=[dict(number=str(i), name=f"Raven Skater{i}", pos=None, birth_year=None) for i in range(1, 17)], season=None)

S.gs_roster = fake_gs
from backend import roster_pages as P                             # noqa: E402
P.read = fake_page
out = asyncio.run(S.from_sheet_links("Buffalo Jr. Sabres 16U AAA", "2026-11-22"))
check("a GameSheet team link is read with GameSheet's own reader", out and out[0]["source"] == "GameSheet" and len(out[0]["players"]) == 18, str(out))
r = S.finish(out[0], "Buffalo Jr. Sabres 16U AAA", "2026-11-22") if out else {}
check("an 18-player roster with numbers and names is ready to use", r.get("status") == "verified", str(r.get("status")))
out = asyncio.run(S.from_sheet_links("Waterloo Ravens U18AA", "2026-11-22"))
check("a club page without a season counts as this season's (an analyst used it this season)",
      out and out[0]["season"] == "2026-27" and out[0]["season_shown"] is False, str(out))
check("it says where the link came from", out and "analysts used on 2026-10-04" in out[0]["note"], str(out and out[0]["note"]))

print("\nALL PASS" if not failures else f"\n{len(failures)} FAILED")
sys.exit(1 if failures else 0)
