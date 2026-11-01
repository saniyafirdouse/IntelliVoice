"""
engines/admission_guide.py — a short guided conversation for "I want to join" (2026-10-29).

Why: "Hi, I want to join this college" got one answer (apply through KCET,
COMEDK or management quota) and then nothing. A human at the admission desk
would offer to help and walk the person through it. Now IntelliVoice does:

  1. Answers the admission question, then asks:
       "Would you like me to help you with the admission process step by step?"
  2. "Yes"            -> "Sure! Are you planning to join through KCET, COMEDK, or the management quota?"
     "No"             -> "No problem! Ask me anything about SVIT admissions whenever you like."
  3. "KCET" (or COMEDK / management)
                      -> the admission steps for that route, then
                         "Which branch are you interested in? I can tell you its fee and cutoff."
  4. "CSE"            -> the fee for CSE through that route, then
                         "If you like, I can also tell you the cutoff, the documents needed, or hostel details."

Rules:
  - The question is ALWAYS asked after the answer, never instead of it.
  - Any other question at any step simply ends the guide and is answered normally.
  - The follow-up sentences are fixed text in English, Hindi and Kannada (no AI
    call, nothing can be made up, no extra delay).

2026-10-30: the same idea for every topic — after answering, a short offer of
the natural next step ("Would you like the CSE cutoff too?"); "yes" answers it.
See TOPIC_OFFERS.

Used by routes/voice.py (decide / next step) and engines/response_engine.py (the sentences).
NOTE: Hindi/Kannada wording pending a native-speaker check by the team.
"""

import re
import time

START_INTENTS = {"ask_admission_process"}
GUIDE_SECONDS = 600            # a guide step is forgotten after 10 minutes
SHORT_REPLY_WORDS = 6          # "yes" / "no" answers are short

_state = {}                    # session_id -> {"step": ..., "at": time, "route": {...}}

# ── Sentences (language, script) ──────────────────────────────────────────
MESSAGES = {
    "offer": {
        ("en", "native"): "Would you like me to help you with the admission process step by step?",
        ("en", "romanized"): "Would you like me to help you with the admission process step by step?",
        ("hi", "native"): "क्या आप चाहेंगे कि मैं admission process में step by step आपकी मदद करूँ?",
        ("hi", "romanized"): "Kya aap chahenge ki main admission process mein step by step aapki madad karoon?",
        ("kn", "native"): "Admission process ಅನ್ನು step by step ಆಗಿ ನಾನು ನಿಮಗೆ ಸಹಾಯ ಮಾಡಲಾ?",
        ("kn", "romanized"): "Admission process annu step by step aagi naanu nimage sahaaya maadala?",
    },
    "ask_route": {
        ("en", "native"): "Sure! Are you planning to join through KCET, COMEDK, or the management quota?",
        ("en", "romanized"): "Sure! Are you planning to join through KCET, COMEDK, or the management quota?",
        ("hi", "native"): "ज़रूर! आप KCET, COMEDK या management quota में से किसके ज़रिए join करना चाहते हैं?",
        ("hi", "romanized"): "Zaroor! Aap KCET, COMEDK ya management quota mein se kiske zariye join karna chahte hain?",
        ("kn", "native"): "ಖಂಡಿತ! ನೀವು KCET, COMEDK ಅಥವಾ management quota, ಯಾವುದರ ಮೂಲಕ join ಆಗಬೇಕು ಅಂತ ಇದ್ದೀರಾ?",
        ("kn", "romanized"): "Khanditha! Neevu KCET, COMEDK athava management quota, yaavudara mooloka join aagabeku anta iddeera?",
    },
    "ask_branch": {
        ("en", "native"): "Which branch are you interested in? I can tell you its fee and cutoff.",
        ("en", "romanized"): "Which branch are you interested in? I can tell you its fee and cutoff.",
        ("hi", "native"): "आपको कौन सी branch में interest है? मैं उसकी fees और cutoff बता सकती हूँ।",
        ("hi", "romanized"): "Aapko kaun si branch mein interest hai? Main uski fees aur cutoff bata sakti hoon.",
        ("kn", "native"): "ನಿಮಗೆ ಯಾವ branch ಬೇಕು? ಅದರ fees ಮತ್ತು cutoff ಹೇಳ್ತೀನಿ.",
        ("kn", "romanized"): "Nimage yaava branch beku? Adara fees mattu cutoff helteeni.",
    },
    "after_branch": {
        ("en", "native"): "If you like, I can also tell you the cutoff, the documents needed, or hostel details.",
        ("en", "romanized"): "If you like, I can also tell you the cutoff, the documents needed, or hostel details.",
        ("hi", "native"): "चाहें तो मैं cutoff, ज़रूरी documents या hostel की जानकारी भी बता सकती हूँ।",
        ("hi", "romanized"): "Chahein to main cutoff, zaroori documents ya hostel ki jaankari bhi bata sakti hoon.",
        ("kn", "native"): "ಬೇಕಿದ್ದರೆ cutoff, ಬೇಕಾದ documents ಅಥವಾ hostel ಬಗ್ಗೆನೂ ಹೇಳ್ತೀನಿ.",
        ("kn", "romanized"): "Bekiddare cutoff, bekaada documents athava hostel baggenu helteeni.",
    },
    "decline": {
        ("en", "native"): "No problem! Ask me anything about SVIT admissions whenever you like.",
        ("en", "romanized"): "No problem! Ask me anything about SVIT admissions whenever you like.",
        ("hi", "native"): "कोई बात नहीं! SVIT admission के बारे में कभी भी कुछ भी पूछिए।",
        ("hi", "romanized"): "Koi baat nahi! SVIT admission ke baare mein kabhi bhi kuch bhi poochiye.",
        ("kn", "native"): "ಪರವಾಗಿಲ್ಲ! SVIT admission ಬಗ್ಗೆ ಯಾವಾಗ ಬೇಕಾದರೂ ಕೇಳಿ.",
        ("kn", "romanized"): "Paravaagilla! SVIT admission bagge yaavaga bekaadaroo keli.",
    },
}

