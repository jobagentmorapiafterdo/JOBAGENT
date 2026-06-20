#!/usr/bin/env python3
# =============================================================================
# Oil & Gas Job Agent — Multi-Engine Search
# =============================================================================
# Engines (tried in order, first with results wins):
#   1. SerpAPI       — paid, best quality (Google Jobs API)
#   2. Serper.dev    — 2,500 free/month (Google results via API)
#   3. Google CSE    — 100 free/day (Google Custom Search JSON API)
#   4. DDGS          — FREE, unlimited, no key (DuckDuckGo scrape)
#   5. Rigzone       — FREE, direct HTML scrape (O&G job board)
#   6. Indeed        — FREE, via DDGS site: search
#   7. LinkedIn      — FREE, via DDGS site: search
# =============================================================================

import time, json, hashlib, logging, re
from datetime import datetime, timezone
from urllib.parse import urlencode, quote_plus

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────────────
try:
    from config import (
        POSITIONS, COUNTRIES, POSITIONS_WEEK,
        VISA_KEYWORDS, OIL_GAS_KEYWORDS,
        REQUEST_TIMEOUT, SEARCH_DELAY_SECONDS, MAX_RESULTS,
        SERPAPI_KEY, SERPER_API_KEY, GOOGLE_CSE_KEY, GOOGLE_CSE_CX,
    )
except ImportError:
    import os
    POSITIONS = []; COUNTRIES = []; POSITIONS_WEEK = {}
    VISA_KEYWORDS = ["visa sponsorship","sponsor visa","relocation","work permit","expat","international"]
    OIL_GAS_KEYWORDS = ["oil and gas","oil & gas","upstream","downstream","offshore","drilling","refinery","LNG","pipeline","petroleum"]
    REQUEST_TIMEOUT = 20; SEARCH_DELAY_SECONDS = 1.5; MAX_RESULTS = 8
    SERPAPI_KEY = os.getenv("SERPAPI_KEY","")
    SERPER_API_KEY = os.getenv("SERPER_API_KEY","")
    GOOGLE_CSE_KEY = os.getenv("GOOGLE_CSE_KEY","")
    GOOGLE_CSE_CX = os.getenv("GOOGLE_CSE_CX","")

UA = "Mozilla/5.0 (compatible; OilGasJobBot/3.0)"


# ═══════════════════════════════════════════════════════════════════════════
#  SCORING ENGINE
# ═══════════════════════════════════════════════════════════════════════════

def _score(title: str, body: str, position: str, country: str) -> int:
    """Score a result 0-15.  Keep >= 5."""
    t = f"{title} {body}".lower(); pl = position.lower(); cl = country.lower(); s = 0

    if pl in title.lower():                                 s += 4
    elif any(w in title.lower() for w in pl.split()):       s += 2
    if cl in t:                                             s += 2
    if sum(1 for k in OIL_GAS_KEYWORDS if k in t) >= 1:     s += 2
    if sum(1 for k in OIL_GAS_KEYWORDS if k in t) >= 3:     s += 1
    if sum(1 for k in VISA_KEYWORDS if k in t) >= 1:        s += 2
    if sum(1 for k in VISA_KEYWORDS if k in t) >= 2:        s += 1
    js = ["job","vacancy","hiring","position","opening","career","recruit","apply","employment","role","requirement","qualification","salary","benefit","contract","opportunity"]
    if sum(1 for x in js if x in t) >= 2:                    s += 1
    return s


def _clean_title(t: str, fallback: str) -> str:
    t = re.sub(r'^(Job|Hiring|Vacancy|Position|Search)[:\s-]+', '', t, flags=re.I).strip()
    return t[:120] if t and len(t) > 2 else fallback


def _guess_company(text: str) -> str:
    m = re.search(r'(?:at|with|for|by)\s+([A-Z][A-Za-z0-9\s&\'.-]{2,50}?)(?:\s*(?:[-–|/,]|in\b|\.\s|$))', text)
    if m and not m.group(1).lower().startswith(("http","www")): return m.group(1).strip()[:60]
    return "Unknown"


