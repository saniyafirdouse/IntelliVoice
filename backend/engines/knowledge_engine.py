"""
Engine 3 — Knowledge Engine

Takes Engine 2's knowledge_request output directly:
    { "collection": "fees", "filters": {"branch": "CSE"} }

Returns verified data from MongoDB. If the filters are specific enough
to match exactly one document, returns that single document. If the
filters are under-specified and match multiple documents (e.g. "CSE
fee" with no exam/quota given — matches KCET, COMEDK, and Management
entries), returns ALL matching documents so Engine 5 can present the
options honestly instead of guessing one.

2026-10-09 (speed): each collection is kept in memory, so a lookup no
longer waits for a round trip to MongoDB Atlas (~0.8 s measured). The
collections are small (fees: 24 documents). Matching and the "broaden
the search" step work exactly as before — only where the documents come
from changed.
  - The cached copy is refreshed every CACHE_TTL_SECONDS (60 s): an
    edit made in the admin panel shows up within about a minute.
    The admin routes can call invalidate_cache("fees") after saving to
    make it show up immediately.
  - Queries the cache can't answer exactly (operators like $gt, dotted
    field names) and very large collections go to MongoDB as before.
  - USE_CACHE = False turns the cache off completely.
Previous version: knowledge_engine_backup_2026-10-09-speed.py
"""

import asyncio
import json
import os
import re
import time

from database.connection import get_database
from engines.college_profile import profile_knowledge
from engines import rank_predictor

USE_CACHE = True
CACHE_TTL_SECONDS = 60
CACHE_MAX_DOCS = 2000          # larger collections are not cached

_cache = {}                    # collection name -> {"docs": [...], "loaded_at": float, "refreshing": bool}

# ── Offline copy (2026-10-28) ─────────────────────────────────────────────
# Every collection the assistant reads is also saved as a small JSON file in
# database/offline_copy/. If MongoDB Atlas can't be reached (a college or expo
# network that blocks it), answers come from these files instead of
# "I don't have that information". The files refresh themselves whenever the
# database is reachable (and check_demo.py saves all of them at once).
OFFLINE_DIR = os.path.join(os.path.dirname(__file__), "..", "database", "offline_copy")
DB_RETRY_SECONDS = 60          # after a failure, use the offline copy for this long, then try again
_db_down_until = 0.0


def _snapshot_path(name: str) -> str:
    return os.path.join(OFFLINE_DIR, f"{name}.json")


def _save_snapshot(name: str, docs: list) -> None:
    try:
        os.makedirs(OFFLINE_DIR, exist_ok=True)
        text = json.dumps(docs, ensure_ascii=False, default=str, indent=1)
        path = _snapshot_path(name)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                if f.read() == text:
                    return                       # unchanged
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except Exception as e:
        print(f"⚠️  Could not save the offline copy of '{name}': {e}")


def _load_snapshot(name: str):
    try:
        with open(_snapshot_path(name), encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"⚠️  Could not read the offline copy of '{name}': {e}")
        return None


def database_reachable() -> bool:
    """False while the last attempt to reach MongoDB failed (offline copy in use)."""
    return time.monotonic() >= _db_down_until


def _use_offline(name: str) -> list | None:
    docs = _load_snapshot(name)
    if docs is not None:
        _cache[name] = {"docs": docs, "loaded_at": time.monotonic(), "refreshing": False, "offline": True}
    return docs


async def save_offline_copy() -> dict:
    """Saves every collection to database/offline_copy/. Returns {collection: record count}."""
    db = get_database()
    if db is None:
        raise RuntimeError("database not connected")
    counts = {}
    for name in sorted(await db.list_collection_names()):
        if name.startswith("system."):
            continue
        docs = await _load_collection(db, name)
        if docs is None:
            continue                              # too large to keep a copy of
        _save_snapshot(name, docs)
        _cache[name] = {"docs": docs, "loaded_at": time.monotonic(), "refreshing": False}
        counts[name] = len(docs)
    return counts
_locks = {}


def invalidate_cache(collection_name: str | None = None) -> None:
    """Forget the cached copy (one collection, or all) — the next lookup reloads it."""
    if collection_name is None:
        _cache.clear()
    else:
        _cache.pop(collection_name, None)


async def _load_collection(db, name: str):
    docs = await db[name].find({}).to_list(length=CACHE_MAX_DOCS + 1)
    if len(docs) > CACHE_MAX_DOCS:
        return None
    for doc in docs:
        doc["_id"] = str(doc["_id"])
    return docs


async def _refresh(db, name: str) -> None:
    global _db_down_until
    if not database_reachable():
        # The database failed a moment ago: don't wait 5 s again, use the offline copy.
        if _use_offline(name) is None and name in _cache:
            _cache[name]["refreshing"] = False
        return
    try:
        docs = await _load_collection(db, name)
        if docs is None:
            _cache.pop(name, None)
        else:
            _cache[name] = {"docs": docs, "loaded_at": time.monotonic(), "refreshing": False}
            _save_snapshot(name, docs)
    except Exception as e:
        print(f"⚠️  Knowledge cache refresh failed for '{name}': {type(e).__name__} — using the offline copy")
        _db_down_until = time.monotonic() + DB_RETRY_SECONDS
        if _use_offline(name) is None and name in _cache:
            _cache[name]["refreshing"] = False


