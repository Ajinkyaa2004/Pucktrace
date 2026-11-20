"""Female World Sport School Challenge (backend/adapters/fwssc.py): the schedule page is read into games.

Run: .venv/bin/python tests/test_fwssc.py     (no network: the page is the sample below)
"""
import asyncio, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from backend.adapters import fwssc as F                          # noqa: E402
from backend import lookup                                       # noqa: E402

failures = []


def check(label, condition, detail=""):
    print(("ok   " if condition else "FAIL ") + label + (f"  [{detail}]" if detail and not condition else ""))
    if not condition:
        failures.append(label)


def row(href, time, home, score, away, rnd):
    return f'''<tr>
                    <td>
                        <a href="{href}">{time}<br /><span class="o50">@</span> HFAC-PCL</a>
                    </td>
                    <td class="center"><strike class="unavailable-link">Watch</strike></td>
                    <td class="right">{home}</td>
                    <td class="center">
                                                    <b>{score}</b>
                                            </td>
                    <td class="left">{away}</td>
                    <td class="right">
                        {rnd}                    </td>
                </tr>'''


def table(day, rows):
    return f'''<div class="table-wrap"><table><thead><tr>
                <th scope="column" class="time-and-place">{day}</th><th scope="column">&nbsp;</th>
                <th scope="column" class="right">Home Team</th><th scope="column" class="vs-or-score">&nbsp;</th>
                <th scope="column" class="left">Away Team</th><th scope="column" class="right">&nbsp;</th>
                </tr></thead><tbody>{"".join(rows)}</tbody></table></div>'''


# rows copied from https://fwssc.bhblazershockey.com/schedule (2026 event)
PAGE = '<div id="schedule">' + table("Thursday, November 12, 2026", [
    row("/schedule/game/26/rink_winnipeg%28r_h_a%29vs_thompson_okanagan_lakers", "10:00 AM", "Rink Winnipeg (RHA)", "6 - 2", "Thompson Okanagan Lakers", "Pool A"),
    row("/schedule/game/32/balmoral_hall_blazers_vs_interlake_lightning", "7:00 PM", "Balmoral Hall Blazers", "2 - 0", "Interlake Lightning", "Pool D"),
]) + table("Friday, November 13, 2026", [
    row("/schedule/game/37/westman_wildcats_vs_central_plains_capitals", "8:15 AM", "Westman Wildcats", "3 - 2", "Central Plains Capitals", "Pool B"),
    row("/schedule/game/48/interlake_lightning_vs_yellowhead_chiefs", "6:15 PM", "Interlake Lightning", "1 - 3", "Yellowhead Chiefs", "Pool D"),
]) + table("Saturday, November 14, 2026", [
    row("/schedule/game/60", "6:45 PM", "", "versus", "", "Skills Competition"),
]) + "</div>"

games = F.parse(PAGE)
check("every game row is read, the skills competition is not", len(games) == 4, str(games))
g = next((x for x in games if x["id"] == "32"), None)
check("date, 24-hour time, teams and score of a game",
      g and g["date"] == "2026-11-12" and g["time"] == "19:00" and g["home"] == "Balmoral Hall Blazers"
      and g["away"] == "Interlake Lightning" and g["score"] == "2-0", str(g))
check("the game link is the report page analysts use",
      g and g["url"] == "https://fwssc.bhblazershockey.com/schedule/game/32/balmoral_hall_blazers_vs_interlake_lightning", str(g))
g = next((x for x in games if x["id"] == "26"), None)
check("an escaped link is unescaped only for html entities (keeps %28)", g and "%28r_h_a%29" in g["url"], str(g))
check("a morning game keeps its morning hour", next(x for x in games if x["id"] == "37")["time"] == "08:15")


def search(header):
    p = lookup.parse_header(header)
    a = F.FWSSC()

    async def fake(url, **kw):
        return PAGE
    F.get_text = fake
    return p, a.applies(p, {}, {}), asyncio.run(a.find(p, {}, {}))


# sheet rows the site was the analyst's report for (header times are Moscow time)
p, ok, c = search("[2] Balmoral Hall Blazers U18 Prep - Interlake Lightning U18 AAA | Female World Sport School Classic | 2026-11-13 04:00:00")
check("the reader is used for the tournament's headers", ok)
best = max(c, key=lambda x: x["confidence"]) if c else {}
check("the header's game is the best match", best.get("url", "").endswith("/game/32/balmoral_hall_blazers_vs_interlake_lightning"), str([(x["url"], x["confidence"]) for x in c]))
check("Winnipeg time is turned into UTC (19:00 CST = 01:00 UTC)", best.get("start_utc") == "2026-11-13T01:00", str(best.get("start_utc")))
p, ok, c = search("[3] Westman Wildcats U18 AAA 0 - 0 Central Plains Capitals U18 AAA | Female World Sport School Classic | 2026-11-13T17:15:00 | RL:8")
best = max(c, key=lambda x: x["confidence"]) if c else {}
check("a second header finds its game", best.get("url", "").endswith("/game/37/westman_wildcats_vs_central_plains_capitals"), str([(x["url"], x["confidence"]) for x in c]))
p, ok, c = search("[4] Westman Wildcats U18 AAA 0 - 0 Central Plains Capitals U18 AAA | Manitoba Female U18 AAA | 2026-11-13T17:15:00 | RL:8")
check("other competitions do not use it", not ok)

print("\nALL PASS" if not failures else f"\n{len(failures)} FAILED")
sys.exit(1 if failures else 0)
