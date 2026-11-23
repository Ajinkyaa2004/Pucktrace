"""users.json from the other server or the backup never takes away a password or admin account.

Run: .venv/bin/python tests/test_users_guard.py
"""
import json, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from backend import users as U                                     # noqa: E402

failures = []


def check(label, condition, detail=""):
    print(("ok   " if condition else "FAIL ") + label + (f"  [{detail}]" if detail and not condition else ""))
    if not condition:
        failures.append(label)


admin = dict(name="Actorix", salt="aa", hash="h1", admin=True, v=3, devices=["d1"])
here = json.dumps({"users": {"actorix": admin, "neha": dict(name="Neha", admin=False, v=1, name_only=True)}}).encode()

# the other server lost its accounts, someone typed "Actorix" on the team site there, and it sent its file
theirs = json.dumps({"users": {"actorix": dict(name="Actorix", admin=False, v=1, name_only=True, devices=["d9"]),
                               "neha": dict(name="Neha", admin=False, v=1, name_only=True),
                               "ravi": dict(name="Ravi", admin=False, v=1, name_only=True)}}).encode()
out = json.loads(U.guard_incoming(theirs, here))["users"]
check("the admin account keeps its password and admin rights", out["actorix"].get("hash") == "h1" and out["actorix"].get("admin"), str(out["actorix"]))
check("the browsers seen on both copies are kept", set(out["actorix"]["devices"]) == {"d1", "d9"}, str(out["actorix"]["devices"]))
check("new name-only accounts from the other server arrive", "ravi" in out)

# a new password set on the other server still arrives
theirs = json.dumps({"users": {"actorix": dict(admin, salt="bb", hash="h2", v=4)}}).encode()
out = json.loads(U.guard_incoming(theirs, here))["users"]
check("a new password from the other server replaces the old one", out["actorix"]["hash"] == "h2")

# the same account with admin dropped but the same password: admin stays
theirs = json.dumps({"users": {"actorix": dict(admin, admin=False)}}).encode()
check("admin rights are not lost by a copy that lacks them", json.loads(U.guard_incoming(theirs, here))["users"]["actorix"]["admin"])

# nothing to protect: the incoming file is used exactly as it came
theirs = json.dumps({"users": {"actorix": admin, "neha": dict(name="Neha", admin=False, v=2, name_only=True)}}).encode()
check("an ordinary copy passes through unchanged", U.guard_incoming(theirs, here) == theirs)

# an account removed on the other server stays removed
theirs = json.dumps({"users": {"actorix": admin}}).encode()
check("a removal on the other server stays a removal", "neha" not in json.loads(U.guard_incoming(theirs, here))["users"])

print("\nALL PASS" if not failures else f"\n{len(failures)} FAILED")
sys.exit(1 if failures else 0)
