import json
import os
import re
from sentence_transformers import SentenceTransformer, util

print("Loading Sentence Transformer model...")
embedding_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
print("✅ Sentence Transformer model loaded")

# ── Load intents (frozen — 45 intents, plain list, no wrapper key) ─────────
INTENTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "database", "seed_data", "intents.json"
)
with open(INTENTS_PATH, "r", encoding="utf-8") as f:
    INTENTS = json.load(f)

# Build a lookup from intent id -> full intent record (for category,
# knowledge_collection lookups without re-scanning the list every time)
INTENT_BY_ID = {intent["id"]: intent for intent in INTENTS}

# Pre-compute embeddings for every example sentence at startup
print("Computing intent embeddings...")
intent_embeddings = []
intent_labels = []
for intent in INTENTS:
    for example in intent["examples"]:
        embedding = embedding_model.encode(example, convert_to_tensor=True)
        intent_embeddings.append(embedding)
        intent_labels.append(intent["id"])
print(f"✅ {len(intent_embeddings)} intent embeddings computed")


# ── Load entities.json (11 finite, truly extractable entity types) ────────
ENTITIES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "database", "seed_data", "entities.json"
)
with open(ENTITIES_PATH, "r", encoding="utf-8") as f:
    ENTITY_DATA = json.load(f)

# Flatten each entity category into a list of (alias, canonical_value)
# pairs, sorted by alias length descending so longer phrases
# ("cyber security") match before shorter ones ("cyber") ever get a chance.
def build_alias_lookup(entity_dict: dict) -> list:
    pairs = []
    for canonical, aliases in entity_dict.items():
        if canonical == "note":  # skip the note field in "company"
            continue
        for alias in aliases:
            pairs.append((alias.lower(), canonical))
    pairs.sort(key=lambda p: len(p[0]), reverse=True)
    return pairs

ENTITY_LOOKUPS = {
    entity_type: build_alias_lookup(entity_dict)
    for entity_type, entity_dict in ENTITY_DATA.items()
}

# The only entities Engine 2 actually extracts — the finite, truly
# lookup-able ones. Everything else in each intent's own
# "optional_entities" list is documentation for Engine 5, not something
# extracted here.
EXTRACTABLE_ENTITY_TYPES = [
    "branch", "quota", "category", "exam",
    "company", "course", "year", "semester", "campus_facility"
]


def find_entity_word_boundary(text_lower: str, lookup_pairs: list) -> str | None:
    """
    Matches an alias only as a whole word/phrase, using \\b boundaries.
    This is the fix for the earlier bug where "ce" matched inside
    "accessible" and "st" matched inside "hostel" — plain substring
    search (`alias in text`) does not respect word boundaries, regex does.
    """
    for alias, canonical in lookup_pairs:
        pattern = r"\b" + re.escape(alias) + r"\b"
        if re.search(pattern, text_lower):
            return canonical
    return None


def extract_entities(text: str) -> dict:
    text_lower = text.lower()
    entities = {}

    for entity_type in EXTRACTABLE_ENTITY_TYPES:
        lookup_pairs = ENTITY_LOOKUPS.get(entity_type, [])
        match = find_entity_word_boundary(text_lower, lookup_pairs)
        if match:
            entities[entity_type] = match

    # Percentage — regex only, no alias table needed
    percent_match = re.search(r"\b(\d{1,3})\s*%|\b(\d{1,3})\s*(?:percent|percentage|marks)\b", text_lower)
    if percent_match:
        entities["percentage"] = int(percent_match.group(1) or percent_match.group(2))

    # Rank — regex only, distinguished from percentage by "rank" keyword
    # or a larger number range typical of KCET/COMEDK ranks
    rank_match = re.search(r"\b(\d{4,6})\s*(?:rank)?\b.*\brank\b|\brank\b.*?(\d{4,6})", text_lower)
    if rank_match:
        rank_value = rank_match.group(1) or rank_match.group(2)
        if rank_value:
            entities["rank"] = int(rank_value)

    return entities


# ── Emotion detection ──────────────────────────────────────────────────────
EMOTION_PATTERNS = {
    "worried": [
        "worried", "scared", "fear", "afraid", "dar", "tension", "anxious",
        "nervous", "concerned", "chinta", "bhayabheetu", "ghabrao",
        "not sure", "what if", "will she", "will he", "still have",
        "struggle", "handle", "manage", "overwhelmed", "confused about"
    ],
    "confused": [
        "confused", "don't understand", "samajh nahi", "clear nahi",
        "not clear", "explain", "what does", "what is meant",
        "artha", "gothilla", "confuse", "confusion"
    ],
    "frustrated": [
        "nobody answered", "no response", "not helpful", "waste",
        "useless", "angry", "fed up", "irritated", "jawab nahi",
        "koi help nahi"
    ],
    "excited": [
        "excited", "happy", "great", "wonderful", "amazing",
        "got rank", "qualified", "passed", "selected", "khushi"
    ]
}