# ── Next-step offers for every topic (2026-10-30) ─────────────────────────
# Like a person at the admission desk: after answering, offer the natural next
# thing ("Would you like the CSE cutoff too?"). "Yes" answers it straight away;
# anything else is simply answered as a new question. Never offered when the
# answer itself already ended with a question (e.g. "Is this for a boy or a girl?").
TOPIC_MESSAGES = {
    "offer_cutoff": ("Would you like to know the {branch} cutoff too?",
                     "क्या आप {branch} का cutoff भी जानना चाहेंगे?", "Kya aap {branch} ka cutoff bhi jaanna chahenge?",
                     "{branch} cutoff ಕೂಡ ಹೇಳಲಾ?", "{branch} cutoff kooda helala?"),
    "offer_fee": ("Would you like to know the {branch} fee too?",
                  "क्या आप {branch} की fees भी जानना चाहेंगे?", "Kya aap {branch} ki fees bhi jaanna chahenge?",
                  "{branch} fees ಕೂಡ ಹೇಳಲಾ?", "{branch} fees kooda helala?"),
    "offer_recruiters": ("Would you like to know which companies recruit from SVIT?",
                         "क्या आप जानना चाहेंगे कि SVIT से कौन सी companies hire करती हैं?", "Kya aap jaanna chahenge ki SVIT se kaun si companies hire karti hain?",
                         "SVIT ಇಂದ ಯಾವ companies hire ಮಾಡ್ತವೆ ಅಂತ ಹೇಳಲಾ?", "SVIT inda yaava companies hire maadtave anta helala?"),
    "offer_placements": ("Would you like to hear about placements too?",
                         "क्या आप placements के बारे में भी जानना चाहेंगे?", "Kya aap placements ke baare mein bhi jaanna chahenge?",
                         "Placements ಬಗ್ಗೆನೂ ಹೇಳಲಾ?", "Placements baggenu helala?"),
    "offer_hostel_life": ("Would you like to know about the hostel food and rules too?",
                          "क्या आप hostel के खाने और rules के बारे में भी जानना चाहेंगे?", "Kya aap hostel ke khaane aur rules ke baare mein bhi jaanna chahenge?",
                          "Hostel ಊಟ ಮತ್ತು rules ಬಗ್ಗೆನೂ ಹೇಳಲಾ?", "Hostel oota mattu rules baggenu helala?"),
    "offer_hostel_fee": ("Would you like to know the hostel fee too?",
                         "क्या आप hostel की fees भी जानना चाहेंगे?", "Kya aap hostel ki fees bhi jaanna chahenge?",
                         "Hostel fees ಕೂಡ ಹೇಳಲಾ?", "Hostel fees kooda helala?"),
    "offer_contact": ("Would you like the admission office contact details?",
                      "क्या आप admission office का contact चाहेंगे?", "Kya aap admission office ka contact chahenge?",
                      "Admission office contact ಕೊಡಲಾ?", "Admission office contact kodala?"),
    "offer_scholarship_apply": ("Would you like to know how to apply for it?",
                                "क्या आप जानना चाहेंगे कि apply कैसे करें?", "Kya aap jaanna chahenge ki apply kaise karein?",
                                "ಹೇಗೆ apply ಮಾಡೋದು ಅಂತ ಹೇಳಲಾ?", "Hege apply maadodu anta helala?"),
    "offer_labs": ("Would you like to know about the labs too?",
                   "क्या आप labs के बारे में भी जानना चाहेंगे?", "Kya aap labs ke baare mein bhi jaanna chahenge?",
                   "Labs ಬಗ್ಗೆನೂ ಹೇಳಲಾ?", "Labs baggenu helala?"),
    "offer_sports": ("Would you like to know about sports too?",
                     "क्या आप sports के बारे में भी जानना चाहेंगे?", "Kya aap sports ke baare mein bhi jaanna chahenge?",
                     "Sports ಬಗ್ಗೆನೂ ಹೇಳಲಾ?", "Sports baggenu helala?"),
    "offer_campus_life": ("Would you like to know about the clubs and fests too?",
                          "क्या आप clubs और fests के बारे में भी जानना चाहेंगे?", "Kya aap clubs aur fests ke baare mein bhi jaanna chahenge?",
                          "Clubs ಮತ್ತು fests ಬಗ್ಗೆನೂ ಹೇಳಲಾ?", "Clubs mattu fests baggenu helala?"),
}
for _key, (_en, _hi, _hi_r, _kn, _kn_r) in TOPIC_MESSAGES.items():
    MESSAGES[_key] = {("en", "native"): _en, ("en", "romanized"): _en, ("hi", "native"): _hi,
                      ("hi", "romanized"): _hi_r, ("kn", "native"): _kn, ("kn", "romanized"): _kn_r}

