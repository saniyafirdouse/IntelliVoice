"""
engines/website_engine.py — the college website inside IntelliVoice (2026-10-30).

What it does
  1. FETCH (admin button "Fetch updated data from website", or
     `python database/fetch_website.py`): reads every page of saividya.ac.in
     and every PDF link on it (calendar of events, timetables, exam circulars,
     syllabus, brochures, bus routes, policies, approvals...). Saves them in
     MongoDB:  website_pages (page text)  and  website_documents (PDF links).
     It reports what is new, changed and removed since the last fetch.
  2. ANSWER (no waiting for the website — only the saved copy is used):
       - "Show me the academic calendar" / "exam timetable PDF" -> PDF buttons
       - a topic answer (scholarships, admission, accreditation...) gets the
         matching PDF button, like the bus-route PDF
       - when the database has no answer, the best matching website page is
         used (with a link to that page)

Why saved copies: reading the website during a question would add seconds to
every reply and fail whenever the site is slow. The admin refreshes the copy
whenever the website changes.

The site only opens from a normal internet connection (e.g. the laptop the
backend runs on). Everything here fails softly: a fetch problem never breaks
answering.
"""

import asyncio
import hashlib
import re
import time
from collections import Counter
from datetime import datetime, timezone
from urllib.parse import unquote, urldefrag, urljoin, urlparse

BASE = "https://saividya.ac.in"
START_PAGES = ["/", "/admissions", "/reports", "/public_self_disclosure", "/timetable", "/inst-academics",
               "/examinations", "/exam-circulars", "/ug-scheme-syllabus", "/transport", "/hostel", "/library",
               "/scholarship", "/placement", "/nirf", "/naac", "/nba", "/autonomous", "/academics"]
MAX_PAGES = 300
CONCURRENCY = 6
TIMEOUT_S = 20
USER_AGENT = "IntelliVoice-SVIT/1.0 (college admissions assistant; website copy for answers)"
PAGES, DOCS, META = "website_pages", "website_documents", "website_meta"

_SKIP_EXT = re.compile(r"\.(jpg|jpeg|png|gif|webp|svg|ico|zip|rar|docx?|xlsx?|pptx?|mp4|mp3|css|js)(\?|$)", re.I)
_PDF = re.compile(r"\.pdf(\?|$)", re.I)
_DRIVE = re.compile(r"drive\.google\.com/(file/d/|open\?id=)", re.I)
_GENERIC = {"view", "view details", "details", "download", "click here", "here", "pdf", "brochure", "link",
            "odd semester", "even semester", "1st semester", "open", "read more", "more"}

status = {"running": False, "started_at": None, "finished_at": None, "pages_done": 0, "message": "", "summary": None}
_index = {"loaded": False, "docs": [], "pages": [], "loaded_at": 0}