def _make_job(title, body, url, position, country, source):
    return {
        "title": _clean_title(title, position),
        "company": _guess_company(f"{title} {body}"),
        "country": country,
        "position_searched": position,
        "snippet": (body or "")[:500],
        "url": url or "",
        "source": source,
        "score": _score(title, body or "", position, country),
        "found_at": datetime.now(timezone.utc).isoformat(),
    }


def _dedup(jobs):
    seen, uq = set(), []
    for j in jobs:
        h = hashlib.sha256(f"{j.get('url','')}|{j.get('title','')}|{j.get('company','')}".encode()).hexdigest()
        if h not in seen: seen.add(h); uq.append(j)
    return uq


# ═══════════════════════════════════════════════════════════════════════════
#  ENGINE 1 — SERPAPI (Google Jobs API — paid, best)
# ═══════════════════════════════════════════════════════════════════════════

def _serpapi(position, country):
    if not SERPAPI_KEY: return []
    try:
        q = f"{position} oil and gas jobs {country} visa sponsorship"
        r = requests.get("https://serpapi.com/search", params={
            "engine":"google_jobs","q":q,"api_key":SERPAPI_KEY,
            "hl":"en","num":MAX_RESULTS}, timeout=REQUEST_TIMEOUT)
        data = r.json()
        jobs = []
        for item in data.get("jobs_results",[]):
            desc = f"{item.get('description','')} {item.get('snippet','')}"
            score = _score(item.get("title",""), desc, position, country)
            if score < 4: continue
            jobs.append({
                "title": item.get("title",position)[:120],
                "company": item.get("company_name","Unknown"),
                "country":country,"position_searched":position,
                "snippet":desc[:500],
                "url":(item.get("related_links",[{}]) or [{}])[0].get("link",""),
                "source":"SerpAPI","score":score,
                "found_at":datetime.now(timezone.utc).isoformat(),
            })
        jobs.sort(key=lambda j:j["score"],reverse=True)
        return jobs[:MAX_RESULTS]
    except Exception as e:
        logger.debug("SerpAPI: %s",e); return []


# ═══════════════════════════════════════════════════════════════════════════
#  ENGINE 2 — SERPER.DEV (2,500 free/month — Google results)
# ═══════════════════════════════════════════════════════════════════════════

def _serper(position, country):
    if not SERPER_API_KEY: return []
    try:
        q = f'"{position}" "oil and gas" {country} job apply hiring'
        r = requests.post("https://google.serper.dev/search",
            json={"q":q,"num":10,"gl":"us","hl":"en"},
            headers={"X-API-KEY":SERPER_API_KEY}, timeout=REQUEST_TIMEOUT)
        if r.status_code != 200: return []
        data = r.json()
        jobs = []
        for item in data.get("organic",[]):
            t = item.get("title",""); b = item.get("snippet","")
            score = _score(t,b,position,country)
            if score < 4: continue
            jobs.append(_make_job(t,b,item.get("link",""),position,country,"Serper.dev"))
        jobs.sort(key=lambda j:j["score"],reverse=True)
        return jobs[:MAX_RESULTS]
    except Exception as e:
        logger.debug("Serper: %s",e); return []


# ═══════════════════════════════════════════════════════════════════════════
#  ENGINE 3 — GOOGLE CUSTOM SEARCH (100 free/day)
# ═══════════════════════════════════════════════════════════════════════════