_FEE_WORDS = ("fee", "fees", "cost", "charge", "eshtu", "kitna", "kitni", "ಫೀಸ್", "ಶುಲ್ಕ", "ಎಷ್ಟು", "फीस", "कितनी")

# intent -> (message, next intent, the question "yes" stands for, needs a branch?)
TOPIC_OFFERS = {
    "ask_fees_branch": ("offer_cutoff", "ask_cutoff", "What is the cutoff for {branch}?", True),
    "ask_cutoff": ("offer_fee", "ask_fees_branch", "What is the yearly fee for {branch}?", True),
    "ask_seat_availability": ("offer_fee", "ask_fees_branch", "What is the yearly fee for {branch}?", True),
    "ask_placement_by_branch": ("offer_recruiters", "ask_top_recruiters", "Which companies recruit from SVIT?", False),
    "ask_top_recruiters": ("offer_placements", "ask_placement_by_branch", "What are the placement numbers at SVIT?", False),
    "ask_about_college": ("offer_placements", "ask_placement_by_branch", "What are the placement numbers at SVIT?", False),
    "ask_required_documents": ("offer_contact", "ask_contact_admission_office", "What are the admission office contact details?", False),
    "ask_scholarship_available": ("offer_scholarship_apply", "ask_scholarship_eligibility", "How do I apply for the scholarship and who is eligible?", False),
    "ask_library": ("offer_labs", "ask_labs", "What labs does SVIT have?", False),
    "ask_campus_life": ("offer_sports", "ask_sports", "What sports facilities does SVIT have?", False),
    "ask_sports": ("offer_campus_life", "ask_campus_life", "What clubs and fests does SVIT have?", False),
    "ask_safety": ("offer_hostel_life", "ask_hostel_facilities", "What are the hostel rules and food like?", False),
}


