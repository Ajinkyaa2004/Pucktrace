"""ECHL (backend/adapters/echl.py): with the header's time, only the header's day is read.

Run: .venv/bin/python tests/test_echl.py     (no network: pages are faked)
"""
import asyncio, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from backend.adapters import echl as E                           # noqa: E402
from backend import lookup                                       # noqa: E402

failures = []


def check(label, condition, detail=""):
    print(("ok   " if condition else "FAIL ") + label + (f"  [{detail}]" if detail and not condition else ""))
    if not condition:
        failures.append(label)


PAGE = '<title>Savannah Ghost Pirates @ Florida Everblades | ECHL</title> client_code=echl'


def run(header, pages):
    async def fake(url, **kw):
        return pages.get(url)
    E.get_text = fake
    p = lookup.parse_header(header)
    return asyncio.run(E.Echl().find(p, {}, {}))


fri = "https://echl.com/games/2026/11/20/florida-everblades-vs-savannah-ghost-pirates"
sat = "https://echl.com/games/2026/11/21/florida-everblades-vs-savannah-ghost-pirates"
H = "[2197032] Florida Everblades 0 - 0 Savannah Ghost Pirates | East Coast Hockey League | 2026-11-22T03:00:00 | RL:8"

c = run(H, {fri: PAGE, sat: PAGE})
check("Saturday 7 PM ET header (03:00 Moscow Sunday): Saturday's game", [x["url"] for x in c] == [sat], str([x["url"] for x in c]))
c = run(H, {fri: PAGE})
check("Saturday's page not readable: no answer, never Friday's game", c == [], str([x["url"] for x in c]))
c = run("[1] Florida Everblades - Savannah Ghost Pirates | East Coast Hockey League | 2026-11-21", {fri: PAGE})
check("a header without a time still looks at the days around it", [x["url"] for x in c] == [fri], str([x["url"] for x in c]))

print("\nALL PASS" if not failures else f"\n{len(failures)} FAILED")
sys.exit(1 if failures else 0)