def _google_cse(position, country):
    if not GOOGLE_CSE_KEY or not GOOGLE_CSE_CX: return []
    try:
        q = f'"{position}" "oil and gas" {country} job'
        r = requests.get("https://www.googleapis.com/customsearch/v1", params={
            "key":GOOGLE_CSE_KEY,"cx":GOOGLE_CSE_CX,"q":q,"num":MAX_RESULTS,
            "hl":"en","gl":"us"}, timeout=REQUEST_TIMEOUT)
        if r.status_code != 200: return []
        data = r.json()
        jobs = []
        for item in data.get("items",[]):
            t = item.get("title",""); b = item.get("snippet","")
            score = _score(t,b,position,country)
            if score < 4: continue
            jobs.append(_make_job(t,b,item.get("link",""),position,country,"Google CSE"))
        jobs.sort(key=lambda j:j["score"],reverse=True)
        return jobs[:MAX_RESULTS]
    except Exception as e:
        logger.debug("Google CSE: %s",e); return []


# ═══════════════════════════════════════════════════════════════════════════
#  ENGINE 4 — DDGS (DuckDuckGo — FREE, unlimited)
# ═══════════════════════════════════════════════════════════════════════════

def _ddgs(position, country):
    """Multi-query DuckDuckGo search. FREE, unlimited, no key needed."""
    try:
        from ddgs import DDGS
        ddgs = DDGS()
        raw = []

        # Query 1 — broad
        raw += list(ddgs.text(
            f'"{position}" "oil and gas" {country} job apply hiring',
            max_results=6))

        # Query 2 — site-specific
        try:
            raw += list(ddgs.text(
                f'site:indeed.com OR site:rigzone.com OR site:linkedin.com/jobs "{position}" oil gas {country}',
                max_results=6))
        except: pass

        # Query 3 — visa/relocation
        try:
            raw += list(ddgs.text(
                f'"{position}" oil gas {country} "visa sponsorship" OR relocation OR expat',
                max_results=5))
        except: pass

        # Dedup URLs
        seen, uniq = set(), []
        for item in raw:
            u = item.get("href","")
            if u and u not in seen: seen.add(u); uniq.append(item)

        # Score + filter
        jobs = []
        for item in uniq:
            t = item.get("title",""); b = item.get("body","")
            score = _score(t,b,position,country)
            if score >= 4:
                jobs.append(_make_job(t,b,item.get("href",""),position,country,"DDGS"))

        jobs.sort(key=lambda j:j["score"],reverse=True)
        return jobs[:MAX_RESULTS]
    except Exception as e:
        logger.debug("DDGS: %s",e); return []


# ═══════════════════════════════════════════════════════════════════════════
#  ENGINE 5 — RIGZONE (direct HTML scrape — O&G job board)
# ═══════════════════════════════════════════════════════════════════════════

def _rigzone(position, country):
    try:
        q = f'{position} {country}'
        url = f"https://www.rigzone.com/oil/jobs/search/?{urlencode({'q':q,'sort':'relevance'})}"
        r = requests.get(url, timeout=REQUEST_TIMEOUT, headers={"User-Agent":UA})
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        jobs = []
        for card in soup.select("div.job-item, li.job-item, div.job-card, div.search-result"):
            t = card.select_one("h2,h3,h4,.job-title,a.job-link,.title,.job-name")
            c = card.select_one(".company,.company-name,.employer,.org")
            d = card.select_one(".description,.snippet,.summary,p,.job-desc")
            a = card.select_one("a[href]")
            if not t: continue
            title = t.get_text(" ",strip=True)
            company = c.get_text(" ",strip=True) if c else "Unknown"
            desc = d.get_text(" ",strip=True) if d else ""
            href = a.get("href","")
            if href and not href.startswith("http"): href = "https://www.rigzone.com"+href
            score = _score(title, f"{title} {desc}", position, country)
            if score < 4: continue
            jobs.append({
                "title":title[:120],"company":company,"country":country,
                "position_searched":position,"snippet":desc[:500],
                "url":href,"source":"Rigzone","score":score,
                "found_at":datetime.now(timezone.utc).isoformat(),
            })
        jobs.sort(key=lambda j:j["score"],reverse=True)
        return jobs[:4]
    except Exception as e:
        logger.debug("Rigzone: %s",e); return []


