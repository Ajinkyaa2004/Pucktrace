"""RAMP InterActive tournament sites, e.g. the Eastern Alliance Kickoff ('EAK Tournament') on
<name>.tournamentsgurus.com, or a tournament on its own address (hockeyintherockiestournaments.com,
'Rockies Tournament'). Pages are Blazor-rendered, so each division's master schedule is read in
headless Chromium. Division names carry the age group (U16 Red, U15 Blue, U16 AA); the game page
/division/<t>/<div>/game/view/<id> is the report. Tournaments: data/rampt_tournaments.json."""
from __future__ import annotations
import asyncio, datetime, json, re
from pathlib import Path
from urllib.parse import urlparse
from ..fetch import get_text, browser_page
from .base import Adapter, score_candidate, days_apart, local_to_utc

DATA = Path(__file__).resolve().parent.parent.parent / "data" / "rampt_tournaments.json"
SCHED = "{base}/division/{tid}/{div}/masterschedule"
DIV_RE = re.compile(r'aria-controls="assoc-menu-text-(\d+)"><span>([^<]+)</span>')
LINK_RE = re.compile(r'/division/(\d+)/(\d+)/masterschedule')
SPAN_RE = re.compile(r'"><span>([^<]+)</span>')
JS = r'''() => { const out = []; const seen = new Set();
  for (const a of document.querySelectorAll("a[href*='/game/view/']")) {
    const href = a.getAttribute('href'); if (seen.has(href)) continue;
    let el = a, txt = '';
    for (let i = 0; i < 7 && el; i++) { el = el.parentElement; if (!el) break; txt = el.innerText || '';
      if (/\d{1,2}:\d{2}\s*[AP]M/i.test(txt) && txt.split('\n').filter(s => s.trim()).length >= 5) break; }
    seen.add(href); out.push([href, txt.slice(0, 600)]); }
  return out; }'''
# 'Friday, September 5, 2025 7:45 pm' and 'Fri, Nov. 13, 2026 7:45 p.m.'
DATE_RE = re.compile(r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*\.?,\s+([A-Z][a-z]+)\.?\s+(\d{1,2}),\s+(\d{4})\s+(\d{1,2}):(\d{2})\s*([ap])\.?m\.?", re.I)
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august", "september",
                                        "october", "november", "december"], 1)}


def month(word: str):
    """'November', 'Nov', 'Sept' -> 11, 11, 9."""
    w = word.lower()
    return MONTHS.get(w) or next((i for m, i in MONTHS.items() if len(w) >= 3 and m.startswith(w)), None)


def site_of(value) -> dict:
    """A tournament's entry: a tournamentsgurus.com subdomain (text), or {"base": address, "tz": time zone}."""
    if isinstance(value, str):
        return dict(base=f"https://{value}.tournamentsgurus.com", tz="America/New_York", name=value)
    base = value["base"].rstrip("/")
    return dict(base=base, tz=value.get("tz") or "America/New_York", name=value.get("name") or urlparse(base).netloc.replace("www.", ""))


def divisions(html: str) -> dict:
    """{division id: (tournament id, division name)} from the site's front page. Each division's
    menu carries its name in a <span> and, below it, a link to its master schedule."""
    out = {}
    for m in LINK_RE.finditer(html or ""):
        tid, div = m.group(1), m.group(2)
        if div in out:
            continue
        names = SPAN_RE.findall(html[max(0, m.start() - 2500):m.start()])
        if names:
            out[div] = (tid, names[-1].strip())
    if not out:                                      # the older menu: the division id is in the button itself
        out = {d: ("0", n.strip()) for d, n in DIV_RE.findall(html or "")}
    return out


def load():
    try:
        return {k: v for k, v in json.loads(DATA.read_text()).items() if not k.startswith("_")}
    except Exception:
        return {}


