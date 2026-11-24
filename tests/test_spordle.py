import asyncio, sys
sys.path.insert(0, ".")
from backend import roster_links as R, lookup
from backend.adapters import spordle as S


def test_message(monkeypatch):
    sp = {R.key("Thunder Bay Kings U16 AAA"): dict(org="thunder-bay-minor-hockey-association", games=3, last="2026-10-22"),
          R.key("Thunder Bay Queens U15 AA"): dict(org=None, games=1, last="2026-10-04")}
    monkeypatch.setattr(R, "links", lambda t: [])
    monkeypatch.setitem(R._cache, "spordle", sp)
    p = lookup.parse_header("[2297697] Thunder Bay Queens U15 AA 0 - 0 South end rangers u15AA | Friendly match | 2026-11-22T23:00:00 | RL:8")
    a = S.Spordle()
    assert a.applies(p, {}, {})
    r = asyncio.run(a.find(p, {}, {}))[0]
    assert r["url"] == "https://page.spordle.com/thunder-bay-minor-hockey-association/schedule"
    assert "Open Thunder Bay Minor Hockey Association → Schedule" in r["message"]
    assert "Sun 22 Nov, 3:00 PM Thunder Bay time" in r["message"]
    assert r["kind"] == "schedule"


def test_one_shared_game_is_not_enough(monkeypatch):
    monkeypatch.setattr(R, "links", lambda t: [])
    monkeypatch.setitem(R._cache, "spordle", {R.key("Westfort Maroons U15 AA"): dict(org=None, games=1, last="2026-10-09")})
    p = lookup.parse_header("[1] Westfort Maroons U15 AA 0 - 0 Someone Else | Friendly match | 2026-11-22T23:00:00 | RL:8")
    assert not S.Spordle().applies(p, {}, {})
