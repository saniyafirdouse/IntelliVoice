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


# Kannada and Devanagari letters. Used to detect where a native-script
# word starts, since \\b does not work with these scripts (their vowel
# signs and viramas are not "word" characters in Python's regex).
_INDIC_LETTER = r"[\u0C80-\u0CFF\u0900-\u097F]"
_ZERO_WIDTH = re.compile(r"[\u200b\u200c\u200d]")  # ZWSP/ZWNJ/ZWJ typed inside words


# 2026-10-30: these aliases are also everyday English words ("tell me the fee",
# "will he be eligible") — they count only when written in CAPITALS (ME, BE).
# "Tell me the fee" was read as a question about Mechanical Engineering.
_UPPERCASE_ONLY_ALIASES = {"me", "be"}


def find_entity_word_boundary(text_lower: str, lookup_pairs: list, original: str | None = None) -> str | None:
    """
    Matches an alias only as a whole word/phrase, using \\b boundaries.
    This is the fix for the earlier bug where "ce" matched inside
    "accessible" and "st" matched inside "hostel" — plain substring
    search (`alias in text`) does not respect word boundaries, regex does.

    2026-10-06: aliases written in Kannada/Devanagari script use a
    different rule — the alias must START a word (not be preceded by
    another Kannada/Hindi letter), and may be followed by a suffix,
    because Kannada attaches case endings directly
    (e.g. "ಕೆಸಿಇಟಿಯಲ್ಲಿ" still means KCET). English aliases are matched
    exactly as before.
    """
    text_lower = _ZERO_WIDTH.sub("", text_lower)
    for alias, canonical in lookup_pairs:
        if alias in _UPPERCASE_ONLY_ALIASES:
            if original is not None and re.search(r"\b" + re.escape(alias.upper()) + r"\b", original):
                return canonical
            continue
        if alias.isascii():
            pattern = r"\b" + re.escape(alias) + r"\b"
        else:
            pattern = r"(?<!" + _INDIC_LETTER + r")" + re.escape(_ZERO_WIDTH.sub("", alias))
        if re.search(pattern, text_lower):
            return canonical
    return None


def find_all_branches(text_lower: str, original: str) -> list:
    """Every branch named in the text, in the order said (longest name wins on overlaps)."""
    text_lower = _ZERO_WIDTH.sub("", text_lower)
    spans = []
    for alias, canonical in ENTITY_LOOKUPS.get("branch", []):
        if alias in _UPPERCASE_ONLY_ALIASES:
            pattern, hay = r"\b" + re.escape(alias.upper()) + r"\b", original
        elif alias.isascii():
            pattern, hay = r"\b" + re.escape(alias) + r"\b", text_lower
        else:
            pattern, hay = r"(?<!" + _INDIC_LETTER + r")" + re.escape(_ZERO_WIDTH.sub("", alias)), text_lower
        for m in re.finditer(pattern, hay):
            spans.append((m.start(), m.end(), canonical))
    spans.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    found, last_end = [], -1
    for start, end, canonical in spans:
        if start < last_end:
            continue                                  # inside a longer name already taken
        last_end = end
        if canonical not in found:
            found.append(canonical)
    return found


def extract_entities(text: str) -> dict:
    text_lower = text.lower()
    entities = {}

    for entity_type in EXTRACTABLE_ENTITY_TYPES:
        lookup_pairs = ENTITY_LOOKUPS.get(entity_type, [])
        match = find_entity_word_boundary(text_lower, lookup_pairs, text)
        if match:
            entities[entity_type] = match

    # 2026-10-31: "cutoff for CSE and Mechanical" names TWO branches. Only one was
    # kept, so the other was never looked up ("I don't have CSE information").
    # All branches named are now kept in "branches" (the first one stays "branch").
    named = find_all_branches(text_lower, text)
    if len(named) >= 2:
        entities["branches"] = named

    # Percentage — regex only, no alias table needed
    percent_match = re.search(r"\b(\d{1,3})\s*%|\b(\d{1,3})\s*(?:percent|percentage|marks)\b", text_lower)
    if percent_match:
        entities["percentage"] = int(percent_match.group(1) or percent_match.group(2))

    # Rank — regex only, distinguished from percentage by "rank" keyword
    # or a larger number range typical of KCET/COMEDK ranks
    # 2026-10-13: "25,000" -> "25000" so ranks written with commas are found too.
    rank_text = re.sub(r"(?<=\d),(?=\d)", "", text_lower)
    rank_match = re.search(r"\b(\d{4,6})\s*(?:rank)?\b.*\brank\b|\brank\b.*?(\d{4,6})", rank_text)
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
    "process": ["exam", "quota"],     # 2026-10-30: step-by-step process for that route
    "documents": ["quota", "exam"],
    "deadline": ["exam"],
    "status": [],
    "seats": ["branch", "branches"],
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