# ═══════════════════════════════════════════════════════════════════════════
#  ENGINE 6 — INDEED (via DDGS site: search)
# ═══════════════════════════════════════════════════════════════════════════

def _indeed_via_ddgs(position, country):
    try:
        from ddgs import DDGS
        ddgs = DDGS()
        raw = list(ddgs.text(
            f'site:indeed.com "{position}" oil gas {country} ("visa sponsorship" OR sponsor OR relocation)',
            max_results=5))
        jobs = []
        for item in raw:
            t = item.get("title",""); b = item.get("body","")
            score = _score(t,b,position,country)
            if score >= 4:
                jobs.append(_make_job(t,b,item.get("href",""),position,country,"Indeed"))
        jobs.sort(key=lambda j:j["score"],reverse=True)
        return jobs[:3]
    except Exception as e:
        logger.debug("Indeed: %s",e); return []


# ═══════════════════════════════════════════════════════════════════════════
#  ENGINE 7 — LINKEDIN (via DDGS site: search)
# ═══════════════════════════════════════════════════════════════════════════

def _linkedin_via_ddgs(position, country):
    try:
        from ddgs import DDGS
        ddgs = DDGS()
        raw = list(ddgs.text(
            f'site:linkedin.com/jobs "{position}" oil gas {country} ("visa sponsorship" OR sponsor OR relocation)',
            max_results=5))
        jobs = []
        for item in raw:
            t = item.get("title",""); b = item.get("body","")
            score = _score(t,b,position,country)
            if score >= 4:
                jobs.append(_make_job(t,b,item.get("href",""),position,country,"LinkedIn"))
        jobs.sort(key=lambda j:j["score"],reverse=True)
        return jobs[:3]
    except Exception as e:
        logger.debug("LinkedIn: %s",e); return []


# ═══════════════════════════════════════════════════════════════════════════
#  ORCHESTRATOR — try engines in priority order
# ═══════════════════════════════════════════════════════════════════════════

ENGINES = [
    ("SerpAPI",   _serpapi),          # 1. Paid, best quality
    ("Serper",    _serper),           # 2. 2,500 free/month
    ("GoogleCSE", _google_cse),       # 3. 100 free/day
    ("DDGS",      _ddgs),             # 4. FREE unlimited ← PRIMARY
    ("Rigzone",   _rigzone),          # 5. O&G job board
    ("Indeed",    _indeed_via_ddgs),  # 6. Indeed via DDGS
    ("LinkedIn",  _linkedin_via_ddgs),# 7. LinkedIn via DDGS
]

def _query_all(position, country):
    """Run ALL engines, merge results. DDGS + Rigzone always run."""
    all_jobs = []
    for name, fn in ENGINES:
        try:
            results = fn(position, country)
            if results:
                logger.debug("  %s → %d results", name, len(results))
            all_jobs += results
        except Exception as e:
            logger.debug("  %s → error: %s", name, e)
    return all_jobs


# ═══════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════

class JobSearcher:
    """Multi-engine search: DDGS (free) + SerpAPI + Serper + Google CSE + Rigzone + Indeed + LinkedIn."""

    def __init__(self):
        self.results = []

    def search_all(self, progress_callback=None, positions=None):
        self.results = []
        plist = positions or POSITIONS
        total = len(plist) * len(COUNTRIES)
        n = 0
        for position in plist:
            for country in COUNTRIES:
                n += 1
                if progress_callback: progress_callback(n, total, position, country)
                try:
                    self.results += _query_all(position, country)
                except Exception as e:
                    logger.warning("Fail: %s / %s — %s", position, country, e)
                time.sleep(SEARCH_DELAY_SECONDS)
        self.results = _dedup(self.results)
        logger.info("Done: %d unique results", len(self.results))
        return self.results

    def search_single(self, position, country):
        return _dedup(_query_all(position, country))