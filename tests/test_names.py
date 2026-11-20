"""Team-name matching: a code read from one letter alone is a guess, never a "Found".

Run: .venv/bin/python tests/test_names.py

Came from a wrong report (16 Nov 2026): the header "KHA - Esbjerg IK | Denmark2" was answered with an
Austrian women's game, "Hokejski Klub Siscia v EAC Women Capitals", because KHA was read as K + Hockey
Association (any word starting with K: "Klub") and EAC as E + Athletic Club ("Esbjerg").
"""
import pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from backend.adapters import base as B                            # noqa: E402
from backend import lookup                                        # noqa: E402

failures = []


def check(label, condition, detail=""):
    print(("ok   " if condition else "FAIL ") + label + (f"  [{detail}]" if detail and not condition else ""))
    if not condition:
        failures.append(label)


sim = lambda h, s: B.team_similarity(h, s, "")                    # noqa: E731
s, r = sim("KHA", "Hokejski Klub Siscia")
check("'KHA' against 'Hokejski Klub Siscia' is a one-letter guess, capped", s <= B.ONE_LETTER_CAP and "one letter" in r, f"{s} {r}")
s, r = sim("Esbjerg IK", "EAC Women Capitals")
check("'Esbjerg IK' against 'EAC Women Capitals' likewise", s <= B.ONE_LETTER_CAP, f"{s} {r}")
p = lookup.parse_header("[2200672] KHA 0 - 0 Esbjerg IK | Denmark2 | 2026-11-15T12:45:00 | RL:8")
c = B.score_candidate(dict(home="Hokejski Klub Siscia", away="EAC Women Capitals", date="2026-11-15", url="https://x/1", source="deb-online",
                           league="DEBL 2026/27", start_utc="2026-11-15T09:30"), p)
check("a game where both teams are one-letter guesses is not offered at all", max(c["team_scores"]) <= 0.4, str(c["team_scores"]))
c = B.score_candidate(dict(home="KHA", away="Esbjerg", date="2026-11-15", url="https://x/2", source="sportsadmin", league="Divisionen",
                           start_utc="2026-11-15T09:45"), p)
check("the real game ('KHA' v 'Esbjerg') matches both teams", min(c["team_scores"]) >= 0.85, str(c["team_scores"]) + str(c["reasons"][:2]))
check("'BHC 12U AA' is still 'Boulder HC 12U AA' (the HC is in the name)", sim("Boulder HC 12U AA", "BHC 12U AA")[0] >= 0.95, str(sim("Boulder HC 12U AA", "BHC 12U AA")))
check("'PHA Icemen' is still 'Pittsburgh Icemen' (another word in common)", sim("Pittsburgh Icemen 13U AAA", "PHA Icemen 13UAAA")[0] >= 0.85, str(sim("Pittsburgh Icemen 13U AAA", "PHA Icemen 13UAAA")))
check("'AC Avalanche' is still 'Airdrie Avalanche'", sim("Airdrie Avalanche U15", "AC Avalanche U15")[0] >= 0.85, str(sim("Airdrie Avalanche U15", "AC Avalanche U15")))
check("initials of whole words still count ('PTL Black 14U' = 'Princeton Tiger Lilies Black 14U')", sim("PTL Black 14U", "Princeton Tiger Lilies Black 14U")[0] >= 0.95)
s, r = sim("Culver Academy 16U", "CMA 16u")
check("a code with one team still matched elsewhere stays a candidate, as a guess", 0.6 <= s <= B.ONE_LETTER_CAP, f"{s} {r}")

print()
print("ALL PASS" if not failures else f"{len(failures)} FAILED: " + "; ".join(failures))
sys.exit(1 if failures else 0)