# ── "Tell me everything" detector (2026-10-15) ────────────────────────────
# One question normally maps to ONE intent, so "fees, placements and hostel?"
# used to answer only one topic. These rules catch requests for the whole
# picture and send them to ask_college_overview (the College-at-a-glance card
# + brochure). Rules run before the models, so they cost no time.
OVERVIEW_INTENT = "ask_college_overview"

_OVERVIEW_PHRASES = [
    "brochure", "broucher", "brochur", "ब्रोशर", "ಬ್ರೋಷರ್", "ಬ್ರೋಚರ್",
    "all details", "all the details", "all information", "all the information", "all info",
    "complete details", "complete information", "complete info", "complete overview",
    "full details", "full information", "full info", "full picture", "whole picture",
    "everything about", "tell me everything", "everything i should know", "everything i need",
    "sab kuch", "sabkuch", "saari details", "sari details", "saari jaankari", "poori jaankari",
    "puri jaankari", "poori jankari", "puri jankari", "poora detail",
    "सब कुछ", "सारी जानकारी", "पूरी जानकारी", "सारी डिटेल",
    "ella maahiti", "ella mahiti", "ella details", "ella vivara", "poorti vivara", "sampoorna maahiti",
    "ಎಲ್ಲಾ ಮಾಹಿತಿ", "ಎಲ್ಲ ಮಾಹಿತಿ", "ಸಂಪೂರ್ಣ ಮಾಹಿತಿ", "ಪೂರ್ತಿ ಮಾಹಿತಿ", "ಎಲ್ಲಾ ವಿವರ",
]

_OVERVIEW_TOPICS = {
    "fees": ["fee", "fees", "kharcha", "shulka", "फीस", "शुल्क", "ಶುಲ್ಕ", "ಫೀಸ್"],
    "cutoff": ["cutoff", "cut off", "cut-off", "closing rank", "कटऑफ", "ಕಟ್ಆಫ್"],
    "placements": ["placement", "package", "recruiter", "companies", "प्लेसमेंट", "ಪ್ಲೇಸ್‌ಮೆಂಟ್", "ಪ್ಲೇಸ್ಮೆಂಟ್"],
    "hostel": ["hostel", "हॉस्टल", "छात्रावास", "ಹಾಸ್ಟೆಲ್"],
    "scholarship": ["scholarship", "छात्रवृत्ति", "स्कॉलरशिप", "ವಿದ್ಯಾರ್ಥಿವೇತನ", "ಸ್ಕಾಲರ್‌ಶಿಪ್", "ಸ್ಕಾಲರ್ಶಿಪ್"],
    "transport": ["transport", "bus", "बस", "ಬಸ್"],
    "internship": ["internship", "इंटर्नशिप", "ಇಂಟರ್ನ್‌ಶಿಪ್", "ಇಂಟರ್ನ್ಶಿಪ್"],
    "courses": ["branches", "courses", "programmes", "programs", "seats", "कोर्स", "ಕೋರ್ಸ್"],
    "faculty": ["faculty", "teachers", "hod", "principal", "ಅಧ್ಯಾಪಕ", "शिक्षक"],
}


def _has_word(text: str, word: str) -> bool:
    if word.isascii():   # whole words only: "bus" must not match "business"
        return re.search(rf"\b{re.escape(word)}", text) is not None
    return word in text


def _overview_topics(text: str) -> int:
    return sum(1 for words in _OVERVIEW_TOPICS.values() if any(_has_word(text, w) for w in words))


def is_overview_request(*texts: str) -> bool:
    """True when the user wants everything at once (see the rules above)."""
    for raw in texts:
        if not raw:
            continue
        t = _ZERO_WIDTH.sub("", raw.lower())
        topics = _overview_topics(t)
        if topics >= 3:                      # "fees, placements and hostel?"
            return True
        if "brochure" in t or "ब्रोशर" in t or "ಬ್ರೋಷರ್" in t or "ಬ್ರೋಚರ್" in t:
            return True
        # "all details" about ONE topic ("full details of the hostel") stays with that topic
        if topics != 1 and any(_has_word(t, p) for p in _OVERVIEW_PHRASES):
            return True
    return False


