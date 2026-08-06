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
"""

from database.connection import get_database


async def retrieve_knowledge(collection_name: str, filters: dict) -> dict:
    if not collection_name:
        return {"found": False, "reason": "no_knowledge_needed", "data": None}

    db = get_database()
    if db is None:
        return {"found": False, "reason": "database_not_connected", "data": None}

    collection = db[collection_name]
    query = {k: v for k, v in (filters or {}).items() if v is not None}

    try:
        cursor = collection.find(query).limit(10)
        documents = await cursor.to_list(length=10)
        for doc in documents:
            doc["_id"] = str(doc["_id"])

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
            cursor = collection.find(broader_query).limit(10)
            documents = await cursor.to_list(length=10)
            for doc in documents:
                doc["_id"] = str(doc["_id"])

            if len(documents) == 1:
                return {"found": True, "match_type": "single", "data": documents[0], "query_used": broader_query, "note": "broadened_search"}
            if len(documents) > 1:
                return {"found": True, "match_type": "multiple", "data": documents, "count": len(documents), "query_used": broader_query, "note": "broadened_search"}

        return {"found": False, "reason": "no_matching_document", "query_used": query}

    except Exception as e:
        return {"found": False, "reason": "database_error", "error": str(e), "query_used": query}


async def fetch_knowledge(intelligence_result: dict) -> dict:
    knowledge_request = intelligence_result.get("knowledge_request", {})
    collection = knowledge_request.get("collection")
    filters = knowledge_request.get("filters", {})
    return await retrieve_knowledge(collection, filters)