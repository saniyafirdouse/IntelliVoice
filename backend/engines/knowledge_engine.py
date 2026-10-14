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
import time

from database.connection import get_database
from engines.college_profile import profile_knowledge
from engines import rank_predictor

USE_CACHE = True
CACHE_TTL_SECONDS = 60
CACHE_MAX_DOCS = 2000          # larger collections are not cached

_cache = {}                    # collection name -> {"docs": [...], "loaded_at": float, "refreshing": bool}
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
    try:
        docs = await _load_collection(db, name)
        if docs is None:
            _cache.pop(name, None)
        else:
            _cache[name] = {"docs": docs, "loaded_at": time.monotonic(), "refreshing": False}
    except Exception as e:
        print(f"⚠️  Knowledge cache refresh failed for '{name}': {e}")
        if name in _cache:
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
    cursor = db[collection_name].find(query).limit(limit)
    documents = await cursor.to_list(length=limit)
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


async def fetch_knowledge(intelligence_result: dict) -> dict:
    knowledge_request = intelligence_result.get("knowledge_request", {})
    collection = knowledge_request.get("collection")
    filters = knowledge_request.get("filters", {})

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

    result = await retrieve_knowledge(collection, filters)

    # No MongoDB record yet? Use the verified college facts if this topic
    # has some (about the college, affiliation, timings, admission contact).
    # A record the admin uploads always wins over these.
    if not result.get("found"):
        profile = profile_knowledge(intelligence_result.get("intent"))
        if profile:
            return profile
    return result