def detect_emotion(text: str) -> str:
    text_lower = text.lower()
    for emotion, keywords in EMOTION_PATTERNS.items():
        for kw in keywords:
            if re.search(r"\b" + re.escape(kw) + r"\b", text_lower):
                return emotion
    return "neutral"

# ── Response mode ───────────────────────────────────────────────────────────
# Emotion always overrides intent-based mode — a worried query about
# branch comparison still gets "reassurance", not "comparison".
COMPARISON_INTENTS = {"ask_branch_difference"}
RECOMMENDATION_INTENTS = {"ask_branch_recommendation"}


def determine_response_mode(intent_id: str, emotion: str, needs_escalation: bool) -> str:
    if needs_escalation:
        return "escalation"
    if emotion in {"worried", "confused", "frustrated"}:
        return "reassurance"
    if intent_id in COMPARISON_INTENTS:
        return "comparison"
    if intent_id in RECOMMENDATION_INTENTS:
        return "recommendation"
    return "informational"


# ── Needs-memory trigger ────────────────────────────────────────────────────
REFERENTIAL_MARKERS = ["what about", "and ", "also", "what if"]


def determine_needs_memory(text: str, entities: dict, confidence_zone: str) -> bool:
    text_lower = text.lower().strip()
    no_entities = len(entities) == 0
    has_referential_marker = any(marker in text_lower for marker in REFERENTIAL_MARKERS)
    is_short_and_bare = no_entities and len(text_lower.split()) <= 4

    if no_entities and (has_referential_marker or is_short_and_bare):
        return True
    if confidence_zone == "uncertain":
        return True
    return False


# ── Main intent classification — the locked Engine 2 contract ─────────────
async def classify_intent(text: str, normalized_text: str = None, language: str = "en") -> dict:
    query_for_matching = normalized_text if normalized_text else text

    if not query_for_matching or not query_for_matching.strip():
        return _build_output(
            query=text, normalized_query=normalized_text or "", language=language,
            intent_id="fallback", confidence=0.0, confidence_zone="out_of_scope",
            emotion="neutral", entities={}
        )

    # Sentence Transformers matching against all 45 intents' examples
    query_embedding = embedding_model.encode(query_for_matching, convert_to_tensor=True)

    best_score = 0.0
    best_intent_id = "fallback"

    for idx, intent_emb in enumerate(intent_embeddings):
        score = float(util.cos_sim(query_embedding, intent_emb))
        if score > best_score:
            best_score = score
            best_intent_id = intent_labels[idx]

    # Three-zone confidence handling
    if best_score >= 0.55:
        confidence_zone = "confident"
    elif best_score >= 0.35:
        confidence_zone = "uncertain"
        # best-guess intent is still used silently — no clarifying
        # question back to the user, per standing project decision
    else:
        confidence_zone = "out_of_scope"
        best_intent_id = "fallback"

    entities = extract_entities(text)
    emotion = detect_emotion(text)

    return _build_output(
        query=text, normalized_query=query_for_matching, language=language,
        intent_id=best_intent_id, confidence=round(best_score, 3),
        confidence_zone=confidence_zone, emotion=emotion, entities=entities
    )


def _build_output(query, normalized_query, language, intent_id, confidence,
                   confidence_zone, emotion, entities) -> dict:
    intent_record = INTENT_BY_ID.get(intent_id, {})
    category = intent_record.get("category", "General")
    knowledge_collection = intent_record.get("knowledge_collection")

    needs_escalation = (
        emotion in {"worried", "frustrated"} and confidence_zone in {"uncertain", "out_of_scope"}
    )
    response_mode = determine_response_mode(intent_id, emotion, needs_escalation)
    needs_memory = determine_needs_memory(query, entities, confidence_zone)

    return {
        "query": query,
        "normalized_query": normalized_query,
        "language": language,

        "intent": intent_id,
        "category": category,
        "confidence": confidence,
        "confidence_zone": confidence_zone,

        "emotion": emotion,
        "entities": entities,

        "knowledge_request": {
            "collection": knowledge_collection,
            "filters": entities
        },

        "response_mode": response_mode,
        "needs_memory": needs_memory,
        "needs_escalation": needs_escalation
    }