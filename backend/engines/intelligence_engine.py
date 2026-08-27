import json
import os
import re
from sentence_transformers import SentenceTransformer, util
from engines.groq_intent_classifier import classify_intent_groq

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

# ── Conversational filler stripping ─────────────────────────────────────
# Real phone-call speech is full of hedges and social framing that dilute
# the mean-pooled embedding away from the actual question being asked.
# This strips that noise ONLY for the text used in intent-matching —
# entity extraction and emotion detection still see the original text,
# since hedges like "i think" are useful signal for those.
FILLER_PATTERNS = [
    r"\bhello sir\b", r"\bhi sir\b", r"\bhello\b",
    r"\bactually\b", r"\bhonestly\b", r"\bbasically\b", r"\bseriously\b",
    r"\bi think\b", r"\bi guess\b",
    r"\bi dont remember exactly\b", r"\bi don't remember exactly\b",
    r"\byou know\b", r"\bum+\b", r"\buh+\b",
    r"\bkind of\b", r"\bsort of\b",
    r"\bsorry\b", r"\bplease\b",
    r"\byaar\b", r"\bbhai\b", r"\bwoh\b",
]

def strip_conversational_filler(text: str) -> str:
    # Guard: never strip on short messages — protects greetings like "Hi"
    # from being emptied out entirely.
    if len(text.split()) < 7:
        return text
    cleaned = text.lower()
    for pattern in FILLER_PATTERNS:
        cleaned = re.sub(pattern, " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned if cleaned else text


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

# ═══════════════════════════════════════════════════════════════════════
# HYBRID ARBITRATION LAYER (Sentence Transformers + Groq)
#
# Added after empirical evaluation on 140 labeled queries (100 regression
# + 40 held-out generalization set). See tests/log_hybrid_data.py and the
# resulting database/seed_data/hybrid_analysis_log.csv.
#
# Findings:
#   - When ST and Groq AGREE: correct 118/118 times (100%)
#   - When they DISAGREE and ST confidence >= 0.90: ST was correct 4/4
#   - When they DISAGREE and ST confidence <  0.90: Groq was correct 18/18
#   - 0.90 sits inside an observed gap between 0.840 (highest wrong-ST
#     disagreement score) and 0.914 (lowest correct-ST disagreement
#     score) — an empirically derived boundary, not an arbitrary guess.
#
# This layer ONLY decides which intent_id wins. It does not touch entity
# extraction, emotion detection, language detection, response_mode, or
# knowledge_request construction — all of that remains exactly as before,
# downstream of this decision.
# ═══════════════════════════════════════════════════════════════════════

HYBRID_ST_CONFIDENCE_THRESHOLD = 0.90


async def arbitrate_intent(st_intent_id: str, st_confidence: float, groq_intent_id: str) -> tuple[str, str]:
    """
    Decide the final intent_id when ST and Groq disagree.
    Returns (final_intent_id, decision_source) — decision_source is for
    internal logging/debugging only, not part of the public output.
    """
    if st_intent_id == groq_intent_id:
        return st_intent_id, "agreement"

    if st_confidence >= HYBRID_ST_CONFIDENCE_THRESHOLD:
        return st_intent_id, "st_high_confidence"

    return groq_intent_id, "groq_arbitration"

# Intents that share the "admissions" collection need a topic tag
# so the Knowledge Engine can tell which sub-type of admission
# info is being asked for (process / documents / deadline / status / seats).
INTENT_TOPIC_MAP = {
    "ask_admission_process": "process",
    "ask_required_documents": "documents",
    "ask_application_deadline": "deadline",
    "ask_admission_status": "status",
    "ask_seat_availability": "seats",
}

# Only these entity types are meaningful per admissions topic —
# sending irrelevant extras causes false non-matches or, worse,
# false matches against the wrong document.
TOPIC_RELEVANT_ENTITIES = {
    "process": [],
    "documents": ["quota"],
    "deadline": ["exam"],
    "status": [],
    "seats": ["branch"],
}


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
    query_for_matching = strip_conversational_filler(query_for_matching)

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

    # Three-zone confidence handling — UNCHANGED, exactly as before.
    # st_intent_id below is the ST result AFTER this zone forcing is
    # applied, matching precisely what was evaluated in the hybrid log.
    if best_score >= 0.55:
        confidence_zone = "confident"
    elif best_score >= 0.35:
        confidence_zone = "uncertain"
    else:
        confidence_zone = "out_of_scope"
        best_intent_id = "fallback"

    st_intent_id = best_intent_id
    st_confidence = best_score

    # ── Hybrid arbitration — the only new decision point ──────────────
    groq_result = await classify_intent_groq(text)
    groq_intent_id = groq_result["intent"]

    final_intent_id, _decision_source = await arbitrate_intent(
        st_intent_id, st_confidence, groq_intent_id
    )
    # ────────────────────────────────────────────────────────────────

    entities = extract_entities(text)
    emotion = detect_emotion(text)

    return _build_output(
        query=text, normalized_query=query_for_matching, language=language,
        intent_id=final_intent_id, confidence=round(best_score, 3),
        confidence_zone=confidence_zone, emotion=emotion, entities=entities
    )

def _build_output(query, normalized_query, language, intent_id, confidence,
                   confidence_zone, emotion, entities) -> dict:
    intent_record = INTENT_BY_ID.get(intent_id, {})
    category = intent_record.get("category", "General")
    knowledge_collection = intent_record.get("knowledge_collection")

    if intent_id in INTENT_TOPIC_MAP:
        topic = INTENT_TOPIC_MAP[intent_id]
        relevant_keys = TOPIC_RELEVANT_ENTITIES.get(topic, [])
        entities = {k: v for k, v in entities.items() if k in relevant_keys}
        entities = {**entities, "topic": topic}

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