def _topic_offer(intent: str, entities: dict, query: str = "", avoid: set | None = None) -> dict | None:
    if intent == "ask_hostel_facilities":
        low = (query or "").lower()
        if any(w in low for w in _FEE_WORDS):
            spec = ("offer_hostel_life", "ask_hostel_facilities", "What is the hostel food like and what are the rules?", False)
        else:
            spec = ("offer_hostel_fee", "ask_hostel_facilities", "What is the hostel fee?", False)
    else:
        spec = TOPIC_OFFERS.get(intent)
    if not spec:
        return None
    key, next_intent, question, needs_branch = spec
    branch = entities.get("branch")
    if needs_branch and not branch:
        return None
    if avoid and next_intent in avoid and next_intent != intent:
        return None
    keep = {k: entities[k] for k in ("branch", "exam", "quota", "category") if entities.get(k)}
    names = entities.get("branches") or []
    if len(names) >= 2 and branch in names:          # 2026-10-31: "CSE and Mechanical"
        keep["branches"] = list(names)
        branch = " and ".join(names) if len(names) == 2 else ", ".join(names[:-1]) + " and " + names[-1]
    return {"followup": key, "kind": "topic", "next": "offer_topic", "fmt": {"branch": branch or ""},
            "offer": {"intent": next_intent, "question": question.format(branch=branch or ""),
                      "entities": keep, "from": intent}}

# ── Understanding short answers ───────────────────────────────────────────
_YES = ["yes", "yeah", "yep", "yup", "ya", "yea", "sure", "ok", "okay", "please", "of course", "definitely",
        "go ahead", "help me", "tell me", "haan", "haa", "han", "ji", "haanji", "howdu", "haudu", "hoon", "hu",
        "sari", "aaytu", "aytu", "beku", "ಹೌದು", "ಹೂಂ", "ಹೂ", "ಸರಿ", "ಬೇಕು", "ಆಯ್ತು", "ಓಕೆ",
        "हाँ", "हां", "जी", "ठीक", "ज़रूर", "जरूर", "ओके"]
_NO = ["no", "nope", "nah", "not now", "later", "illa", "beda", "bedi", "nahi", "nahin", "mat",
       "ಇಲ್ಲ", "ಬೇಡ", "नहीं", "नही", "ना"]
# Route words, including how speech recognition often hears them ("CET", "Commit K").
_ROUTES = [
    (r"\bk\s?cet\b|\bcet\b|ಕೆಸಿಇಟಿ|ಸಿಇಟಿ|केसेट|सीईटी", {"exam": "KCET"}),
    (r"\bcomed\s?k\b|\bcommit\s?k\b|\bcomet\s?k\b|\bcomedk\b|ಕಾಮೆಡ್|कॉमेडके|कोमेडके", {"exam": "COMEDK"}),
    (r"\bmanagement\b|\bdirect\b|ಮ್ಯಾನೇಜ್‌?ಮೆಂಟ್|मैनेजमेंट", {"quota": "Management"}),
]


def _has(text: str, words: list) -> bool:
    for w in words:
        if w.isascii():
            if re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", text):
                return True
        elif w in text:
            return True
    return False


def _short(text: str) -> bool:
    return len(text.split()) <= SHORT_REPLY_WORDS


def _route_label(route: dict) -> str:
    if route.get("exam"):
        return route["exam"]
    return "the management quota" if route.get("quota") else "KCET or COMEDK"


def _route_of(text: str, entities: dict) -> dict:
    if entities.get("exam") or entities.get("quota"):
        return {k: entities[k] for k in ("exam", "quota") if entities.get(k)}
    for pattern, route in _ROUTES:
        if re.search(pattern, text):
            return dict(route)
    return {}