async def _cached_docs(db, name: str):
    """All documents of a collection from memory, or None if it can't be cached."""
    entry = _cache.get(name)
    if entry is not None:
        if time.monotonic() - entry["loaded_at"] > CACHE_TTL_SECONDS and not entry["refreshing"]:
            # Serve the current copy now, refresh in the background.
            entry["refreshing"] = True
            asyncio.create_task(_refresh(db, name))
        return entry["docs"]
    lock = _locks.setdefault(name, asyncio.Lock())
    async with lock:
        if name not in _cache:
            await _refresh(db, name)
        entry = _cache.get(name)
        return entry["docs"] if entry else None


def _cacheable(query: dict) -> bool:
    return all("." not in k and not k.startswith("$") and not isinstance(v, dict)
               for k, v in query.items())


def _field_matches(value, wanted) -> bool:
    # MongoDB equality: same value, or the value is a list containing it.
    return value == wanted or (isinstance(value, list) and wanted in value)


async def _find(db, collection_name: str, query: dict, limit: int = 10) -> list:
    """Same result as db[collection].find(query).limit(limit), from memory when possible."""
    if USE_CACHE and _cacheable(query):
        docs = await _cached_docs(db, collection_name)
        if docs is not None:
            matches = [dict(d) for d in docs
                       if all(_field_matches(d.get(k), v) for k, v in query.items())]
            return matches[:limit]
    try:
        if not database_reachable():
            raise ConnectionError("database unreachable (offline copy in use)")
        cursor = db[collection_name].find(query).limit(limit)
        documents = await cursor.to_list(length=limit)
    except Exception:
        # Offline copy, matched the simple way (only plain field = value filters).
        docs = _load_snapshot(collection_name)
        if docs is None:
            raise
        simple = {k: v for k, v in query.items() if not k.startswith("$") and not isinstance(v, dict)}
        return [dict(d) for d in docs if all(_field_matches(d.get(k), v) for k, v in simple.items())][:limit]
    for doc in documents:
        doc["_id"] = str(doc["_id"])
    return documents


async def _drop_unknown_fields(db, collection_name: str, query: dict) -> dict:
    """
    2026-10-13: ignore filters on fields that NO record in this collection has.
    E.g. "hostel for first-year students" sends {"year": "1st Year", ...} to
    the hostel collection, which has no "year" field at all — such a filter
    can never match, so it used to turn a good question into "not found".
    Filters on fields the collection does have still apply as before.
    """
    if not query or not USE_CACHE or not _cacheable(query):
        return query
    docs = await _cached_docs(db, collection_name)
    if not docs:
        return query
    known = set().union(*(d.keys() for d in docs))
    return {k: v for k, v in query.items() if k in known}


async def retrieve_knowledge(collection_name: str, filters: dict) -> dict:
    if not collection_name:
        return {"found": False, "reason": "no_knowledge_needed", "data": None}

    db = get_database()
    if db is None:
        return {"found": False, "reason": "database_not_connected", "data": None}

    query = {k: v for k, v in (filters or {}).items() if v is not None}

    try:
        query = await _drop_unknown_fields(db, collection_name, query)
        documents = await _find(db, collection_name, query)

        if len(documents) == 1:
            return {"found": True, "match_type": "single", "data": documents[0], "query_used": query}

        if len(documents) > 1:
            return {
                "found": True,
                "match_type": "multiple",
                "data": documents,
                "count": len(documents),
                "query_used": query,
                "note": "Multiple options match this query — present all of them, do not pick one"
            }

        if len(query) > 1:
            broader_query = dict(list(query.items())[:1])
            documents = await _find(db, collection_name, broader_query)

            if len(documents) == 1:
                return {"found": True, "match_type": "single", "data": documents[0], "query_used": broader_query, "note": "broadened_search"}
            if len(documents) > 1:
                return {"found": True, "match_type": "multiple", "data": documents, "count": len(documents), "query_used": broader_query, "note": "broadened_search"}

        return {"found": False, "reason": "no_matching_document", "query_used": query}

    except Exception as e:
        return {"found": False, "reason": "database_error", "error": str(e), "query_used": query}


# Questions that get the rank predictor when the user gave a rank.
RANK_INTENTS = {"ask_rank_prediction", "ask_cutoff", "ask_seat_availability", "ask_branch_recommendation"}
# Questions about ISE that get the "merged into CSE" answer.
ISE_MERGED_INTENTS = {"ask_fees_branch", "ask_cutoff", "ask_seat_availability"}


# ── People and faculty lists (2026-10-29) ─────────────────────────────────
# Names come from the faculty_members collection (every department's teachers,
# "Name — Designation; ...") and the leadership fields of the faculty record
# (principal, vice principal, deans, HODs, section heads, trustees...).
_TITLES = {"dr", "prof", "mr", "mrs", "ms", "sri", "shri", "smt", "miss"}
_PERSON_RE = re.compile(r"(?:Dr|Prof|Mr|Mrs|Ms|Sri|Shri|Smt)\.?\s+[A-Z][\w.]*(?:\s+[A-Z][\w.]*)*")
_DEPT_WORDS = {"Mathematics": ("math", "maths", "mathematics"), "Physics": ("physics",),
               "Chemistry": ("chemistry",), "MBA": ("mba", "business administration")}
_people_index = {"key": None, "people": []}


