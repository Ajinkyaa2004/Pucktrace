"""Choosing the game (backend/adapters/__init__.py decide) and the name checks fixed on 21 Nov 2026.

Run: .venv/bin/python tests/test_decide.py     (no network, no game list: the candidates are made here)
"""
import copy, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from backend import lookup                                       # noqa: E402
from backend.adapters import decide                              # noqa: E402
from backend.adapters.base import score_candidate, team_similarity, expand_acronyms   # noqa: E402

failures = []


def check(label, condition, detail=""):
    print(("ok   " if condition else "FAIL ") + label + (f"  [{detail}]" if detail and not condition else ""))
    if not condition:
        failures.append(label)


def cand(parsed, home, away, start_utc, gid, score=None, league="USPHL NCDC"):
    c = dict(source="timetoscore", adapter="timetoscore", site="stats.usphl.timetoscore.com", league=league, home=home, away=away,
             date=start_utc[:10], time=start_utc[11:16], start_utc=start_utc, score=score, status="final" if score else None,
             kind="protocol", url=f"https://stats.usphl.timetoscore.com/oss-scoresheet?game_id={gid}&mode=display")
    score_candidate(c, parsed, "")
    return c


# 1. A weekend series: Friday's game has a score, Saturday's not yet. The header is Saturday's.
#    (header 2235729 got Friday's game; the header's time points at the other one)
p = lookup.parse_header("[2235729] Typhoon Hockey Club NCDC - Florida Surge NCDC | USPHL National Collegiate Development Conference | 2026-11-16 00:10:00")
cs = [cand(p, "Typhoon Hockey Club", "Florida Surge", "2026-11-15T18:10", 26204, "5-3"),
      cand(p, "Typhoon Hockey Club", "Florida Surge", "2026-11-15T21:10", 24750)]
d = decide(p, copy.deepcopy(cs))
check("weekend series: the game at the header's time, not the one that already has a score",
      d["verdict"] != "found" or "24750" in d["best"]["url"], str((d["verdict"], (d["best"] or {}).get("url"))))

p = lookup.parse_header("[2235696] Casper Warbirds NCDC 0 - 0 Minnesota Squatch NCDC | USPHL National Collegiate Development Conference | 2026-11-14T05:00:00 | RL:8")
cs = [cand(p, "Casper Warbirds", "Minnesota Squatch", "2026-11-15T00:00", 23870, "3-4"),
      cand(p, "Casper Warbirds", "Minnesota Squatch", "2026-11-14T00:00", 23869)]
d = decide(p, copy.deepcopy(cs))
check("weekend series with the site's time two hours off: Saturday's game is never chosen for Friday",
      d["verdict"] != "found" or "23869" in d["best"]["url"], str((d["verdict"], (d["best"] or {}).get("url"))))

# 2. A tournament's placeholder copy of a game at the same time: the copy with the result still wins
p = lookup.parse_header("[1] Typhoon Hockey Club NCDC - Florida Surge NCDC | USPHL National Collegiate Development Conference | 2026-11-16 00:10:00")
cs = [cand(p, "Typhoon Hockey Club", "Florida Surge", "2026-11-15T21:10", 111, "5-3"),
      cand(p, "Typhoon Hockey Club", "Florida Surge", "2026-11-15T21:20", 222)]
d = decide(p, copy.deepcopy(cs))
check("a placeholder copy at the same time: the played copy is the game",
      d["verdict"] == "found" and "game_id=111" in d["best"]["url"], str((d["verdict"], (d["best"] or {}).get("url"))))

# 3. League tags are not a club's initials ("ACHA" is not "Aquinas College", 2257956)
check("'ACHA' in a team name is not read as Aquinas College",
      "Aquinas" not in expand_acronyms("Oklahoma State Univ. ACHA 2", "MD3 Aquinas College"))
check("so Oklahoma State is far from Aquinas College", team_similarity("Oklahoma State Univ. ACHA 2", "MD3 Aquinas College")[0] < 0.5,
      str(team_similarity("Oklahoma State Univ. ACHA 2", "MD3 Aquinas College")))

# 4. A spelling on the '_never' list in aliases.json is not used, even when learned earlier
check("Midland University is not Calvin University (learned by a wrong save, now on the never list)",
      team_similarity("Midland University", "MD2 Calvin University")[0] < 0.9,
      str(team_similarity("Midland University", "MD2 Calvin University")))
check("Midland University still matches itself", team_similarity("Midland University", "MD1 Midland University")[0] >= 0.9)

# 5. A header naming a JV team: the varsity game of the pair is never "Found" over the JV game (2297012)
p = lookup.parse_header("[2297012] Providence Catholic Celtics 0 - 0 HS Carmel Catholic Corsairs JV | United States High School, Illinois | 2026-11-21T04:00:00 | RL:8")
cs = [cand(p, "Providence Celtics", "Carmel Corsairs", "2026-11-21T02:30", 2998572, league="IHSHL"),
      cand(p, "Providence Celtics (JV)", "Carmel Corsairs (JV)", "2026-11-21T01:00", 2998721, league="IHSHL")]
d = decide(p, copy.deepcopy(cs))
check("JV header: the varsity game is not the answer",
      not (d["verdict"] == "found" and "2998572" in d["best"]["url"]), str((d["verdict"], (d["best"] or {}).get("url"))))


print("\nALL PASS" if not failures else f"\n{len(failures)} FAILED")
sys.exit(1 if failures else 0)