def _active(session_id):
    st = _state.get(session_id) if session_id else None
    if st and time.time() - st["at"] > GUIDE_SECONDS:
        _state.pop(session_id, None)
        return None
    return st


def decide(session_id, query: str, entities: dict) -> dict | None:
    """
    What this message means inside the guide, or None (= answer it normally).
      {"reply": "ask_route" | "decline", "next": step | None}
      {"intent": ..., "entities": {...}, "followup": "ask_branch" | "after_branch", "next": step | None, "route": {...}}
    Read-only: the state only changes in remember() after the reply was made.
    """
    st = _active(session_id)
    if not st:
        return None
    text = (query or "").lower().strip()
    step = st["step"]
    if step == "offer_help":
        route = _route_of(text, entities)
        if route:                                  # "yes, KCET" -> skip straight to the route answer
            return {"intent": "ask_admission_process", "entities": route, "followup": "ask_branch",
                    "next": "ask_branch", "route": route,
                    "question": f"What is the admission process at SVIT through {_route_label(route)}?"}
        if _short(text) and _has(text, _NO):
            return {"reply": "decline", "next": None}
        if _short(text) and _has(text, _YES):
            return {"reply": "ask_route", "next": "ask_route"}
        return None
    if step == "ask_route":
        route = _route_of(text, entities)
        if route:
            return {"intent": "ask_admission_process", "entities": route, "followup": "ask_branch",
                    "next": "ask_branch", "route": route,
                    "question": f"What is the admission process at SVIT through {_route_label(route)}?"}
        if _short(text) and _has(text, _NO):
            return {"reply": "decline", "next": None}
        if _short(text) and (_has(text, _YES) or "not sure" in text or "don't know" in text):
            return {"reply": "ask_route", "next": "ask_route"}       # ask again, plainly
        return None
    if step == "offer_topic":
        offer = st.get("offer") or {}
        if offer and _short(text) and _has(text, _NO):
            return {"reply": "decline", "next": None}
        if offer and _short(text) and _has(text, _YES):
            done = set(st.get("done", [])) | {offer.get("from")}
            chained = _topic_offer(offer["intent"], offer["entities"], offer["question"], avoid=done) or {}
            return {"intent": offer["intent"], "entities": offer["entities"], "question": offer["question"],
                    "followup": chained.get("followup"), "kind": "topic", "fmt": chained.get("fmt"),
                    "next": chained.get("next"), "offer": chained.get("offer"), "done": sorted(d for d in done if d)}
        return None
    if step == "ask_branch":
        if entities.get("branch"):
            route = st.get("route", {})
            return {"intent": "ask_fees_branch", "entities": {**route, "branch": entities["branch"]},
                    "followup": "after_branch", "next": None,
                    "question": f"What is the yearly fee for {entities['branch']} through {_route_label(route)}?"}
        if _short(text) and _has(text, _NO):
            return {"reply": "decline", "next": None}
        return None
    return None


def start_followup(intent: str, entities: dict, query: str = "") -> dict | None:
    """After a plain answer: the admission guide's offer, or the topic's next-step offer."""
    if intent in START_INTENTS and not (entities.get("exam") or entities.get("quota")):
        return {"followup": "offer", "next": "offer_help"}
    return _topic_offer(intent, entities, query)


def remember(session_id, next_step, route: dict | None = None, offer: dict | None = None,
             done: list | None = None) -> None:
    """Called once per turn, after the reply was made. None ends the guide."""
    if not session_id:
        return
    if not next_step:
        _state.pop(session_id, None)
        return
    old = _state.get(session_id) or {}
    _state[session_id] = {"step": next_step, "at": time.time(), "route": route or old.get("route", {}),
                          "offer": offer, "done": done or []}


def message(key: str, language: str, script: str, fmt: dict | None = None) -> str:
    table = MESSAGES[key]
    text = table.get((language, script)) or table[("en", "native")]
    return text.format(**fmt) if fmt and "{" in text else text