def _name_words(name: str) -> list:
    words = re.sub(r"[^a-z\s]", " ", name.lower().replace(".", " ")).split()
    return [w for w in words if w not in _TITLES]


def _name_tokens(name: str) -> list:
    return [w for w in _name_words(name) if len(w) >= 3]


def _initials(name: str) -> list:
    # "Dr. Manjunath T N" -> ["t", "n"]: tells two people with the same first name apart
    return [w for w in _name_words(name) if len(w) <= 2]


def _token_hit(token: str, words: set) -> bool:
    if token in words:
        return True
    # "Manjunath" ~ "Manjunatha", "Shantakumar" ~ "Shantakumara"
    # (only for long names, so "Ganesha Chaturthi" never matches "Prof. Ganesh C")
    return len(token) >= 7 and any(len(w) >= 7 and (w.startswith(token) or token.startswith(w)) for w in words)


async def _build_people_index():
    db = get_database()
    if db is None:
        return []
    members = await _cached_docs(db, "faculty_members") or []
    leaders = await _cached_docs(db, "faculty") or []
    key = (id(members), id(leaders), len(members), len(leaders))
    if _people_index["key"] == key:
        return _people_index["people"]
    people = {}

    def put(name, role):
        name = name.strip().rstrip(".,;")
        toks = _name_tokens(name)
        if not toks:
            return
        # the key keeps the initials, so "Manjunath T N" and "Manjunath S" stay two people
        key = " ".join(sorted(_name_words(name)))
        entry = people.setdefault(key, {"name": name, "tokens": toks, "initials": _initials(name), "roles": []})
        if role and role not in entry["roles"]:
            entry["roles"].append(role)

    for doc in members:
        dept = doc.get("department") or doc.get("branch") or ""
        for item in str(doc.get("faculty") or "").split(";"):
            if "—" in item:
                name, desig = item.split("—", 1)
                put(name, f"{desig.strip()}, {dept}")
    for doc in leaders:
        for field, value in doc.items():
            if field.startswith("_") or not isinstance(value, str):
                continue
            # split into sentences, but "Dr. A M Padma Reddy" is not a sentence end
            hidden = re.sub(r"(?<![A-Za-z])(Dr|Prof|Mr|Mrs|Ms|Sri|Shri|Smt|Govt|[A-Z])\.(?=\s)", r"\1§", value)
            for part in (p.replace("§", ".") for p in re.split(r";|\.\s", hidden)):
                for m in _PERSON_RE.finditer(part):
                    put(m.group(), f"{field.replace('_', ' ')}: {part.strip()[:220]}")
    _people_index.update(key=key, people=list(people.values()))
    return _people_index["people"]


async def find_people(query: str) -> list:
    """People named in the question: [{"name", "roles", "match": "full" | "partial"}]."""
    words = set(re.sub(r"[^a-z\s]", " ", (query or "").lower()).split())
    if not words:
        return []
    found = []
    for p in await _build_people_index():
        hits = sum(1 for t in p["tokens"] if _token_hit(t, words))
        if not hits:
            continue
        full = hits == len(p["tokens"]) and (len(p["tokens"]) >= 2 or len(p["tokens"][0]) >= 6)
        inits = p.get("initials") or []
        found.append({"name": p["name"], "roles": p["roles"], "match": "full" if full else "partial", "hits": hits,
                      "initials_ok": bool(inits) and all(i in words for i in inits)})
    # "Who is T G Manjunatha?" names the initials: keep only the people they fit
    if any(p["match"] == "full" and p["initials_ok"] for p in found):
        found = [p for p in found if p["match"] == "full" and p["initials_ok"]]
    found.sort(key=lambda p: (p["match"] != "full", -p["hits"]))
    for p in found:
        p.pop("initials_ok", None)
    return found[:6]


async def _faculty_list_knowledge(intelligence_result: dict) -> dict:
    entities = intelligence_result.get("entities") or {}
    branch = entities.get("branch")
    if not branch:
        low = (intelligence_result.get("query") or "").lower()
        branch = next((b for b, ws in _DEPT_WORDS.items() if any(re.search(rf"\b{w}\b", low) for w in ws)), None)
    if branch:
        result = await retrieve_knowledge("faculty_members", {"branch": branch})
        if result.get("found"):
            return result
    # No department named: the number of teachers per department and the HODs.
    db = get_database()
    docs = await _cached_docs(db, "faculty") if db is not None else None
    if docs:
        d = docs[0]
        return {"found": True, "match_type": "single", "query_used": {"summary": "faculty"},
                "data": {k: d[k] for k in ("faculty_strength", "heads_of_departments", "principal", "vice_principal") if k in d},
                "note": "No department was named: give the totals and offer to list a department's faculty."}
    return {"found": False, "reason": "no_matching_document", "query_used": {}}


