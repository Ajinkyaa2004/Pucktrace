"""Rosters read ahead of time (backend/roster_store.py).

Run: .venv/bin/python tests/test_roster_store.py      (no network: the reader is faked)
"""
import asyncio, datetime, json, pathlib, sys, tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from backend import roster_links as L, roster_store as T, roster_sources as S     # noqa: E402

failures = []


def check(label, condition, detail=""):
    print(("ok   " if condition else "FAIL ") + label + (f"  [{detail}]" if detail and not condition else ""))
    if not condition:
        failures.append(label)


d = pathlib.Path(tempfile.mkdtemp())
L.FILE, T.FILE, T.GAP = d / "roster_links.json", d / "roster_store.json", 0
today = datetime.date.today().isoformat()
L.FILE.write_text(json.dumps({"v": L.VERSION, "teams": {
    "hb detroit 16u aaa": [{"url": "https://gamesheetstats.com/seasons/15477/teams/533730/roster", "date": today, "name": "HB Detroit 16U AAA"}],
    "no numbers 14u": [{"url": "https://club.example/roster", "date": today, "name": "No Numbers 14U"}]}}))
calls = []


async def fake_read(url, date):
    calls.append(url)
    if "gamesheet" in url:
        return dict(url=url, source="GameSheet", season=S.season_label(S.season_start(date)), note="GameSheet roster, 18 players",
                    players=[dict(number=str(i), name=f"Player Name{i}", pos="F", birth_year=2010) for i in range(1, 19)])
    return dict(url=url, source="Roster link on file", season=None, note="club page",
                players=[dict(number=None, name=f"Player Name{i}") for i in range(1, 15)])

S._read_link = fake_read
st = asyncio.run(T.harvest(log=lambda *a: None))
check("every team's link is read once", len(calls) == 2, str(calls))
check("both rosters are stored, one of them proper", st["teams"] == 2 and st["proper"] == 1, str(st))
g = T.get("HB Detroit 16U AAA", today)
check("a stored roster is found by the header's name", g and len(g["players"]) == 18 and g["proper"])
calls.clear()
asyncio.run(T.harvest(log=lambda *a: None))
check("a second pass reads nothing that is still fresh", calls == [], str(calls))
out = asyncio.run(S.from_sheet_links("HB Detroit 16U AAA", today))
check("the roster check answers from the store, without reading the page", calls == [] and out and out[0].get("stored") and len(out[0]["players"]) == 18, str(out))
check("next season the stored roster is not used", T.get("HB Detroit 16U AAA", f"{int(today[:4]) + 2}-01-10") is None)

print("\nALL PASS" if not failures else f"\n{len(failures)} FAILED")
sys.exit(1 if failures else 0)
