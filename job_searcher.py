# Oil & Gas Job Agent — Search Engine (ddgs API backend — free, fast, single)
import time, hashlib, logging, re
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

from config import (
    POSITIONS, COUNTRIES, TUE_POSITIONS, FRI_POSITIONS,
    VISA_KW, OIL_GAS_KW, DELAY, TIMEOUT,
)


def _score(title, body, position, country):
    t = f"{title} {body}".lower(); s = 0
    pl = position.lower(); cl = country.lower()
    if pl in title.lower(): s += 4
    elif any(w in title.lower() for w in pl.split()): s += 2
    if cl in t: s += 2
    if any(k in t for k in OIL_GAS_KW): s += 2
    if any(k in t for k in VISA_KW): s += 2
    js = ["job","vacancy","hiring","position","career","recruit","apply","employment","role","requirement","salary","contract"]
    if sum(1 for x in js if x in t) >= 2: s += 1
    return s


def _clean_title(t, fb):
    t = re.sub(r'^(Job|Hiring|Vacancy|Position|Search)[:\s-]+', '', t, flags=re.I).strip()
    return t[:120] if t and len(t) > 2 else fb


def _company(text):
    m = re.search(r'(?:at|with|for|by)\s+([A-Z][A-Za-z0-9\s&\'.-]{2,50}?)(?:\s*(?:[-–|/,]|in\b|\.\s|$))', text)
    if m and not m.group(1).lower().startswith(("http","www")):
        return m.group(1).strip()[:60]
    return "Unknown"


def _dedup(jobs):
    seen, uq = set(), []
    for j in jobs:
        h = hashlib.sha256(f"{j.get('url','')}|{j.get('title','')}|{j.get('company','')}".encode()).hexdigest()
        if h not in seen: seen.add(h); uq.append(j)
    return uq


def search_ddgs(position, country):
    """Search DuckDuckGo API (single engine, no spam). Returns 0-8 jobs."""
    try:
        from ddgs import DDGS
        ddgs = DDGS()
        all_raw = []

        # Query 1 — broad
        all_raw += list(ddgs.text(
            f'"{position}" "oil and gas" {country} job apply',
            max_results=5, backend="api"))

        # Query 2 — site-specific
        try:
            all_raw += list(ddgs.text(
                f'site:indeed.com OR site:rigzone.com "{position}" oil gas {country}',
                max_results=5, backend="api"))
        except: pass

        # Query 3 — visa/relocation
        try:
            all_raw += list(ddgs.text(
                f'"{position}" oil gas {country} "visa sponsorship" OR relocation OR expat',
                max_results=4, backend="api"))
        except: pass

        # Dedup URLs
        seen_urls, uniq = set(), []
        for item in all_raw:
            u = item.get("href","")
            if u and u not in seen_urls:
                seen_urls.add(u); uniq.append(item)

        # Score + filter
        jobs = []
        for item in uniq:
            t = item.get("title",""); b = item.get("body","")
            sc = _score(t, b, position, country)
            if sc >= 4:
                jobs.append({
                    "title": _clean_title(t, position),
                    "company": _company(f"{t} {b}"),
                    "country": country,
                    "position_searched": position,
                    "snippet": b[:500],
                    "url": item.get("href",""),
                    "source": "DDGS",
                    "score": sc,
                    "found_at": datetime.now(timezone.utc).isoformat(),
                })

        jobs.sort(key=lambda j: j["score"], reverse=True)
        return jobs[:8]
    except Exception as e:
        logger.debug("DDGS error: %s", e)
        return []


def search_rigzone(position, country):
    """Scrape Rigzone — O&G job board."""
    try:
        import requests
        from bs4 import BeautifulSoup
        from urllib.parse import urlencode
        q = f'{position} {country}'
        u = f"https://www.rigzone.com/oil/jobs/search/?{urlencode({'q':q,'sort':'relevance'})}"
        r = requests.get(u, timeout=TIMEOUT,
            headers={"User-Agent":"Mozilla/5.0"})
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        jobs = []
        for card in soup.select("div.job-item,li.job-item,div.job-card,div.search-result"):
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
            sc = _score(title, f"{title} {desc}", position, country)
            if sc < 3: continue
            jobs.append({
                "title":title[:120],"company":company,"country":country,
                "position_searched":position,"snippet":desc[:500],
                "url":href,"source":"Rigzone","score":sc,
                "found_at":datetime.now(timezone.utc).isoformat()})
        jobs.sort(key=lambda j:j["score"],reverse=True)
        return jobs[:4]
    except: return []


def search_one(position, country):
    """Run all engines for one position+country. Returns deduped jobs."""
    jobs = search_ddgs(position, country)
    jobs += search_rigzone(position, country)
    return _dedup(jobs)


class JobSearcher:
    def __init__(self): self.results = []

    def search_all(self, progress=None, positions=None):
        self.results = []
        plist = positions or POSITIONS
        total = len(plist) * len(COUNTRIES); n = 0
        for p in plist:
            for c in COUNTRIES:
                n += 1
                if progress: progress(n, total, p, c)
                try:
                    self.results += search_one(p, c)
                except Exception as e:
                    logger.warning("Fail: %s / %s — %s", p, c, e)
                time.sleep(DELAY)
        self.results = _dedup(self.results)
        logger.info("Search done: %d unique results", len(self.results))
        return self.results

    def search_single(self, p, c):
        return _dedup(search_one(p, c))