# ── Bus routes and stops (2026-10-29) ─────────────────────────────────────
# The transport record has one text per route ("Route 8 — driver ..., staff
# coordinator .... Stops and morning pick-up times: Kogilu Cross 7:30, ...").
# Here each route is split into its stops once, so "Is there a bus from
# Yelahanka?" is answered from the exact stops and times — not by the AI
# reading nine long paragraphs. Any place, any route number, works the same way.
TRANSPORT_INTENT = "ask_transport_routes"
BUS_ROUTES_PDF = "https://saividya.ac.in/assets/pdf/transport/bus_routes_2026_2027.pdf"
_ROUTE_HEAD = re.compile(r"Route\s+(\d+)\s*[—–-]\s*driver\s+(.+?),\s*staff coordinator\s+(.+?)\.\s*Stops", re.I)
_ROUTE_ASKED = re.compile(r"\broute\s*(?:no\.?|number|num)?\s*(\d{1,2})\b", re.I)
# Words that are part of many stop names, so they never identify a place on their own.
_STOP_GENERIC = {
    "cross", "circle", "road", "main", "stop", "station", "layout", "gate", "temple", "college",
    "hospital", "junction", "nagar", "nagara", "block", "phase", "town", "complex", "bridge",
    "entrance", "post", "office", "railway", "mile", "park", "quarters", "tank", "water", "ring",
    "tech", "mall", "more", "court", "factory", "studio", "campus", "svit", "eye", "dhaba", "machine",
    "samadhi", "choultry", "government", "old", "new", "bus", "the",
}
# Common question words — never compared with stop names.
_QUERY_COMMON = {
    "what", "which", "there", "where", "from", "time", "when", "does", "will", "have", "near", "area",
    "place", "goes", "going", "come", "comes", "coming", "reach", "reaches", "pick", "pickup", "drop",
    "morning", "evening", "route", "routes", "buses", "college", "available", "driver", "number",
    "phone", "coordinator", "staff", "timing", "timings", "start", "starts", "fees", "campus",
    "please", "tell", "about", "details", "transport", "facility", "stop", "stops", "location",
}
_bus_index = {"key": None, "routes": []}


def _words(text: str) -> list:
    return re.sub(r"[^a-z0-9\s]", " ", (text or "").lower()).split()


def _parse_route(number: int, text: str) -> dict:
    head = _ROUTE_HEAD.search(text or "")
    route = {"route": number, "driver": head.group(2).strip() if head else None,
             "staff_coordinator": head.group(3).strip() if head else None, "stops": [], "reaches_campus": None}
    body = (text or "").split("times:", 1)[-1].strip().rstrip(".")
    for item in body.split(", "):
        m = re.match(r"(.+?)\s+(\d{1,2}[:.]\d{2})\s*(am|pm)?\s*$", item.strip())
        if not m:
            continue
        name, at = m.group(1).strip(), m.group(2).replace(".", ":") + " am"
        if name.lower().startswith("svit campus"):
            route["reaches_campus"] = at
            continue
        tokens = [w for w in _words(name) if len(w) >= 4 and w not in _STOP_GENERIC and not w.isdigit()]
        route["stops"].append({"stop": name, "pickup_time": at, "tokens": tokens,
                               "phrase": " ".join(_words(re.sub(r"\(.*?\)", "", name.split(": ")[-1])))})
    return route


async def _bus_routes() -> tuple:
    """(transport record, [parsed routes]) — parsed once per data load."""
    db = get_database()
    docs = (await _cached_docs(db, "transport") or []) if db is not None else []
    doc = next((d for d in docs if any(k.startswith("route_") and k[6:].isdigit() for k in d)), None)
    if doc is None:
        return (docs[0] if docs else None), []
    key = (id(doc), len(docs))
    if _bus_index["key"] != key:
        routes = [_parse_route(int(k[6:]), str(v)) for k, v in doc.items()
                  if k.startswith("route_") and k[6:].isdigit()]
        _bus_index.update(key=key, routes=sorted(routes, key=lambda r: r["route"]))
    return doc, _bus_index["routes"]


def _close(a: str, b: str, strict: bool) -> bool:
    if a == b:
        return True
    if min(len(a), len(b)) < 5:
        return False
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a, b).ratio() >= (0.88 if strict else 0.84)   # "yelhanka" ~ "yelahanka"


def _match_stops(query: str, routes: list, strict: bool = False) -> list:
    words = [w for w in _words(query) if len(w) >= 4 and w not in _QUERY_COMMON]
    plain = " ".join(_words(query))
    hits = []
    for r in routes:
        for st in r["stops"]:
            by_word = any(_close(t, w, strict) for t in st["tokens"] for w in words)
            by_phrase = len(st["phrase"].split()) >= 2 and f" {st['phrase']} " in f" {plain} "
            if by_word or by_phrase:
                hits.append({**_hit(r, st), "_exact": by_phrase})
    # "Yelahanka New Town" names one exact stop: answer only that one
    exact = [h for h in hits if h["_exact"]]
    return [{k: v for k, v in h.items() if k != "_exact"} for h in (exact or hits)]


def _hit(r: dict, st: dict) -> dict:
    return {"route": r["route"], "stop": st["stop"], "pickup_time": st["pickup_time"],
            "bus_reaches_campus": r["reaches_campus"], "driver": r["driver"],
            "staff_coordinator": r["staff_coordinator"]}


async def find_bus_stops(query: str, strict: bool = True) -> list:
    """Bus stops named in the question (used by intelligence_engine to spot bus questions)."""
    try:
        _, routes = await _bus_routes()
    except Exception as e:
        print(f"⚠️  Bus stop lookup skipped: {e}")
        return []
    hits = _match_stops(query, routes, strict=strict)
    # A short follow-up like "New Town" after "Yelahanka": the whole reply is part of one stop name.
    plain = " ".join(_words(query))
    if not hits and 1 <= len(plain.split()) <= 4:
        for r in routes:
            for st in r["stops"]:
                if len(plain.split()) >= 2 and f" {plain} " in f" {st['phrase']} ":
                    hits.append(_hit(r, st))
    return hits