# ── 1. Fetching ───────────────────────────────────────────────────────────
def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _same_site(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return host in ("saividya.ac.in", "www.saividya.ac.in")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _branch_of_file(name: str) -> str:
    n = name.lower()
    for key, label in (("cse_aiml", "CSE (AI & ML)"), ("aiml", "CSE (AI & ML)"), ("data_science", "CSE (Data Science)"),
                       ("/ds/", "CSE (Data Science)"), ("tt_ds", "CSE (Data Science)"), ("cse", "CSE"),
                       ("ece", "ECE"), ("ise", "ISE"), ("mech", "Mechanical"), ("civil", "Civil"), ("mba", "MBA")):
        if key in n:
            return label
    return ""


def _pdf_title(anchor_text: str, row_text: str, heading: str, url: str) -> str:
    """A readable name for a PDF link ("View Details" alone says nothing)."""
    path = unquote(urlparse(url).path)
    stem = re.sub(r"[_\-]+", " ", path.rsplit("/", 1)[-1].rsplit(".", 1)[0]).strip()
    if "/brochure/" in path:
        return f"{_branch_of_file(path) or stem.upper()} brochure"
    if "/tt_coe/" in path:
        return f"{_branch_of_file(path) or stem.upper()} timetable (odd semester)"
    if path.endswith("/svit_brochure.pdf"):
        return "SVIT brochure (all branches)"
    a = _clean(anchor_text)
    if a and re.fullmatch(r"[\d\s\-–/]+", a) and heading:      # "2024-25" alone -> "Annual accounts 2024-25"
        return f"{_clean(heading)[:80]} {a}"
    if a and a.lower() not in _GENERIC and len(a) >= 6:
        return a[:150]
    row = _clean(row_text)
    for g in sorted(_GENERIC, key=len, reverse=True):
        row = re.sub(rf"\b{re.escape(g)}\b", " ", row, flags=re.I)
    row = _clean(row)
    if 4 <= len(row) <= 120:
        return f"{row} ({a})" if a and a.lower() not in _GENERIC else row
    if heading:
        return f"{_clean(heading)[:80]} — {a or stem}"
    return stem or a or "Document"


_CATEGORIES = [   # (category, words in url / page / title)
    ("transport", ("bus_routes", "transport", "bus route")),
    ("brochure", ("brochure",)),
    ("scholarship", ("scholarship",)),
    ("timetable", ("tt_coe", "time_table", "timetable", "time table")),
    ("calendar", ("calendar", "coe)", "/inst-academics")),
    ("exam", ("exam", "malpractice", "cgpa")),
    ("syllabus", ("syllabus", "scheme")),
    ("admission", ("admission policy", "admission_policy")),
    ("fees", ("refund", "fee structure")),
    ("student_welfare", ("ragging", "grievance", "complaints", "equal_opportunity", "minority", "sc_st", "reservation")),
    ("accreditation", ("naac", "nba")),
    ("approvals", ("aicte", "vtu_", "/vtu/", "autonomous", "ugc")),
    ("nirf", ("nirf",)),
    ("newsletter", ("newsletter",)),
    ("accounts", ("annual_accounts",)),
    ("governing_council", ("proceedings",)),
    ("patents", ("/patents", "patent")),
    ("staff_policy", ("research", "reward", "cas_", "/cas", "pop", "r- score", "r-score", "emoluments", "service_rules", "publication")),
    ("disclosure", ("disclosure", "rti", "idp", "iqac", "regulations", "undertak", "cell")),
]
STAFF_ONLY = {"accounts", "governing_council", "patents", "staff_policy"}


def _category(url: str, page: str, title: str) -> str:
    # the link itself first; the page it sits on only when the link says nothing
    for hay in (f"{unquote(url).lower()} {title.lower()}", page.lower()):
        for name, words in _CATEGORIES:
            if any(w in hay for w in words):
                return name
    return "other"


def _parse(url: str, html: str):
    """(title, text lines, [pdf links], [page links]) for one page."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()
    title = _clean((soup.find("h1").get_text(" ") if soup.find("h1") else "") or (soup.title.string if soup.title else ""))
    title = re.sub(r"^SVIT\s*\|\s*", "", title) or urlparse(url).path
    pdfs, links = [], []
    for a in soup.find_all("a", href=True):
        href = urldefrag(urljoin(url, a["href"].strip()))[0]
        if not href.startswith("http"):
            continue
        if _PDF.search(href) or _DRIVE.search(href):
            anchor = a.get_text(" ")
            row, p = "", a.parent
            for _ in range(3):
                if p is None:
                    break
                row = p.get_text(" ")
                if len(_clean(row)) >= 25:
                    break
                p = p.parent
            heading = ""
            h = a.find_previous(["h1", "h2", "h3", "h4", "h5"])
            if h:
                heading = h.get_text(" ")
            pdfs.append((href, anchor, row if len(_clean(row)) <= 200 else "", heading))
        elif _same_site(href) and not _SKIP_EXT.search(href):
            links.append(href.rstrip("/") or BASE)
    lines = [_clean(t) for t in soup.get_text("\n").split("\n")]
    return title, [l for l in lines if len(l) > 2], pdfs, links


async def crawl(max_pages: int = MAX_PAGES) -> tuple[dict, dict, list]:
    """Reads the website. Returns ({url: page}, {pdf_url: doc}, errors)."""
    import httpx
    queue = [BASE + p if p != "/" else BASE for p in START_PAGES]
    seen, pages, docs, errors = set(), {}, {}, []
    sem = asyncio.Semaphore(CONCURRENCY)
    async with httpx.AsyncClient(timeout=TIMEOUT_S, follow_redirects=True,
                                 headers={"User-Agent": USER_AGENT}) as client:
        async def fetch(u):
            async with sem:
                try:
                    r = await client.get(u)
                    if r.status_code != 200 or "text/html" not in r.headers.get("content-type", ""):
                        if r.status_code != 200:
                            errors.append(f"{u} -> {r.status_code}")
                        return u, None
                    return u, r.text
                except Exception as e:
                    errors.append(f"{u} -> {type(e).__name__}")
                    return u, None

        while queue and len(seen) < max_pages:
            batch = []
            while queue and len(batch) < CONCURRENCY * 2 and len(seen) < max_pages:
                u = queue.pop(0)
                if u in seen:
                    continue
                seen.add(u)
                batch.append(u)
            for u, html in await asyncio.gather(*(fetch(u) for u in batch)):
                if not html:
                    continue
                try:
                    title, lines, pdfs, links = _parse(u, html)
                except Exception as e:
                    errors.append(f"{u} -> parse {type(e).__name__}")
                    continue
                path = urlparse(u).path or "/"
                pages[u] = {"url": u, "path": path, "title": title, "lines": lines}
                for href, anchor, row, heading in pdfs:
                    name = _pdf_title(anchor, row, heading, href)
                    old = docs.get(href)
                    if old is None or (old["page"] == "/" and path != "/" and len(name) > len(old["title"])):
                        cat = _category(href, path, name)
                        docs[href] = {"url": href, "title": name, "page": path, "category": cat,
                                      "audience": "staff" if cat in STAFF_ONLY else "parents"}
                for link in links:
                    if link not in seen:
                        queue.append(link)
            status["pages_done"] = len(pages)
    return pages, docs, errors


def _strip_boilerplate(pages: dict) -> None:
    """Menus and footers repeat on every page: drop lines found on most pages."""
    if not pages:
        return
    counts = Counter(l for p in pages.values() for l in set(p["lines"]))
    limit = max(3, int(len(pages) * 0.4))
    for p in pages.values():
        body = [l for l in p["lines"] if counts[l] < limit]
        p["text"] = "\n".join(body)[:20000]
        p.pop("lines", None)


async def refresh(db) -> dict:
    """Fetch the website and save what changed. Returns a summary for the admin."""
    if status["running"]:
        return {"error": "already running"}
    status.update(running=True, started_at=_now().isoformat(), finished_at=None, pages_done=0,
                  message="Reading the college website…", summary=None)
    started = time.perf_counter()
    try:
        pages, docs, errors = await crawl()
        if len(pages) < 5:
            raise RuntimeError(f"only {len(pages)} pages could be read — is the website reachable from this computer?")
        _strip_boilerplate(pages)
        now = _now()
        summary = {"pages": len(pages), "pdfs": len(docs), "pdfs_for_parents": sum(d["audience"] == "parents" for d in docs.values()),
                   "new_pages": 0, "changed_pages": 0, "removed_pages": 0, "new_pdfs": 0, "removed_pdfs": 0,
                   "new_pdf_titles": [], "errors": errors[:20]}
        old_pages = {d["url"]: d async for d in db[PAGES].find({}, {"url": 1, "hash": 1})}
        for url, p in pages.items():
            h = hashlib.md5((p["title"] + p["text"]).encode("utf-8")).hexdigest()
            doc = {**p, "hash": h, "fetched_at": now}
            if url not in old_pages:
                summary["new_pages"] += 1
                doc["changed_at"] = now
            elif old_pages[url].get("hash") != h:
                summary["changed_pages"] += 1
                doc["changed_at"] = now
            await db[PAGES].update_one({"url": url}, {"$set": doc}, upsert=True)
        gone = [u for u in old_pages if u not in pages]
        if gone:
            await db[PAGES].delete_many({"url": {"$in": gone}})
        summary["removed_pages"] = len(gone)

        old_docs = {d["url"]: d async for d in db[DOCS].find({}, {"url": 1})}
        for url, d in docs.items():
            if url not in old_docs:
                summary["new_pdfs"] += 1
                if d["audience"] == "parents" and len(summary["new_pdf_titles"]) < 15:
                    summary["new_pdf_titles"].append(d["title"])
                d = {**d, "first_seen": now}
            await db[DOCS].update_one({"url": url}, {"$set": {**d, "last_seen": now}}, upsert=True)
        gone = [u for u in old_docs if u not in docs]
        if gone:
            await db[DOCS].delete_many({"url": {"$in": gone}})
        summary["removed_pdfs"] = len(gone)

        summary["seconds"] = round(time.perf_counter() - started, 1)
        summary["finished_at"] = _now().isoformat()
        await db[META].update_one({"_id": "last_fetch"}, {"$set": summary}, upsert=True)
        _index["loaded"] = False                      # answers use the new copy from now on
        status.update(message="Done", summary=summary)
        return summary
    except Exception as e:
        status.update(message=f"Failed: {e}")
        return {"error": str(e)}
    finally:
        status.update(running=False, finished_at=_now().isoformat())


async def last_fetch(db) -> dict | None:
    try:
        doc = await db[META].find_one({"_id": "last_fetch"})
    except Exception:
        return None
    if doc:
        doc.pop("_id", None)
    return doc


# ── 2. Answering from the saved copy ──────────────────────────────────────
async def _load_index(db) -> None:
    if _index["loaded"] and time.monotonic() - _index["loaded_at"] < 600:
        return
    try:
        _index["docs"] = await db[DOCS].find({}, {"_id": 0}).to_list(length=2000)
        _index["pages"] = await db[PAGES].find({}, {"_id": 0, "url": 1, "title": 1, "text": 1}).to_list(length=1000)
    except Exception as e:
        print(f"⚠️  Website copy not available: {type(e).__name__}: {e}")
        _index["docs"], _index["pages"] = [], []
    _index.update(loaded=True, loaded_at=time.monotonic())


_STOP = {"the", "and", "for", "pdf", "show", "send", "give", "get", "can", "please", "document", "documents", "file",
         "link", "download", "copy", "what", "where", "how", "is", "are", "me", "my", "of", "to", "a", "an", "in", "svit",
         "college", "kodi", "chahiye", "ide", "enu", "beku", "want", "need", "see", "open", "have", "you", "this",
         "about", "tell", "with", "from", "there", "any", "list"}
_SYNONYMS = {"calender": "calendar", "events": "calendar", "coe": "calendar", "timetables": "timetable",
             "schedule": "timetable", "examination": "exam", "exams": "exam", "fees": "fee", "syllabi": "syllabus",
             "regulation": "regulations", "anti-ragging": "ragging", "brochures": "brochure", "policies": "policy",
             "approval": "approvals", "aiml": "aiml", "ai": "aiml", "ds": "data", "mechanical": "mech"}
# how each branch shows up in a document's title / file name
_BRANCH_PATTERNS = {
    "CSE": r"\bcse\b(?!\s*\((?:ai|data))(?![_ ]?(?:aiml|data|ds))", "CSE-AIML": r"aiml|ai\s*&\s*ml",
    "CSE-DS": r"data[_ ]?science|\bds\b|tt[_ ]ds", "ECE": r"\bece\b", "ISE": r"\bise\b",
    "Mechanical": r"mech", "Civil": r"civil", "MBA": r"\bmba\b",
}
_BRANCH_WORDS = {"aiml": "CSE-AIML", "cse": "CSE", "ece": "ECE", "ise": "ISE", "mech": "Mechanical",
                 "civil": "Civil", "mba": "MBA", "data": "CSE-DS"}


def _is_branch(d: dict, branch: str) -> bool:
    pat = _BRANCH_PATTERNS.get(branch)
    return bool(pat and re.search(pat, _doc_words(d)))
_BRANCH_SENSITIVE = {"timetable", "brochure"}


def _tokens(text: str) -> list:
    low = (text or "").lower().replace("time table", "timetable").replace("calendar of events", "calendar")
    words = re.findall(r"[a-z0-9]+", low)
    return [_SYNONYMS.get(w, w) for w in words if (len(w) >= 3 or w in ("ai", "ds", "tt")) and w not in _STOP]


def _doc_words(d: dict) -> str:
    return f"{d.get('title', '')} {d.get('category', '')} {unquote(d.get('url', ''))}".lower().replace("_", " ")


def _year(d: dict) -> int:
    ys = [int(y) for y in re.findall(r"20\d\d", f"{d.get('title', '')} {d.get('url', '')}")]
    return max(ys) if ys else 0


async def find_documents(db, query: str, branch: str | None = None, limit: int = 4) -> list:
    """PDFs that match a request like "exam timetable for CSE". Parents' documents first."""
    await _load_index(db)
    words = _tokens(query)
    if not words or not _index["docs"]:
        return []
    want_staff = any(w in words for w in ("patent", "patents", "accounts", "proceedings", "research"))
    if not branch:   # "AIML timetable" names the branch in the words
        branch = next((_BRANCH_WORDS[w] for w in ("aiml", "data", "ece", "ise", "mech", "civil", "mba", "cse")
                       if w in words), None)
    scored = []
    for d in _index["docs"]:
        if d.get("audience") == "staff" and not want_staff:
            continue
        hay = _doc_words(d)
        hits = sum(1 for w in set(words) if w in hay)
        if not hits:
            continue
        score = hits * 2 + (3 if d.get("category") in words else 0)
        if d.get("category") in _BRANCH_SENSITIVE and branch:
            score += 3 if _is_branch(d, branch) else -4
        elif d.get("category") == "brochure" and "svit_brochure" in d.get("url", ""):
            score += 1                                # no branch named: the full brochure first
        scored.append((score, _year(d), d))
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    best = scored[0][0] if scored else 0
    return [_button(d) for s, _, d in scored if s >= max(3, best - 2)][:limit]


# Topic answers that get a PDF button too (category, words that must be in the title, newest only?)
TOPIC_DOCUMENTS = {
    "ask_scholarship_available": ("scholarship", None),
    "ask_scholarship_eligibility": ("scholarship", None),
    "ask_admission_process": ("admission", "admission policy"),
    "ask_important_dates": ("calendar", None),
    "ask_exam_pattern": ("exam", "regulations"),
    "ask_grading_system": ("exam", "cgpa"),
    "ask_curriculum": ("syllabus", None),
    "ask_accreditation": ("accreditation", None),
    "ask_autonomous": ("approvals", "autonomous"),
    "ask_university_affiliation": ("approvals", "vtu"),
    "ask_safety": ("student_welfare", "ragging"),
    "ask_fee_payment": ("fees", "refund"),
    "ask_branch_difference": ("brochure", None),
    "ask_courses_offered": ("brochure", None),
}


async def documents_for_topic(db, intent: str, branch: str | None = None, limit: int = 2) -> list:
    spec = TOPIC_DOCUMENTS.get(intent)
    if not spec:
        return []
    await _load_index(db)
    category, must = spec
    docs = [d for d in _index["docs"] if d.get("category") == category and d.get("audience") != "staff"
            and (not must or must in d.get("title", "").lower() or must in unquote(d.get("url", "")).lower())]
    if category == "brochure":
        branch_docs = [d for d in docs if branch and _is_branch(d, branch)]
        main = [d for d in docs if "svit_brochure" in d.get("url", "")]
        docs = branch_docs + main
    docs.sort(key=_year, reverse=True)
    if category in ("approvals", "admission", "accreditation"):
        docs = docs[:1]                               # only the latest one
    return [_button(d) for d in docs[:limit]]


async def find_page(db, query: str) -> dict | None:
    """The website page that best matches a question the database couldn't answer."""
    await _load_index(db)
    words = set(_tokens(query))
    if len(words) < 1 or not _index["pages"]:
        return None
    best, best_score = None, 0
    for p in _index["pages"]:
        text, title = (p.get("text") or "").lower(), (p.get("title") or "").lower()
        score = sum(3 for w in words if w in title) + sum(min(text.count(w), 3) for w in words)
        distinct = sum(1 for w in words if w in text or w in title)
        if distinct < max(1, min(2, len(words))):
            continue
        if score > best_score:
            best, best_score = p, score
    if not best or best_score < 4:
        return None
    text = best.get("text") or ""
    first = min((text.lower().find(w) for w in words if w in text.lower()), default=0)
    start = max(0, first - 300)
    return {"title": best.get("title"), "url": best.get("url"), "text": text[start:start + 1800]}


def _button(d: dict) -> dict:
    return {"title": d.get("title") or "Document (PDF)", "url": d.get("url")}