# ── "Who is the principal?" rule (2026-10-28) ─────────────────────────────
# No intent used to mention the principal, so the models guessed: sometimes
# "about the college" (worked), sometimes "fallback" — and a fallback right
# after a fees question was treated as a follow-up about fees, so the reply
# said "I don't have that information". Questions naming a leader now go
# straight to ask_leadership (answered from the faculty record).
LEADERSHIP_INTENT = "ask_leadership"
_LEADER_WORDS = [
    "principal", "principle", "vice principal", "hod", "hods", "head of department",
    "head of the department", "dean", "deans",
    # 2026-10-29: management, trust and office heads too
    "registrar", "chairman", "chairperson", "president", "vice president", "secretary", "treasurer",
    "trustee", "trustees", "board of trustees", "governing council", "governing body", "director",
    "founder", "founders", "controller of examination", "controller of examinations", "librarian",
    "office superintendent", "management members", "trusti", "adhyaksha",
    "अध्यक्ष", "ट्रस्टी", "संस्थापक", "निदेशक", "रजिस्ट्रार",
    "ಅಧ್ಯಕ್ಷ", "ಟ್ರಸ್ಟಿ", "ಸಂಸ್ಥಾಪಕ", "ನಿರ್ದೇಶಕ", "ರಿಜಿಸ್ಟ್ರಾರ್",
    "प्रिंसिपल", "प्राचार्य", "प्रधानाचार्य", "विभागाध्यक्ष", "डीन",
    "ಪ್ರಾಂಶುಪಾಲ", "ಪ್ರಿನ್ಸಿಪಾಲ್", "ಪ್ರಿನ್ಸಿಪಲ್", "ವಿಭಾಗದ ಮುಖ್ಯಸ್ಥ", "ಡೀನ್", "ಎಚ್‌ಒಡಿ", "ಎಚ್ಒಡಿ",
]
# "Are HODs approachable?" is about faculty support, not who leads.
_SUPPORT_WORDS = ["approach", "supportive", "support", "helpful", "friendly", "strict", "mentor"]


def is_leadership_question(*texts: str) -> bool:
    for raw in texts:
        if not raw:
            continue
        t = _ZERO_WIDTH.sub("", raw.lower())
        if any(_has_word(t, w) for w in _LEADER_WORDS) and not any(w in t for w in _SUPPORT_WORDS):
            return True
    return False


# ── Faculty lists and named people (2026-10-29) ────────────────────────────
# "Who are the faculty in AIML?" / "How many professors in ECE?" -> ask_faculty_list
# (the faculty_members collection: every department's teachers from the website).
# "Who is Dr. Vrinda Shetty?" -> ask_person (that person's roles, from the same data).
FACULTY_LIST_INTENT = "ask_faculty_list"
PERSON_INTENT = "ask_person"
_FACULTY_WORDS = [
    "faculty", "faculties", "professor", "professors", "teacher", "teachers", "teaching staff",
    "lecturer", "lecturers", "staff members", "adhyapakaru", "upanyasakaru",
    "शिक्षक", "प्रोफेसर", "अध्यापक", "ಅಧ್ಯಾಪಕ", "ಉಪನ್ಯಾಸಕ", "ಪ್ರೊಫೆಸರ್", "ಶಿಕ್ಷಕ",
]
_LIST_CUES = [
    "list", "names", "name of", "who are", "how many", "number of", "all the", "details", "members",
    "strength", "kaun kaun", "kitne", "yaaru yaaru", "eshtu", "yaaru", "ಯಾರು", "ಎಷ್ಟು", "कौन", "कितने",
]
_PERSON_CUES = [
    "who is", "who's", "about", "tell me", "details", "profile", "sir", "madam", "mam", "ma'am",
    "yaaru", "kaun", "contact", "department", "teach", "ಯಾರು", "ಬಗ್ಗೆ", "कौन", "बारे",
]


def is_faculty_list_question(*texts: str) -> bool:
    for raw in texts:
        if not raw:
            continue
        t = _ZERO_WIDTH.sub("", raw.lower())
        if any(w in t for w in _SUPPORT_WORDS):
            continue
        if "who teaches" in t or "who all teach" in t:
            return True
        if any(_has_word(t, w) for w in _FACULTY_WORDS) and any(_has_word(t, c) for c in _LIST_CUES):
            return True
    return False