def _bus_documents(doc) -> list:
    url = (doc or {}).get("bus_routes_pdf") or BUS_ROUTES_PDF
    return [{"title": "Bus routes 2026-27 (PDF)", "url": url}]


async def _transport_knowledge(intelligence_result: dict, result: dict) -> dict:
    """Narrows the transport record to what was asked: a place, a route number, or all routes."""
    doc, routes = await _bus_routes()
    if not routes:
        return result
    query = " ".join(x for x in (intelligence_result.get("query"), intelligence_result.get("normalized_query")) if x)
    general = {k: v for k, v in doc.items() if not k.startswith("_") and not (k.startswith("route_") and k[6:].isdigit())}
    asked = {int(n) for n in _ROUTE_ASKED.findall(query)}
    hits = _match_stops(query, routes)
    if not hits:   # "New Town" right after a Yelahanka answer
        for text in (intelligence_result.get("query"), intelligence_result.get("normalized_query")):
            hits = await find_bus_stops(text or "", strict=False)
            if hits:
                break
    if asked and not hits:
        picked = [r for r in routes if r["route"] in asked]
        if picked:
            general = {k: v for k, v in general.items() if k in ("driver_phone_policy", "timings", "academic_year")}
            data = {**general, "routes_asked": [
                {"route": r["route"], "driver": r["driver"], "staff_coordinator": r["staff_coordinator"],
                 "stops_and_pickup_times": ", ".join(f"{s['stop']} {s['pickup_time']}" for s in r["stops"]),
                 "bus_reaches_campus": r["reaches_campus"]} for r in picked],
                "answer_guide": ("Answer only what was asked about the route(s), in plain spoken sentences, "
                                 "never a list. Never give a driver's phone number.")}
            return {"found": True, "match_type": "single", "query_used": {"route": sorted(asked)},
                    "data": data, "documents": _bus_documents(doc)}
    if hits:
        stops = {h["stop"] for h in hits}
        low = query.lower()
        fee_asked = any(w in low for w in ("fee", "fees", "charge", "cost", "price", "shulka", "ಶುಲ್ಕ", "फीस", "किराया"))
        driver_asked = any(w in low for w in ("driver", "coordinator", "ಡ್ರೈವರ್", "ಚಾಲಕ", "ड्राइवर"))
        # only the facts this question needs (a smaller prompt answers faster)
        keep = {"driver_phone_policy"} | ({k for k in general if k.startswith("fee") or k == "academic_year"} if fee_asked else set())
        small = {k: v for k, v in general.items() if k in keep}
        matches = [{k: v for k, v in h.items() if driver_asked or k not in ("driver", "staff_coordinator")} for h in hits]
        if fee_asked:
            guide = ("They asked about the bus fee: give the fee that applies to their area. "
                     "Do not ask which stop they use.")
        else:
            guide = "First answer: give each matching stop with its route number and morning pick-up time. "
            if len(stops) > 1:
                guide += ("There are several matching stops, so AFTER answering, end with one short question "
                          "asking which of these stops is nearest to them.")
            else:
                guide += "Do not ask a follow-up question."
        guide += " Write plain spoken sentences, never a list. Never give a driver's phone number."
        data = {**small, "matching_stops": matches, "answer_guide": guide}
        return {"found": True, "match_type": "single", "query_used": {"stops": sorted(stops)},
                "data": data, "documents": _bus_documents(doc)}
    # General transport question, or a place with no college bus stop
    data = {**general, "all_routes": [
        {"route": r["route"], "first_stop": r["stops"][0]["stop"] if r["stops"] else None,
         "stops": ", ".join(s["stop"] for s in r["stops"]), "driver": r["driver"],
         "staff_coordinator": r["staff_coordinator"]} for r in routes],
        "answer_guide": ("If they asked about all routes, say how many routes there are and name the areas they "
                         "cover in one or two sentences, and say the full list with every stop and time is in the "
                         "Bus Routes PDF on their screen. If they named a place that is not in any route, say no "
                         "college bus stop is listed there and give the admission office numbers. Write plain "
                         "spoken sentences, never a list. Never give a driver's phone number.")}
    return {"found": True, "match_type": "single", "query_used": {"transport": "all"},
            "data": data, "documents": _bus_documents(doc)}