def parse_row(href: str, text: str):
    m = DATE_RE.search(text or "")
    if not m:
        return None
    mon = month(m.group(1))
    if not mon:
        return None
    h = int(m.group(4)) % 12 + (12 if m.group(6).lower() == "p" else 0)
    date = f"{m.group(3)}-{mon:02d}-{int(m.group(2)):02d}"
    rest = [l.strip() for l in text[m.end():].split("\n") if l.strip()]
    # home is the line just before the score (or 'vs'), away the first team line after it;
    # lines such as 'Consolation Game' or 'Semi Final' come before the home team
    k = next((i for i, l in enumerate(rest) if re.fullmatch(r"\d+\s*-\s*\d+|vs\.?|@", l, re.I)), None)
    if not k:
        return None
    status = re.compile(r"final.*|f/(?:ot|so)|scheduled|in progress|results|.*\bperiod\b.*|\d{1,2}:\d{2}.*", re.I)
    after = [l for l in rest[k + 1:] if not status.fullmatch(l)]
    if not after:
        return None
    sc = re.fullmatch(r"(\d+)\s*-\s*(\d+)", rest[k])
    return dict(href=href, date=date, time=f"{h:02d}:{m.group(5)}", home=_expand(rest[k - 1]), away=_expand(after[0]),
                score=f"{sc.group(1)}-{sc.group(2)}" if sc else None)


def _expand(name: str) -> str:
    """Site short forms the headers spell out: 'NJ Rockets' -> 'New Jersey Rockets NJ'."""
    for short, full in (("NJ", "New Jersey"), ("NY", "New York"), ("LI", "Long Island"), ("CT", "Connecticut"), ("HA", "Hockey Academy")):
        if re.search(rf"\b{short}\b", name):
            name = re.sub(rf"\b{short}\b", full, name) + f" {short}"
    return name


class RampTournament(Adapter):
    name = "rampt"
    site = "tournamentsgurus.com"
    budget_s = 75

    def _site(self, parsed):
        c = parsed["comp"].lower()
        sites = load()
        for words, value in sites.items():
            if all(re.search(r"\b" + re.escape(w) + r"\b", c) for w in words.split()):
                try:
                    return site_of(value)
                except Exception:
                    return None
        # a tournament game filed under a general competition ('Hockey Canada 18U'): the entry's
        # "also" names those competitions, and only games inside its "dates" are looked up there
        for value in sites.values():
            if isinstance(value, dict) and value.get("also") and len(value.get("dates") or []) == 2:
                if value["dates"][0] <= (parsed.get("date") or "") <= value["dates"][1] and any(a in c for a in value["also"]):
                    try:
                        return site_of(value)
                    except Exception:
                        return None
        return None

    def applies(self, parsed, tm, kb):
        return self._site(parsed) is not None

    async def find(self, parsed, tm, kb):
        from ..lookup import tokens
        st = self._site(parsed)
        base, host = st["base"], urlparse(st["base"]).netloc.replace("www.", "")
        home = await get_text(base + "/", ttl=24 * 3600)
        divs = divisions(home)
        ages = {str(a) for a in tokens(parsed["t1"])[1] | tokens(parsed["t2"])[1]}
        pick = {d: v for d, v in divs.items() if not ages or any(re.search(rf"\bU{a}\b|\b{a}U\b", v[1], re.I) for a in ages)}
        # one page at a time: fetch.py's browser semaphore is created at import time and, on
        # Python 3.9 under asyncio.run, fails when two renders wait on it concurrently
        rows = []
        for d, (tid, _) in pick.items():
            rows.append(await browser_page(SCHED.format(base=base, tid=tid, div=d), wait_ms=5000, ttl=3 * 3600, js=JS, light_ok=True))
        out, seen = [], set()
        for d, rs in zip(pick, rows):
            tid, dname = pick[d]
            age = re.search(r"\bU(\d{2})\b", dname, re.I)
            for href, text in rs or []:
                if f"/division/{tid}/{d}/" not in href or href in seen:
                    continue
                g = parse_row(href, text)
                if not g or days_apart(parsed["date"], g["date"]) not in (0, 1):
                    continue
                seen.add(href)
                suffix = f" U{age.group(1)}" if age else ""
                cand = dict(source=self.name, site=host, league=f"{st['name']} {dname}", home=g["home"] + suffix,
                            away=g["away"] + suffix, date=g["date"], score=g["score"], status=None, kind="protocol", adapter=self.name,
                            url=base + href, start_utc=local_to_utc(g["date"], g["time"], st["tz"]))
                score_candidate(cand, parsed, f"U{age.group(1)}" if age else "")
                if min(cand["team_scores"]) >= 0.6:
                    out.append(cand)
        return out