async def find_named_people(text: str) -> list:
    """People from the college data named in the question (never raises)."""
    try:
        from engines.knowledge_engine import find_people      # local import: no import cycle
        people = await find_people(text)
    except Exception as e:
        print(f"⚠️  Name lookup skipped: {type(e).__name__}: {e}")
        return []
    if not people:
        return []
    if any(p["match"] == "full" for p in people):
        return [p for p in people if p["match"] == "full"]
    low = (text or "").lower()
    if len(people) <= 3 and any(c in low for c in _PERSON_CUES):
        return people
    return []


# ── Bus questions (2026-10-29) ────────────────────────────────────────────
# "Which bus for Yelahanka?", "route 3 timing", "who drives route 5",
# "is there pickup at Hebbal?" -> ask_transport_routes, answered from the exact
# stops (knowledge_engine). A place name alone works too when it is a bus stop
# ("Yelahanka?", "New Town" right after a Yelahanka answer).
TRANSPORT_INTENT = "ask_transport_routes"
_BUS_WORDS = [
    "bus", "buses", "college bus", "bus route", "bus routes", "bus stop", "pick up", "pickup", "pick-up",
    "boarding point", "transport", "transportation", "driver", "drivers", "bus fee", "bus fees",
    "बस", "परिवहन", "ड्राइवर", "ಬಸ್", "ಸಾರಿಗೆ", "ಡ್ರೈವರ್", "ಚಾಲಕ",
]
_ROUTE_NUMBER = re.compile(r"\broute\s*(?:no\.?|number|num)?\s*\d{1,2}\b", re.I)
_TRAVEL_CUES = ["reach", "come", "comes", "coming", "from", "pick", "drop", "near", "travel", "which one", "timing"]
_NOT_A_PLACE_CUES = ["who is", "who's", "sir", "madam", "mam", "prof", "dr.", "dr ", "holiday", "jayanti", "festival"]


def _has_whole_word(text: str, word: str) -> bool:
    if word.isascii():   # "bus" matches "bus" / "buses" only, never "business"
        return re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", text) is not None
    return word in text


async def is_bus_question(text: str, query_for_matching: str) -> bool:
    low = _ZERO_WIDTH.sub("", f"{text or ''} {query_for_matching or ''}".lower())
    if any(_has_whole_word(low, w) for w in _BUS_WORDS) or _ROUTE_NUMBER.search(low):
        return True
    if any(c in low for c in _NOT_A_PLACE_CUES):
        return False
    words = len((query_for_matching or text or "").split())
    if words > 5 and not any(_has_whole_word(low, c) for c in _TRAVEL_CUES):
        return False
    try:
        from engines.knowledge_engine import find_bus_stops      # local import: no import cycle
        return bool(await find_bus_stops(query_for_matching or text, strict=True))
    except Exception as e:
        print(f"⚠️  Bus stop check skipped: {type(e).__name__}: {e}")
        return False


# ── Documents from the college website (2026-10-30) ──────────────────────
# "Show me the academic calendar", "exam timetable PDF", "syllabus" -> the PDF
# button, from the saved copy of saividya.ac.in (engines/website_engine.py).
# 2026-11-02: "Cse fees" (very short) was sometimes given another topic by the Groq second
# opinion (ST is unsure on two words), so the reply said "I don't have CSE fee information".
# A short question about fees now always means the branch fee — unless it is clearly a
# different fee (hostel, bus, exam, application, payment / instalments / refund).
FEES_INTENT = "ask_fees_branch"
FEES_MAX_WORDS = 8
_FEE_WORDS = re.compile(r"\b(fee|fees|shulka|shulk|kharcha|kharch)\b|ಫೀಸ್|ಶುಲ್ಕ|फीस|शुल्क|ख़र्च|खर्च", re.IGNORECASE)
_OTHER_FEE = re.compile(
    r"\b(hostel|mess|bus|transport|transportation|exam|examination|application|admission\s+form|form|pay|paid|paying|"
    r"payment|payments|instal+ments?|emi|refund|late|fine|due\s+date|last\s+date|scholarship|concession|waiver)\b"
    r"|ಹಾಸ್ಟೆಲ್|ಬಸ್|हॉस्टल|बस",
    re.IGNORECASE)