# ── Leadership questions: only the part asked (2026-10-29) ───────────────
# The faculty record now has principal, deans, HODs, trustees, council...
# (~7,000 characters). Sending all of it made "Who is the CSE HOD?" take 15 s.
# Each group of words picks the fields that answer it; if nothing matches,
# the whole record is used as before.
_LEADER_FIELDS = [
    (["vice principal", "vice-principal", "उप प्राचार्य", "ಉಪ ಪ್ರಾಂಶುಪಾಲ"], ["vice_principal"]),
    (["principal", "principle", "प्रिंसिपल", "प्राचार्य", "प्रधानाचार्य", "ಪ್ರಾಂಶುಪಾಲ", "ಪ್ರಿನ್ಸಿಪಾಲ್", "ಪ್ರಿನ್ಸಿಪಲ್"],
     ["principal", "principal_profile"]),
    (["hod", "hods", "head of", "heads of", "विभागाध्यक्ष", "ವಿಭಾಗದ ಮುಖ್ಯಸ್ಥ", "ಎಚ್‌ಒಡಿ", "ಎಚ್ಒಡಿ"], ["heads_of_departments"]),
    (["dean", "deans", "controller", "डीन", "ಡೀನ್"], ["deans"]),
    (["trustee", "trustees", "trust", "president", "secretary", "treasurer", "founder", "founders", "management", "manages", "managing", "runs the college",
      "trusti", "adhyaksha", "ट्रस्टी", "अध्यक्ष", "संस्थापक", "ಟ್ರಸ್ಟಿ", "ಅಧ್ಯಕ್ಷ", "ಸಂಸ್ಥಾಪಕ"],
     ["board_of_trustees", "trustee_profiles", "director"]),
    (["chairman", "chairperson", "governing council", "governing body", "council"], ["governing_council", "board_of_trustees"]),
    (["director", "निदेशक", "ನಿರ್ದೇಶಕ"], ["director"]),
    (["registrar", "office superintendent", "office", "रजिस्ट्रार", "ರಿಜಿಸ್ಟ್ರಾರ್"], ["office_administration"]),
    (["section head", "iqac", "librarian", "library", "coordinator", "nss", "ncc"], ["section_heads"]),
]