def is_branch_fee_question(*texts: str) -> bool:
    """'CSE fees', 'fees for ECE?', 'ಫೀಸ್ ಎಷ್ಟು', 'fees kitni hai' — but not hostel / bus / exam fees or paying."""
    for t in texts:
        t = (t or "").strip()
        if not t or len(t.split()) > FEES_MAX_WORDS:
            continue
        if _FEE_WORDS.search(t) and not _OTHER_FEE.search(t):
            return True
    return False


DOCUMENTS_INTENT = "ask_documents_pdf"
_DOC_WORDS = [
    "pdf", "calendar", "calender", "calendar of events", "time table", "timetable", "syllabus", "scheme of study",
    "circular", "circulars", "regulations", "admission policy", "refund policy", "anti ragging", "anti-ragging",
    "mandatory disclosure", "nirf", "aicte", "approval letter", "newsletter", "exam fee structure", "grievance",
    "branch brochure", "cse brochure", "ece brochure", "aiml brochure", "mechanical brochure", "data science brochure",
    "ಕ್ಯಾಲೆಂಡರ್", "ಟೈಮ್ ಟೇಬಲ್", "ಸಿಲಬಸ್", "टाइम टेबल", "कैलेंडर", "सिलेबस",
]


def is_document_request(*texts: str) -> bool:
    for raw in texts:
        low = _ZERO_WIDTH.sub("", (raw or "").lower())
        if any(_has_whole_word(low, w) for w in _DOC_WORDS):
            return True
    return False


# ── Personal cases only the admission office can decide (2026-10-30) ──────
# "Can my son get this quota?", "Will my daughter's fee be reduced?" — depends on
# the student's own documents and is decided by the office after admission, so
# IntelliVoice gives the general facts and refers them to the office (the reply
# also shows the office's contact card).
_SELF_WORDS = [
    "my son", "my daughter", "my child", "my kid", "my ward", "my brother", "my sister", "my nephew", "my niece",
    "for me", "can i get", "will i get", "am i eligible", "do i get", "for my", "nanna maga", "nanna magalu",
    "nanna magu", "mera beta", "meri beti", "mere bete", "mere bachche", "mujhe", "nange", "nanage",
    "ನನ್ನ ಮಗ", "ನನ್ನ ಮಗಳು", "ನನ್ನ ಮಗು", "ನನಗೆ", "मेरा बेटा", "मेरी बेटी", "मेरे बच्चे", "मुझे",
]
_DECIDE_WORDS = [
    "eligible", "eligibility", "qualify", "concession", "discount", "reduce", "reduced", "reduction", "less fee",
    "lesser fee", "waiver", "waive", "free seat", "quota", "guarantee", "confirm", "chance", "possible", "apply for",
    "avail", "applicable", "applied", "applies", "sigutta", "sigutte", "siguthe", "milega", "milegi", "mil sakta", "mil sakti",
    "ಸಿಗುತ್ತಾ", "ಸಿಗುತ್ತೆ", "ರಿಯಾಯಿತಿ", "मिलेगा", "मिलेगी", "छूट",
]
_RANK_NUMBER = re.compile(r"\b\d{3,6}\b")


def is_personal_case(*texts: str) -> bool:
    low = _ZERO_WIDTH.sub("", " ".join(t or "" for t in texts).lower())
    if _RANK_NUMBER.search(low) and "rank" in low:
        return False                                   # "my son's rank is 25000" -> the rank predictor answers
    return any(_has_whole_word(low, w) for w in _SELF_WORDS) and any(_has_whole_word(low, w) for w in _DECIDE_WORDS)


# ── Main intent classification — the locked Engine 2 contract ─────────────
async def classify_intent(text: str, normalized_text: str = None, language: str = "en",
                          confirmed_intent: str = None) -> dict:
    """Engine 2. 2026-10-30: also marks personal cases only the admission office can decide."""
    result = await _classify_intent(text, normalized_text, language, confirmed_intent)
    if is_personal_case(text, normalized_text or ""):
        if result["intent"] in ("fallback", "greet"):
            result = _build_output(
                query=text, normalized_query=result.get("normalized_query", ""), language=language,
                intent_id="ask_contact_admission_office", confidence=1.0, confidence_zone="confident",
                emotion=result.get("emotion", "neutral"), entities=result.get("entities") or {})
        result["personal_case"] = True
    return result


async def _classify_intent(text: str, normalized_text: str = None, language: str = "en",
                           confirmed_intent: str = None) -> dict:
    """
    confirmed_intent (2026-10-09, speed): the voice route first classifies
    Whisper's raw text, then — if the transcript corrector changed a few
    words — classifies the corrected text again. It passes the intent the
    first run settled on (already checked by Groq, or confident). If
    Sentence Transformers picks the SAME intent for the corrected text,
    the two agree and the second Groq call (~1 s) is skipped. If they
    differ, Groq is asked exactly as before. Entities, emotion etc. are
    always recomputed from the corrected text.
    Previous version: intelligence_engine_backup_2026-10-09c.py
    """
    query_for_matching = normalized_text if normalized_text else text
    query_for_matching = strip_conversational_filler(query_for_matching)

    if not query_for_matching or not query_for_matching.strip():
        return _build_output(
            query=text, normalized_query=normalized_text or "", language=language,
            intent_id="fallback", confidence=0.0, confidence_zone="out_of_scope",
            emotion="neutral", entities={}
        )

    # 2026-10-15: "everything at once" requests -> College-at-a-glance overview
    if is_overview_request(text, query_for_matching):
        return _build_output(
            query=text, normalized_query=query_for_matching, language=language,
            intent_id=OVERVIEW_INTENT, confidence=1.0, confidence_zone="confident",
            emotion=detect_emotion(text), entities={}
        )

    # 2026-10-28: "Who is the principal / HOD / dean?" -> ask_leadership
    if is_leadership_question(text, query_for_matching):
        return _build_output(
            query=text, normalized_query=query_for_matching, language=language,
            intent_id=LEADERSHIP_INTENT, confidence=1.0, confidence_zone="confident",
            emotion=detect_emotion(text), entities=extract_entities(text)
        )

    # 2026-10-29: bus questions (before names: "Ramakrishna Ashrama" is a stop, not a person)
    if await is_bus_question(text, query_for_matching):
        return _build_output(
            query=text, normalized_query=query_for_matching, language=language,
            intent_id=TRANSPORT_INTENT, confidence=1.0, confidence_zone="confident",
            emotion=detect_emotion(text), entities=extract_entities(text)
        )

    # 2026-11-02: short fee questions -> branch fee (see is_branch_fee_question)
    if is_branch_fee_question(text, query_for_matching):
        return _build_output(
            query=text, normalized_query=query_for_matching, language=language,
            intent_id=FEES_INTENT, confidence=1.0, confidence_zone="confident",
            emotion=detect_emotion(text), entities=extract_entities(text)
        )

    # 2026-10-30: a PDF from the college website ("academic calendar", "exam timetable")
    if is_document_request(text, query_for_matching):
        return _build_output(
            query=text, normalized_query=query_for_matching, language=language,
            intent_id=DOCUMENTS_INTENT, confidence=1.0, confidence_zone="confident",
            emotion=detect_emotion(text), entities=extract_entities(text)
        )

    # 2026-10-29: a question naming someone from the college ("Who is Dr. Vrinda Shetty?")
    people = await find_named_people(text)
    if people:
        result = _build_output(
            query=text, normalized_query=query_for_matching, language=language,
            intent_id=PERSON_INTENT, confidence=1.0, confidence_zone="confident",
            emotion=detect_emotion(text), entities=extract_entities(text)
        )
        result["people"] = [p["name"] for p in people]
        return result

    # 2026-10-29: "Who are the faculty in CSE?" -> the department's teachers
    if is_faculty_list_question(text, query_for_matching):
        return _build_output(
            query=text, normalized_query=query_for_matching, language=language,
            intent_id=FACULTY_LIST_INTENT, confidence=1.0, confidence_zone="confident",
            emotion=detect_emotion(text), entities=extract_entities(text)
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
    # 2026-10-08 speed-up with IDENTICAL decisions: when ST confidence is
    # already >= the threshold, arbitrate_intent() always keeps ST's
    # intent whatever Groq says — so the Groq call is skipped (~0.6 s
    # saved). Below the threshold Groq is called exactly as before.
    if st_confidence >= HYBRID_ST_CONFIDENCE_THRESHOLD:
        groq_intent_id = st_intent_id
    elif confirmed_intent is not None and confirmed_intent == st_intent_id:
        groq_intent_id = confirmed_intent      # agreed by the first run — no second Groq call
    else:
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