def _leadership_part(data, query: str):
    if not isinstance(data, dict):
        return data
    low = (query or "").lower()
    rest = low.replace("vice principal", " ").replace("vice-principal", " ")
    fields = []
    for words, keys in _LEADER_FIELDS:
        text = low if keys == ["vice_principal"] else rest
        if any((re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", text) if w.isascii() else w in text) for w in words):
            fields += [k for k in keys if k in data and k not in fields]
    if not fields:
        return data
    return {k: data[k] for k in fields}


# ── Every topic, the bus way (2026-10-30) ─────────────────────────────────
# The bus answers worked so well because the code picks the exact facts and
# tells the reply step what this question needs ("answer_guide"). The same now
# for the other topics: step-by-step admission per route, hostel for boys or
# girls, "why should I join SVIT", personal questions only the office can
# decide, website PDFs, and the college website when the database has nothing.
from engines import website_engine

_GIRLS = ("girl", "girls", "hudugi", "hudugiyaru", "ladki", "ladkiyon", "ಹುಡುಗಿ", "लड़की", "daughter", "magalu", "beti")
_BOYS = ("boy", "boys", "huduga", "hudugaru", "ladka", "ladkon", "ಹುಡುಗ", "लड़का", "son", "maga", "beta")

PERSONAL_GUIDE = (
    "This question is about one particular student's case (for example whether a quota, concession, "
    "scholarship or fee reduction applies to their child). First give, in one or two sentences, the "
    "general facts from this data that relate to it. Then say clearly that whether it applies to their "
    "child is decided by the SVIT admission office after checking the student's documents, so you cannot "
    "confirm it, and ask them to call the admission office number shown below. Never promise it will apply."
)


def _query_text(intelligence_result: dict) -> str:
    return " ".join(x for x in (intelligence_result.get("query"), intelligence_result.get("normalized_query")) if x)


def _has_any(text: str, words) -> bool:
    low = f" {text.lower()} "
    return any((f" {w} " in low) if w.isascii() else (w in low) for w in words)


def _with_guide(result: dict, guide: str) -> dict:
    """Adds an answer_guide to the data (a list of records is wrapped)."""
    data = result.get("data")
    if isinstance(data, dict):
        data = {**data, "answer_guide": guide}
    else:
        data = {"options": data, "answer_guide": guide}
    return {**result, "match_type": "single", "data": data}


def _hostel_part(result: dict, query: str) -> dict:
    docs = result.get("data") if isinstance(result.get("data"), list) else None
    if not docs:
        return result
    girls, boys = _has_any(query, _GIRLS), _has_any(query, _BOYS)
    if girls == boys:
        return result                                  # both or neither: all hostels (the reply asks which)
    want = "girls" if girls else "boys"
    keep = [d for d in docs if not d.get("hostel_for") or str(d.get("hostel_for")).lower() == want]
    return {**result, "data": keep} if keep else result


def _process_part(result: dict, entities: dict) -> dict:
    if entities.get("exam") or entities.get("quota"):
        return _with_guide(result, (
            "Give these admission steps in order, as short spoken sentences (First..., then..., after that..., "
            "finally...), not as a list. Mention the note in one short line at the end."))
    return _with_guide(result, (
        "The person did not say how they will apply. Explain briefly that there are three ways to join SVIT: "
        "KCET, COMEDK and the management quota, with one short line on each from the steps. Do not read out "
        "every step, and do not end with a question."))


async def _about_college_knowledge() -> dict:
    """"How is the college / why should I join" — the strongest facts from several records."""
    db = get_database()
    data = dict(profile_knowledge("ask_about_college").get("data") or {}) if profile_knowledge("ask_about_college") else {}
    for key in ("core_leadership_team", "educational_philosophy", "founded_by", "sister_institution"):
        data.pop(key, None)
    if db is not None:
        try:
            placements = await _cached_docs(db, "placements") or []
            college = next((d for d in placements if str(d.get("scope", "")).lower() == "whole college"), None)
            if college:
                data["placements"] = {k: college.get(k) for k in ("year", "total_placement_offers", "highest_ctc",
                                                                   "average_ctc", "companies_visited") if college.get(k)}
            campus = next(iter(await _cached_docs(db, "campus") or []), None)
            if campus and campus.get("overview"):
                data["campus"] = campus["overview"]
            safety = next(iter(await _cached_docs(db, "safety") or []), None)
            if safety:
                data["safety"] = "; ".join(str(safety[k]) for k in ("ragging", "girls_safety", "mentoring") if safety.get(k))
        except Exception as e:
            print(f"⚠️  About-college details skipped: {e}")
    if not data:
        return {"found": False, "reason": "no_data", "query_used": {}}
    data["answer_guide"] = (
        "If they ask how the college is or why they should join, answer in 3 or 4 short spoken sentences with the "
        "strongest points: autonomous status and accreditation (NAAC, NBA), placements (offers, highest and average "
        "package), the campus and student safety and mentoring. Do not list everything; never compare with other colleges.")
    return {"found": True, "match_type": "single", "query_used": {"about": "college"}, "data": data}


async def _documents_knowledge(intelligence_result: dict) -> dict:
    db = get_database()
    entities = intelligence_result.get("entities") or {}
    docs = await website_engine.find_documents(db, _query_text(intelligence_result), entities.get("branch")) if db is not None else []
    if not docs:
        return {"found": False, "reason": "no_matching_document", "query_used": {}}
    return {"found": True, "match_type": "single", "query_used": {"documents": [d["title"] for d in docs]},
            "data": {"documents_on_screen": [d["title"] for d in docs],
                     "answer_guide": ("Say in one short sentence that the document is on their screen as a button "
                                      "they can open, naming it. Do not describe what is inside it.")},
            "documents": docs}


async def _finish(intelligence_result: dict, result: dict) -> dict:
    """Last touches for every topic: the exact part, PDF buttons, website fallback, personal cases."""
    intent = intelligence_result.get("intent")
    entities = intelligence_result.get("entities") or {}
    query = _query_text(intelligence_result)
    db = get_database()
    try:
        if result.get("found"):
            if intent == "ask_admission_process":
                result = _process_part(result, entities)
            elif intent == "ask_hostel_facilities":
                result = _hostel_part(result, query)
        elif intent not in ("greet", "fallback", "ask_person") and db is not None:
            page = await website_engine.find_page(db, query)
            if page:
                result = {"found": True, "match_type": "single", "query_used": {"website_page": page["url"]},
                          "data": {"from_college_website_page": page["title"], "page_text": page["text"],
                                   "answer_guide": ("This text is from the college website. Answer only if it really "
                                                    "answers the question; otherwise say you don't have that "
                                                    "information. Say the page is linked below.")},
                          "documents": [{"title": f"Open on the college website: {page['title']}", "url": page["url"]}]}
        if result.get("found") and db is not None:
            extra = await website_engine.documents_for_topic(db, intent, entities.get("branch"))
            if extra:
                have = {d.get("url") for d in result.get("documents") or []}
                result = {**result, "documents": list(result.get("documents") or []) +
                          [d for d in extra if d["url"] not in have]}
        if intelligence_result.get("personal_case"):
            if result.get("found"):
                result = _with_guide(result, PERSONAL_GUIDE)
            else:
                result = {"found": True, "match_type": "single", "query_used": {"personal_case": True},
                          "data": {"answer_guide": PERSONAL_GUIDE}}
    except Exception as e:
        print(f"⚠️  Topic touches skipped: {type(e).__name__}: {e}")
    return result


# ── Questions naming several branches (2026-10-31) ───────────────────────
# "Cutoff for CSE and Mechanical": each branch is looked up and all records go
# to the reply (before, only one branch was searched).
MULTI_BRANCH_INTENTS = {"ask_fees_branch", "ask_cutoff", "ask_placement_by_branch", "ask_seat_availability"}


def branches_asked(entities: dict) -> list:
    """The branches named in THIS question (an older list kept by memory is ignored)."""
    names = (entities or {}).get("branches") or []
    return names if len(names) >= 2 and (entities or {}).get("branch") in names else []


async def _multi_branch_knowledge(collection: str, filters: dict, names: list) -> dict:
    records, missing = [], []
    for name in names:
        part = await retrieve_knowledge(collection, {**filters, "branch": name})
        data = part.get("data") if part.get("found") else None
        if isinstance(data, list):
            records.extend(data)
        elif isinstance(data, dict):
            records.append(data)
        else:
            missing.append(name)
    if not records:
        return {"found": False, "reason": "no_matching_records", "query_used": {**filters, "branches": names}}
    result = {"found": True, "match_type": "multiple", "data": records, "count": len(records),
              "query_used": {**filters, "branches": names},
              "note": "Several branches were asked: answer for EACH of them"}
    if missing:
        result["no_data_for"] = missing
    return result


async def fetch_knowledge(intelligence_result: dict) -> dict:
    knowledge_request = intelligence_result.get("knowledge_request", {})
    collection = knowledge_request.get("collection")
    filters = knowledge_request.get("filters", {})

    # 2026-10-29: a named person, or a department's faculty list
    if intelligence_result.get("intent") == "ask_person":
        try:
            people = await find_people(intelligence_result.get("query") or "")
        except Exception as e:
            print(f"⚠️  Person lookup failed: {e}")
            people = []
        if people:
            full = [p for p in people if p["match"] == "full"] or people
            return {"found": True, "match_type": "single", "query_used": {"people": [p["name"] for p in full]},
                    "data": {"people": [{"name": p["name"], "roles": p["roles"]} for p in full],
                             "note": "Answer with each person's roles; if several people match, mention each."}}
        return {"found": False, "reason": "no_matching_person", "query_used": {}}
    if intelligence_result.get("intent") == "ask_faculty_list":
        try:
            names = branches_asked(intelligence_result.get("entities") or {})
            if names:     # "faculty in CSE and ECE"
                parts = [await _faculty_list_knowledge({**intelligence_result, "entities": {
                    **(intelligence_result.get("entities") or {}), "branch": n}}) for n in names]
                found = [p["data"] for p in parts if p.get("found")]
                if found:
                    return {"found": True, "match_type": "multiple", "data": found, "count": len(found),
                            "query_used": {"branches": names}}
            return await _faculty_list_knowledge(intelligence_result)
        except Exception as e:
            print(f"⚠️  Faculty list lookup failed: {e}")
            return {"found": False, "reason": "database_error", "query_used": {}}

    # 2026-10-30: website PDFs on request, and "how is the college / why join"
    if intelligence_result.get("intent") == "ask_documents_pdf":
        return await _documents_knowledge(intelligence_result)
    if intelligence_result.get("intent") == "ask_about_college":
        return await _finish(intelligence_result, await _about_college_knowledge())

    # 2026-10-15: "tell me everything" -> College-at-a-glance overview built from
    # every collection at once (engines/college_overview.py).
    if intelligence_result.get("intent") == "ask_college_overview":
        from engines.college_overview import build_overview   # local import: it imports _find from here
        try:
            return {"found": True, "match_type": "overview", "query_used": {}, "data": await build_overview()}
        except Exception as e:
            print(f"⚠️  Could not build the college overview: {e}")
            return {"found": False, "match_type": "none", "query_used": {}, "data": None}

    # 2026-10-13: a rank was given ("my KCET rank is 25000, which branch?")
    # -> compare it with the cutoffs in code (engines/rank_predictor.py).
    entities = intelligence_result.get("entities") or {}
    if intelligence_result.get("intent") in RANK_INTENTS and isinstance(entities.get("rank"), int):
        db = get_database()
        try:
            docs = await _find(db, "cutoffs", {}, limit=500) if db is not None else []
        except Exception as e:
            print(f"⚠️  Could not read cutoffs for rank prediction: {e}")
            docs = []
        return rank_predictor.predict(entities["rank"], docs, exam=rank_predictor.wanted_exam(entities),
                                      branch=entities.get("branch"), category=entities.get("category"))

    # 2026-10-13: ISE is closed for new admissions (merged into CSE from 2026-27).
    # A fee / cutoff / seat question about ISE gets that explanation + the CSE figures,
    # instead of "I don't have that information".
    if entities.get("branch") == "ISE" and intelligence_result.get("intent") in ISE_MERGED_INTENTS:
        cse = await retrieve_knowledge(collection, {**filters, "branch": "CSE"})
        return {
            "found": True, "match_type": "single", "note": "ise_merged",
            "query_used": {**filters, "branch": "CSE"},
            "data": {
                "ise_status": ("ISE is closed for new admissions from 2026-27. ISE and CSE are very similar, "
                               "so ISE has been merged into CSE. Current ISE students continue in ISE."),
                "cse_details_instead": cse.get("data") if cse.get("found") else "not available",
            },
        }

    filters = {k: v for k, v in (filters or {}).items() if k != "branches"}
    names = branches_asked(entities) if intelligence_result.get("intent") in MULTI_BRANCH_INTENTS else []
    if names:
        result = await _multi_branch_knowledge(collection, filters, names)
    else:
        result = await retrieve_knowledge(collection, filters)

    # 2026-10-29: leadership -> only the part of the faculty record that was asked
    if intelligence_result.get("intent") == "ask_leadership" and result.get("found"):
        query = " ".join(x for x in (intelligence_result.get("query"), intelligence_result.get("normalized_query")) if x)
        result = {**result, "data": _leadership_part(result.get("data"), query)}

    # 2026-10-29: placements with no branch -> the whole-college figures (highest, average, offers)
    if (intelligence_result.get("intent") == "ask_placement_by_branch" and not entities.get("branch")
            and result.get("found")):
        docs = result.get("data") if isinstance(result.get("data"), list) else [result.get("data")]
        college = [d for d in docs if isinstance(d, dict) and str(d.get("scope", "")).lower() == "whole college"]
        if college:
            result = {**result, "match_type": "single", "data": college[0]}

    # 2026-10-29: bus questions -> the exact stops / route asked, plus the bus-route PDF
    if intelligence_result.get("intent") == TRANSPORT_INTENT:
        try:
            result = await _transport_knowledge(intelligence_result, result)
        except Exception as e:
            print(f"⚠️  Bus stop lookup failed, using the whole transport record: {e}")

    # No MongoDB record yet? Use the verified college facts if this topic
    # has some (about the college, affiliation, timings, admission contact).
    # A record the admin uploads always wins over these.
    if not result.get("found"):
        profile = profile_knowledge(intelligence_result.get("intent"))
        if profile:
            return await _finish(intelligence_result, profile)
    return await _finish(intelligence_result, result)