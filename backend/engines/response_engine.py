"""
Engine 5 — Response Generation + Voice Output

Takes Engine 2's classification output + Engine 3's retrieved knowledge,
and generates a natural, empathetic response using Groq — strictly
constrained to only use provided facts (RAG principle), never invent
information. This is a communication layer only; all facts and
decisions were already made by Engines 2 and 3.

Flow per language:
    en: Groq writes English                              -> TTS (en)
    hi: Groq writes Hindi in the chosen script           -> TTS (hi)
    kn: Groq writes English
        -> Sarvam Mayura translates (code-mixed)
        -> Groq polishes into simple spoken Kannada, in Kannada script
        -> TTS always speaks the Kannada-script text
        -> if romanized display was chosen, Sarvam transliterates the
           Kannada-script text to Roman letters for the screen only

Script options (the `script` argument):
    "native"    — Kannada script / Devanagari
    "romanized" — Roman letters
    None        — language default: Kannada -> native, Hindi -> romanized

2026-10-02 changes (original kept in response_engine_backup_2026-10-02.py):
    - Added voice output (Sarvam Bulbul v3, see tts_engine.py)
    - Kannada script by default, romanized as a display option
    - Greetings/fallbacks for Kannada now use the same
      English -> Sarvam -> polish pipeline (were direct Groq Kannada)
    - Fixed greet/fallback prompt receiving a raw dict as its
      language instruction
    - Escalation now takes priority over the fallback redirect
    - Groq/Sarvam calls run in worker threads (no longer block the server)
    - Raised max_tokens: gpt-oss-20b is a reasoning model and spends
      tokens thinking before answering — low limits returned empty text
    - Removed unused code (_self_check_kannada, Kannada example
      dictionaries, Kannada direct-generation instructions)

2026-10-03 changes:
    - Added rule 10: spoken-length limit for all languages (English
      fee answers were ~53s because every fee field was read out)
    - Shortened the comparison and escalation mode instructions

2026-10-06 changes:
    - Kannada polish now receives the user's own question and MIRRORS it:
      English only for the user's own words, names/abbreviations/numbers,
      and a short list of college words (college, fee, admission, branch,
      hostel, placement, course, semester). Replaced the old
      "20-30% English" rule and English-heavy examples.
    - Kannada polish now uses openai/gpt-oss-120b (falls back to 20B),
      edits Sarvam's grammatical sentences instead of rewriting them,
      follows correct sentence patterns, and writes the user's
      romanized Kannada words in Kannada script.

2026-10-08 changes:
    - Faster plain factual replies, greetings and off-topic redirects
      (reasoning_effort="low"). Emotional / confused / escalation /
      comparison / recommendation replies and the Kannada polish keep
      full thinking — quality first.
    - Worried/confused replies no longer repeat the parent's situation
      back ("your son has low marks and you are tense, I understand");
      they acknowledge in a few words. Possibilities are never turned
      into promises ("can manage", not "will manage").

2026-10-08 (second set; previous version in response_engine_backup_2026-10-08b.py):
    - The assistant no longer says it will connect/transfer the parent to
      the admission office (it cannot) — it suggests contacting the office
      instead (rule 2, escalation mode, Kannada polish pattern).
    - Kannada polish: "to you" is always ನಿಮಗೆ, never ನಿಮ್ಮಿಗೆ.
    - Per-step timings (generate / translate / polish / romanize / tts)
      are returned in debug["timings_ms"] to see where time goes.

2026-10-08 (third set; previous version in response_engine_backup_2026-10-08c.py):
    - Kannada polish no longer adds "don't worry" / comfort lines when the
      reply being refined has none (a calm fee question got "tension
      ಮಾಡ್ಕೋಬೇಡಿ").
    - Fee answers: semester fee, early-bird fee, payment mode and
      installments are left out of the data given to the model unless the
      parent asked about them — prompt rules alone did not stop them being
      read out.

2026-10-09 (previous version in response_engine_backup_2026-10-09.py):
    - Kannada polish keeps quota/exam names in English: "Management quota"
      had become "ಸ್ವಂತ ಕೋಟಾ" ("own quota"), which a parent would not
      recognise. Added management, quota, seat, exam, rank, cutoff to the
      English college words.

2026-10-09 (speed set; previous version in response_engine_backup_2026-10-09-speed.py):
    - Kannada polish never repeats/restates the parent's question
      (a reply began "fee ಎಷ್ಟು ಎಂದು ಕೇಳಿದ್ದೀರಾ." — "you asked how much the fee is").
    - Returns "speech_language" so the voice route can make audio
      sentence-by-sentence for play-as-you-go.

2026-10-09 (b; previous version in response_engine_backup_2026-10-09b.py):
    - "Which branch?" safety net: a fee / cutoff / placement-by-branch
      question with no recognised branch gets a short question back
      ("Which branch are you asking about?") instead of an answer about a
      misheard name ("no information on the LCC branch") or a long list
      of every branch.

2026-10-09 (c; previous version in response_engine_backup_2026-10-09c.py):
    - KANNADA_PIPELINE setting: "translate_polish" (Sarvam translation +
      120B polish — the tested default) or "direct" (the 120B model
      writes the final Kannada from the English answer in ONE step,
      following the same rules; ~1 s faster). Compare both with
      tests/compare_kannada.py before switching. "direct" falls back to
      translate+polish automatically if it fails.
    - Sentence pattern for asking which branch; ಯಾವುದು (not ಯಾವದು).

2026-10-09 (d; previous version in response_engine_backup_2026-10-09d.py):
    - Kannada polish instructions rewritten compactly: the same rules and
      examples in well under half the length, so each Kannada reply uses
      far fewer Groq tokens (the free plan allows ~8K tokens/minute per
      model) and the polish is quicker. Added: never add facts/subjects
      that are not in the response (a CSE-vs-AIML reply had invented CSE
      subjects); technical words (AI, machine learning...) stay English.
    - Reply cache: repeated factual questions reuse the earlier reply.

2026-10-09 (e; previous version in response_engine_backup_2026-10-09e.py):
    - Polish: never mention son/daughter or the parent's situation unless
      the response does (a reply said ಮಗ to a mother asking about her
      daughter); no Kannada word left in English letters (mane, tumba);
      "office ಅನ್ನು", never "office ನನ್ನು".
"""

import asyncio
import hashlib
import json
import os
import re
import time
from collections import OrderedDict

from dotenv import load_dotenv
from groq import Groq

from engines.college_profile import IDENTITY_LINE
from engines.kannada_translator import translate_to_kannada
from engines.transliterator import romanize
from engines.tts_engine import synthesize_speech

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "openai/gpt-oss-20b"  # same model already validated for intent classification

# Kannada polish only: the larger model builds Kannada sentences far more
# reliably than the 20B one (20B produced awkward grammar like
# "...ಅಂತ ಕೇಳಿ ನನಗೆ ಅರ್ಥ ಆಗುತ್ತೆ"). If it fails, falls back to MODEL.
KANNADA_POLISH_MODEL = "openai/gpt-oss-120b"

# How much the gpt-oss models "think" before answering. "low" roughly
# halves the time of a call (measured 0.6 s vs 1.3 s) and is used ONLY
# for simple, low-risk replies. Emotional, confused, escalation,
# comparison and recommendation replies — and the Kannada polish — keep
# the model's default (fuller) thinking, so quality is not traded for
# speed where it matters most.
# How the Kannada reply is made (see changelog 2026-10-09 c):
#   "translate_polish" — Sarvam translates, 120B polishes (default, tested)
#   "direct"           — 120B writes the Kannada in one step (faster)
KANNADA_PIPELINE = "translate_polish"

FAST_REASONING = "low"
FAST_RESPONSE_MODES = {"informational"}

SUPPORTED_LANGUAGES = {"en", "hi", "kn"}
VALID_SCRIPTS = {"native", "romanized"}
DEFAULT_SCRIPT = {"en": "native", "hi": "romanized", "kn": "native"}

# Kannada is never generated directly by Groq (it can't produce reliable
# Kannada grammar), so only English and Hindi instructions exist here.
LANGUAGE_INSTRUCTIONS = {
    "en": {
        "romanized": "Respond in clear, natural English.",
        "native": "Respond in clear, natural English.",
    },
    "hi": {
        "romanized": (
            "Respond in natural, conversational Hindi WRITTEN IN ROMAN/ENGLISH "
            "LETTERS (Hinglish style, e.g. 'CSE ka fee 145000 hai'), NOT "
            "Devanagari script. The way real people actually text/speak on a "
            "phone call, NOT formal written Hindi. Keep technical terms "
            "(branch names, exam names like KCET/COMEDK, quota names, course "
            "names, and numbers) in English/numerals. Avoid formal words like "
            "'वार्षिक' or 'शुल्क' — use simple, spoken-style words like 'yearly', 'fee'.\n"
            "Example of RIGHT: 'CSE ka fee hai na, ye 145000 rupees hai yearly.'"
        ),
        "native": (
            "Respond in natural, conversational Hindi WRITTEN IN DEVANAGARI "
            "SCRIPT (हिन्दी लिपि), for readers who read Hindi script. Even in "
            "Devanagari, keep technical terms (branch names, exam names like "
            "KCET/COMEDK, quota names, course names, and numbers) in English/"
            "Roman letters and numerals — do not translate or transliterate "
            "them into Devanagari. Use simple, spoken-style Hindi words, not "
            "formal/literary vocabulary."
        ),
    },
}

SYSTEM_PROMPT_BASE = """You are IntelliVoice, SVIT college's admissions assistant — replacing a human staff member on a phone call, not acting like a typical chatbot.

ABSOLUTE RULES:
1. Use ONLY the facts given to you in "Retrieved Data" below. Never invent a number, fee, cutoff, place, name, or any fact not explicitly provided. Never use your own general knowledge about SVIT or any other college.
2. If Retrieved Data says NOT FOUND, say plainly you don't have that information right now and suggest they contact the SVIT admission office directly — never guess. You CANNOT connect, transfer or call anyone: never say "I will connect you", "I will transfer you" or "someone will call you".
2b. If Retrieved Data answers only part of the question, answer that part and say plainly you don't have information on the rest.
3. If multiple options are given, present ALL of them honestly — never pick one and pretend it's the only answer.
4. Never say anything negative about another college.
5. When comparing or recommending branches, never favor one — present facts, let the person decide.
6a. Never promise outcomes about a student (admission, results, placement, success). Say what is possible ("can", "may"), never what "will" happen.
6. If the user asks about a multi-year or total cost and you only have a per-year figure: state the current per-year figure as an exact fact, THEN clearly mention that fees can change year to year (institutional decisions, renovations, policy changes — real and common). If a rough multi-year estimate is genuinely useful, phrase it as an approximation only — using words like "roughly," "approximately," "as of now this could be around" — never state a calculated multi-year total as if it were a confirmed, precise fact.
7. Pay attention to the SPECIFIC words the user used in their own question (e.g., if they said "yearly," say "yearly" back; if they used a Hindi/Kannada word like "varshik," use that same word back). Mirror their own vocabulary and register as closely as natural, rather than substituting your own formal or casual synonym.
8. NEVER use markdown formatting — no asterisks for bold, no bullet points/dashes, no headers, no literal "\\n" newline characters. Write ONLY as plain, natural spoken sentences and paragraphs, exactly the way a person would actually talk on a phone call. If comparing multiple things, weave them into flowing sentences (e.g. "CSE focuses on... while AIML focuses on...") instead of a list structure.
9. {language_instruction}
10. This answer will be SPOKEN on a phone call, so keep it SHORT: usually 2-4 short sentences. Answer only what was asked, and mention only the details that answer the question. For example, for a fee question give the annual fee for each option — do not read out semester fees, early-bird fees, installments, or payment mode unless the user asked about them. Do not repeat the question back, and do not add long closing lines.
"""

# Tell the model exactly which college SVIT is (it once guessed a different
# "SVIT" in Pune). The line comes from engines/college_profile.py.
SYSTEM_PROMPT_BASE = SYSTEM_PROMPT_BASE.replace(
    "\n\nABSOLUTE RULES:", f"\n{IDENTITY_LINE}\n\nABSOLUTE RULES:", 1
)

RESPONSE_MODE_INSTRUCTIONS = {
    "informational": (
        "Give a direct, clear answer using the retrieved facts. Keep it "
        "conversational, not robotic or list-like unless the data is "
        "inherently list-shaped (e.g., multiple fee options)."
    ),

    "reassurance": (
        "The person is feeling {emotion}. Follow this exact structure:\n"
        "1. Acknowledge the feeling in a FEW words only (e.g. 'Please don't "
        "worry' / 'I understand your concern'). Do NOT repeat back the details "
        "of what they told you (never 'I understand that your son has low marks "
        "and you are tense...') — they know what they said; restating it is "
        "slow and sounds robotic.\n"
        "2. Normalize it — make clear this is a common, understandable concern.\n"
        "3. If Retrieved Data has relevant facts, weave them in as reassurance. "
        "If Retrieved Data says NOT FOUND, do NOT dwell on that or apologize "
        "for missing data — this is an emotional-support moment, not a data "
        "lookup. Simply reassure them in general, genuine terms (e.g. that "
        "support systems, mentorship, and guidance exist for exactly this "
        "kind of concern) without needing a specific database fact.\n"
        "4. End by inviting them to ask anything else — leave the door open.\n"
        "Never promise an outcome (never 'he WILL succeed'); say what is "
        "possible ('he CAN do well with the right support')."
    ),

    "comparison": (
        "Compare using only the retrieved facts: one short sentence per branch "
        "on its main focus, then one short sentence saying the right choice "
        "depends on the student's own interests — never state one branch is "
        "objectively \"better.\""
    ),

    "recommendation": (
        "Base your suggestion on what the person said about their interests. "
        "Never just rank branches. Explain briefly why the suggested branch(es) "
        "fit what they described, using only retrieved facts."
    ),

    "escalation": (
        "Answer in about 2 short sentences: first, briefly and warmly "
        "acknowledge their concern in a few words, without repeating back what "
        "they said (and give any directly relevant retrieved "
        "fact, if there is one); second, suggest they speak to the SVIT "
        "admission office directly, who can help them fully. Never say you "
        "are connecting or transferring them, or that someone will call "
        "them — you cannot do that."
    ),
}

GREET_INSTRUCTION = (
    "The user is greeting you. Respond with a warm, brief welcome "
    "and invite them to ask their question. No facts needed."
)

# Questions that can only be answered for a specific branch. If Engine 2
# found no branch (not said, or misheard), the parent is asked which one.
BRANCH_SPECIFIC_INTENTS = {"ask_fees_branch", "ask_cutoff", "ask_placement_by_branch"}

ASK_BRANCH_INSTRUCTION = (
    "The parent asked about fees, cutoff or placement, but it is not clear "
    "which branch they mean (the branch name was not said, or was not heard "
    "clearly). Do NOT give any numbers. In ONE short, polite sentence, ask "
    "which branch they are asking about, mentioning a few examples: CSE, "
    "ISE, ECE, AIML. Do not mention any branch name from their question "
    "that is not one of these, and do not say you could not hear them."
)

FALLBACK_INSTRUCTION = (
    "The user's question is unrelated to SVIT admissions (e.g. "
    "weather, sports, general knowledge). Politely acknowledge "
    "it's outside what you can help with, and gently steer the "
    "conversation back to admissions topics. Never attempt to "
    "actually answer the unrelated question."
)

# Fix A (2026-10-13): when Engine 3 finds NO data, the reply is this fixed
# message — the model is not asked at all, so it cannot make anything up.
# (Worried / escalation replies still go to the model: they comfort the
# parent without needing facts.)
# NOTE: Hindi/Kannada versions pending native-speaker check by the team.
NOT_FOUND_MESSAGES = {
    ("en", "native"): "I'm sorry, I don't have that information yet. For the correct details, please contact the SVIT admission office directly.",
    ("en", "romanized"): "I'm sorry, I don't have that information yet. For the correct details, please contact the SVIT admission office directly.",
    ("hi", "native"): "माफ़ कीजिए, यह जानकारी अभी मेरे पास नहीं है। सही जानकारी के लिए कृपया SVIT admission office से सीधे संपर्क कीजिए।",
    ("hi", "romanized"): "Maaf kijiye, yeh jaankari abhi mere paas nahi hai. Sahi jaankari ke liye kripya SVIT admission office se seedha sampark kijiye.",
    ("kn", "native"): "ಕ್ಷಮಿಸಿ, ಈ ಮಾಹಿತಿ ಸದ್ಯಕ್ಕೆ ನನ್ನ ಹತ್ತಿರ ಇಲ್ಲ. ಸರಿಯಾದ ಮಾಹಿತಿಗಾಗಿ ದಯವಿಟ್ಟು SVIT admission office ಅನ್ನು ನೇರವಾಗಿ ಸಂಪರ್ಕಿಸಿ.",
    ("kn", "romanized"): "Kshamisi, ee maahiti sadyakke nanna hattira illa. Sariyaada maahitigaagi dayavittu SVIT admission office annu neravaagi samparkisi.",
}
# Response modes that only state facts — with no facts they get NOT_FOUND_MESSAGES.
FACT_ONLY_MODES = {"informational", "comparison", "recommendation"}


def _fixed_reply(messages: dict, language: str, script: str) -> dict:
    """A ready-made reply in the user's language (no model call)."""
    message = messages[(language, script)]
    native_message = messages[(language, "native")]
    return {
        "display_text": message,
        "speech_text": native_message if language == "kn" else message,
        "speech_language": language,
    }


# 2026-10-13: contact answers list 3 phone numbers and 2 emails — fine to READ
# on screen, tiring to HEAR. For these the voice says one short sentence and
# the full details stay in the on-screen text.
# NOTE: Hindi/Kannada versions pending native-speaker check by the team.
CONTACT_SPEECH_INTENTS = {"ask_contact_admission_office"}
CONTACT_SPEECH = {
    "en": "You can call the SVIT admission office on the phone numbers shown on your screen, or email them at the addresses shown there.",
    "hi": "आप स्क्रीन पर दिखाए गए फ़ोन नंबरों पर SVIT admission office को call कर सकते हैं, या वहाँ दिए गए email पर mail कर सकते हैं।",
    "kn": "ಸ್ಕ್ರೀನ್ ಮೇಲೆ ತೋರಿಸಿರುವ ಫೋನ್ ನಂಬರ್‌ಗಳಿಗೆ SVIT admission office ಗೆ call ಮಾಡಬಹುದು, ಅಥವಾ ಅಲ್ಲಿ ಕೊಟ್ಟಿರುವ email ಗೆ mail ಮಾಡಬಹುದು.",
}


# Shown (and spoken) only if Groq fails completely.
# NOTE: Hindi/Kannada versions pending native-speaker check by the team.
ERROR_MESSAGES = {
    ("en", "native"): "I'm sorry, I'm having trouble answering right now. Please contact the SVIT admission office directly for help.",
    ("en", "romanized"): "I'm sorry, I'm having trouble answering right now. Please contact the SVIT admission office directly for help.",
    ("hi", "romanized"): "Maaf kijiye, abhi jawab dene mein dikkat ho rahi hai. Kripya SVIT admission office se seedha contact kijiye.",
    ("hi", "native"): "माफ़ कीजिए, अभी जवाब देने में दिक्कत हो रही है। कृपया SVIT admission office से सीधे contact कीजिए।",
    ("kn", "romanized"): "Kshamisi, eega uttara kodoke tondare aagtide. Dayavittu SVIT admission office annu neravaagi contact maadi.",
    ("kn", "native"): "ಕ್ಷಮಿಸಿ, ಈಗ ಉತ್ತರ ಕೊಡೋಕೆ ತೊಂದರೆ ಆಗ್ತಿದೆ. ದಯವಿಟ್ಟು SVIT admission office ಅನ್ನು ನೇರವಾಗಿ contact ಮಾಡಿ.",
}

KANNADA_POLISH_PROMPT = """You are refining a Kannada response for IntelliVoice, a college admissions voice assistant. The response will be SPOKEN to a parent on a phone call.
YOUR GOAL:
Rewrite the response so it sounds like NATURAL, SIMPLE, SPOKEN KARNATAKA KANNADA, the way a warm college counselor talks to a parent who may be elderly, rural, or comfortable mainly in Kannada. Not formal, textbook, literary or Sanskritized Kannada; not a translated English paragraph; not slang.
LENGTH: usually 2-4 short sentences. No long explanations, no repeating a point, no filler.

LANGUAGE — MIRROR THE USER'S WORDS (MOST IMPORTANT RULE):
Kannada is the main language. Use English ONLY for:
1. words the USER said in English (e.g. worry, tension, marks, manage);
2. names, abbreviations and numbers (CSE, AIML, KCET, COMEDK, SVIT, 120000, 2026-27);
3. college words Kannada speakers say in English: college, fee, admission, office, branch, hostel, placement, course, semester, management, quota, seat, exam, rank, cutoff;
4. technical subject names: AI, artificial intelligence, machine learning, deep learning, data science, programming, coding, software.
Say everything else in simple spoken Kannada, even if the response uses English for it (e.g. concern, normal, future, support, guidance, improve, succeed, questions). If the user used a Kannada word (bhaya, chinte, duddu), use that same word back.
Never translate quota/exam names or technical words: "Management quota", "KCET", "COMEDK", "NRI quota", "Government quota", "machine learning". WRONG: ಸ್ವಂತ ಕೋಟಾ, ಆಡಳಿತ ಕೋಟಾ, ಕೃತಕ ಬುದ್ಧಿಮತ್ತೆ, ಯಂತ್ರ ಕಲಿಕೆ, ಶಾಖೆ. Say "seat ಸಿಕ್ಕವರಿಗೆ", not "ಸ್ಥಾನ ಪಡೆಯುವ ಅಭ್ಯರ್ಥಿಗಳಿಗೆ".
SCRIPT: Kannada words in Kannada script, English words in English letters, numbers as digits. Kannada words the user typed in Roman letters (alli, eshtu, mane, tumba, maga) are written in Kannada script (ಅಲ್ಲಿ, ಎಷ್ಟು, ಮನೆ, ತುಂಬಾ, ಮಗ). Before answering, check that NO Kannada word is left in English letters.

EDIT, DON'T REWRITE — VERY IMPORTANT FOR GRAMMAR:
The response you are refining is already grammatically correct Kannada. Keep its sentence structure wherever it is correct and natural.
Mainly SWAP WORDS: replace unwanted English with simple Kannada, and use the user's own words where they fit.
Only restructure a sentence if it is genuinely formal, stiff, or textbook-like — and then use one of the CORRECT SENTENCE PATTERNS below.
A short, simple, grammatically correct sentence is always better than a clever one with broken grammar.

CORRECT SENTENCE PATTERNS:
- Acknowledge a worry ONLY if the response already does — a few words, with the user's own word: "ನಿಮ್ಮ ಚಿಂತೆ ಅರ್ಥ ಆಗುತ್ತೆ." / "tension ಮಾಡ್ಕೋಬೇಡಿ." A calm question gets NO "don't worry" line. WRONG (repeats their situation): "ನಿಮ್ಮ ಮಗನಿಗೆ ಕಡಿಮೆ marks ಬಂದಿರೋದ್ರಿಂದ ನಿಮಗೆ tension ಆಗ್ತಿರೋದು ನನಗೆ ಅರ್ಥ ಆಗುತ್ತೆ."
- Normalize: "ತುಂಬಾ ಜನ ತಂದೆ-ತಾಯಿಗೆ ಇದೇ ಚಿಂತೆ ಇರುತ್ತೆ."
- Reassure with a possibility, never a promise: "ಸರಿಯಾದ ಸಹಾಯ ಸಿಕ್ಕರೆ ಅವನು ಚೆನ್ನಾಗಿ ಮಾಡ್ಕೋಬಹುದು." WRONG: "ಅವನು manage ಮಾಡ್ತಾನೆ."
- A fact: "2026-27 ಕ್ಕೆ KCET ಮೂಲಕ CSE fee 120000 ರೂಪಾಯಿ."
- Not available: "ಈ ಮಾಹಿತಿ ಈಗ ನನ್ನ ಹತ್ತಿರ ಇಲ್ಲ. ದಯವಿಟ್ಟು SVIT admission office ಅಲ್ಲಿ ಕೇಳಿ." WRONG: "ನಾನು ನಿಮ್ಮನ್ನು admission office-ಗೆ ಸಂಪರ್ಕಿಸುತ್ತೇನೆ." (the assistant cannot connect anyone)
- Which branch: "ಯಾವ branch ಬಗ್ಗೆ ಕೇಳ್ತಿದ್ದೀರಾ? ಉದಾಹರಣೆಗೆ CSE, ISE, ECE, AIML."
- More questions: "ಇನ್ನೇನಾದ್ರೂ ಕೇಳಬೇಕಿದ್ರೆ ಕೇಳಿ." WRONG: "ನೀವು ಇನ್ನೇನಾದರೂ ಪ್ರಶ್ನೆಗಳಿದ್ದರೆ ಕೇಳಿ."
- Spelling: ನಿಮಗೆ (never ನಿಮ್ಮಿಗೆ), ಯಾವುದು (never ಯಾವದು), "office ಅನ್ನು" / "office ಅಲ್ಲಿ" (never "office ನನ್ನು").
- Formal -> natural: "ನಿಮ್ಮ ಚಿಂತೆಯನ್ನು ನಾನು ಅರ್ಥಮಾಡಿಕೊಳ್ಳುತ್ತೇನೆ." -> "ನಿಮ್ಮ ಚಿಂತೆ ನನಗೆ ಅರ್ಥ ಆಗುತ್ತೆ."   "ವಿದ್ಯಾರ್ಥಿಗಳಿಗೆ ಶೈಕ್ಷಣಿಕ ಮಾರ್ಗದರ್ಶನ ಮತ್ತು ಬೆಂಬಲವನ್ನು ಒದಗಿಸಲಾಗುತ್ತದೆ." -> "ಮಕ್ಕಳಿಗೆ ಸರಿಯಾದ ಸಹಾಯ ಸಿಗುತ್ತೆ."
Full example (the user said only marks, CSE, manage, tension): "tension ಮಾಡ್ಕೋಬೇಡಿ, ಇದು ತುಂಬಾ ತಂದೆ-ತಾಯಿಗೆ ಇರೋ ಚಿಂತೆನೇ. Marks ಸ್ವಲ್ಪ ಕಡಿಮೆ ಇದ್ರೂ, ಸರಿಯಾದ ಸಹಾಯ ಸಿಕ್ಕರೆ ಅವನು CSE ಅಲ್ಲಿ ಚೆನ್ನಾಗಿ manage ಮಾಡ್ಕೋಬಹುದು."

MEANING AND FACTS:
- Keep every number, date, name, branch, exam and fee exactly. Keep the meaning and the emotional tone.
- Add NOTHING that is not in the response: no new facts, subjects, details, advice, promises or comfort.
- Never turn "can/may" (ಮಾಡ್ಕೋಬಹುದು) into "will" (ಮಾಡ್ತಾನೆ) about a student's results, admission or placement.
- Never repeat or restate the parent's question or situation ("...ಎಂದು ಕೇಳಿದ್ದೀರಾ"). Start with the answer. Mirroring means reusing their words, not their question.
- Never say the assistant will connect, transfer or call anyone. Do not speak to the child directly.
- Never mention the student as son or daughter (ಮಗ / ಮಗಳು), and never describe the parent's situation, unless the response itself does — and then use exactly what it says.

OUTPUT: only the final Kannada response as one paragraph — no explanations, alternatives, translations, romanization, quotes, bullets, markdown or line breaks.

User's question (mirror these words):
{user_query}

Response to refine:
{formal_kannada}
"""


def _build_direct_prompt(polish_prompt: str) -> str:
    """Same rules as the polish prompt, but the input is the ENGLISH answer."""
    p = polish_prompt
    replacements = [
        ("You are refining a Kannada response for IntelliVoice",
         "You are writing a Kannada response for IntelliVoice"),
        ("Rewrite the response so it sounds like NATURAL, SIMPLE, SPOKEN KARNATAKA KANNADA",
         "Write the English answer given at the end as NATURAL, SIMPLE, SPOKEN KARNATAKA KANNADA"),
        ("""EDIT, DON'T REWRITE — VERY IMPORTANT FOR GRAMMAR:
The response you are refining is already grammatically correct Kannada. Keep its sentence structure wherever it is correct and natural.
Mainly SWAP WORDS: replace unwanted English with simple Kannada, and use the user's own words where they fit.
Only restructure a sentence if it is genuinely formal, stiff, or textbook-like — and then use one of the CORRECT SENTENCE PATTERNS below.
A short, simple, grammatically correct sentence is always better than a clever one with broken grammar.""",
         """GRAMMAR — VERY IMPORTANT:
Write short, simple sentences, each one grammatically correct. Build them like the CORRECT SENTENCE PATTERNS below.
Say exactly what the English answer says — the same facts and meaning — nothing added, nothing left out.
A short, simple, grammatically correct sentence is always better than a clever one with broken grammar."""),
        ("Response to refine:\n{formal_kannada}", "English answer to write in Kannada:\n{formal_kannada}"),
    ]
    for old, new in replacements:
        assert p.count(old) == 1, f"direct prompt: could not find {old[:40]!r}"
        p = p.replace(old, new)
    return p


KANNADA_DIRECT_PROMPT = _build_direct_prompt(KANNADA_POLISH_PROMPT)


# ── Reply cache ─────────────────────────────────────────────────────────
# 2026-10-09: a plain factual question that was already answered (same
# intent, same branch/exam/quota, same language and script, and the SAME
# database facts) gets the earlier reply instantly — no Groq or Sarvam
# calls, so it is fast and uses none of the free-plan allowance.
#   - Never used for worried / confused / escalation / comparison /
#     recommendation replies, greetings or off-topic questions: those are
#     always written fresh.
#   - The database facts are part of the key, so if a fee changes in
#     MongoDB the old reply is simply never used again.
#   - Trade-off: a repeated reply does not mirror the new parent's exact
#     words (it mirrors the first parent's). Facts are identical.
# REPLY_CACHE_ENABLED = False turns it off.
REPLY_CACHE_ENABLED = True
REPLY_CACHE_TTL_SECONDS = 3600
REPLY_CACHE_MAX_ENTRIES = 200
_reply_cache = OrderedDict()


def _reply_cache_key(engine2_result: dict, knowledge_result: dict,
                     language: str, script: str, query: str):
    if not REPLY_CACHE_ENABLED:
        return None
    intent_id = engine2_result.get("intent")
    if intent_id in (None, "greet", "fallback"):
        return None
    if (engine2_result.get("needs_escalation")
            or engine2_result.get("emotion", "neutral") != "neutral"
            or engine2_result.get("response_mode", "informational") != "informational"):
        return None
    if not (knowledge_result or {}).get("found"):
        return None   # "not found" replies are fixed text — nothing to cache
    facts = format_retrieved_data(knowledge_result, query)
    # The question's own words are part of the key (2026-10-13): two
    # differently-worded questions no longer share one cached answer.
    question = re.sub(r"[^\w\s]", " ", (query or "").lower())
    question = " ".join(question.split())
    raw = json.dumps([intent_id, language, script, engine2_result.get("entities") or {}, facts, question],
                     sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _reply_cache_get(key):
    if key is None or key not in _reply_cache:
        return None
    entry = _reply_cache[key]
    if time.monotonic() - entry["at"] > REPLY_CACHE_TTL_SECONDS:
        _reply_cache.pop(key, None)
        return None
    _reply_cache.move_to_end(key)
    return entry["value"]


def _reply_cache_put(key, value) -> None:
    _reply_cache[key] = {"value": value, "at": time.monotonic()}
    _reply_cache.move_to_end(key)
    while len(_reply_cache) > REPLY_CACHE_MAX_ENTRIES:
        _reply_cache.popitem(last=False)


# ── Small helpers ───────────────────────────────────────────────────────

def _ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def _resolve_language(language: str) -> str:
    return language if language in SUPPORTED_LANGUAGES else "en"


def _resolve_script(language: str, script: str | None) -> str:
    if script in VALID_SCRIPTS:
        return script
    return DEFAULT_SCRIPT[language]


def _language_instruction(language: str, script: str) -> str:
    """Kannada is generated in English first, so it gets the English instruction."""
    generation_language = "en" if language == "kn" else language
    return LANGUAGE_INSTRUCTIONS[generation_language][script]


async def _groq_chat(messages: list, temperature: float, max_tokens: int,
                     model: str = MODEL, reasoning_effort: str | None = None) -> str:
    """
    Runs the (synchronous) Groq client in a worker thread so the
    FastAPI event loop stays free for other requests.
    Raises ValueError on an empty answer, so callers never return blank text.
    """
    extra = {"reasoning_effort": reasoning_effort} if reasoning_effort else {}
    response = await asyncio.to_thread(
        client.chat.completions.create,
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        **extra,
    )
    text = (response.choices[0].message.content or "").strip()
    if not text:
        raise ValueError("Groq returned an empty response (token limit hit during reasoning?)")
    return text


# Fee records also carry details a parent rarely needs on a call. Each is
# kept only if the parent's question contains one of its words; otherwise
# it is removed before the model sees the data (prompt rules alone did not
# stop the model reading them out).
OPTIONAL_DETAIL_FIELDS = {
    "semester_fee":   ["semester", "sem"],
    "early_bird_fee": ["early", "bird", "discount", "concession"],
    "payment_mode":   ["payment", "pay", "installment", "instalment", "emi", "kantu", "kisht"],
    "installments":   ["payment", "pay", "installment", "instalment", "emi", "kantu", "kisht"],
}


def _drop_unasked_details(doc: dict, query: str) -> dict:
    words = set(re.findall(r"[a-z]+", (query or "").lower()))
    joined = (query or "").lower()
    def asked(keywords):
        return any(k in words or (" " in k and k in joined) for k in keywords)
    return {k: v for k, v in doc.items()
            if k not in OPTIONAL_DETAIL_FIELDS or asked(OPTIONAL_DETAIL_FIELDS[k])}


def format_retrieved_data(knowledge_result: dict, query: str = "") -> str:
    """
    Formats Engine 3's output into the exact text block the prompt needs.
    Handles all three real cases Engine 3 actually produces: single match,
    multiple matches (ambiguous query), and not found.
    MongoDB's internal _id is dropped — it's meaningless to the user.
    """
    if not knowledge_result or not knowledge_result.get("found"):
        return "NOT FOUND — no matching record exists yet."

    def clean(doc):
        if isinstance(doc, dict):
            # "_id" and bookkeeping like "_meta" (seed tag, sources) are not facts for the reply.
            doc = {k: v for k, v in doc.items() if not k.startswith("_")}
            return _drop_unasked_details(doc, query)
        return doc

    def to_text(doc):
        return json.dumps(clean(doc), ensure_ascii=False, default=str)

    data = knowledge_result.get("data")
    if knowledge_result.get("match_type") == "multiple" and isinstance(data, list):
        lines = ["Multiple options — present all of them:"]
        for i, item in enumerate(data, 1):
            lines.append(f"{i}. {to_text(item)}")
        return "\n".join(lines)

    return to_text(data)


# ── Text generation ─────────────────────────────────────────────────────

async def _generate_grounded(engine2_result: dict, knowledge_result: dict,
                             language: str, script: str) -> str:
    """Normal path — full RAG-constrained prompt with Engine 3's data."""
    intent_id = engine2_result.get("intent", "fallback")
    emotion = engine2_result.get("emotion", "neutral")
    response_mode = engine2_result.get("response_mode", "informational")
    query = engine2_result.get("query", "")

    system_prompt = SYSTEM_PROMPT_BASE.format(
        language_instruction=_language_instruction(language, script)
    )

    mode_instruction = RESPONSE_MODE_INSTRUCTIONS.get(
        response_mode, RESPONSE_MODE_INSTRUCTIONS["informational"]
    )
    if response_mode == "reassurance":
        mode_instruction = mode_instruction.format(emotion=emotion)

    user_message = f"""User's question: {query}

Intent: {intent_id}
Response mode instructions: {mode_instruction}

Retrieved Data: {format_retrieved_data(knowledge_result, query)}

Generate the response now, following all rules above."""

    return await _groq_chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.4,   # factual consistency matters more than creativity
        max_tokens=1500,   # reasoning model: needs headroom for thinking + answer
        # Plain factual answers think less (faster); every emotional or
        # complex mode keeps full thinking.
        reasoning_effort=FAST_REASONING if response_mode in FAST_RESPONSE_MODES else None,
    )


async def _generate_simple(instruction: str, language: str, script: str, query: str) -> str:
    """Greet/fallback path — no retrieved data involved."""
    system_prompt = (
        "You are IntelliVoice, SVIT college's admissions assistant.\n"
        f"{IDENTITY_LINE}\n"
        f"{instruction}\n"
        f"{_language_instruction(language, script)}\n"
        "Keep it brief — 1-2 sentences. Plain spoken sentences, no markdown."
    )
    return await _groq_chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query or "Hello"},
        ],
        temperature=0.5,
        max_tokens=800,    # was 150 — too low for a reasoning model
        reasoning_effort=FAST_REASONING,   # greeting / off-topic redirect: simple
    )


# ── Kannada pipeline ────────────────────────────────────────────────────

async def _polish_kannada(formal_kannada: str, user_query: str = "") -> tuple[str, bool]:
    """
    Takes Sarvam's translated Kannada (code-mixed mode) and asks Groq to
    rebalance it toward Kannada-dominant, simple spoken language — a
    constrained edit, not free composition. Returns (text, polished_ok);
    on any failure the unpolished Sarvam translation is used.
    """
    messages = [{"role": "user", "content": KANNADA_POLISH_PROMPT.format(
        formal_kannada=formal_kannada,
        user_query=user_query or "(not available)",
    )}]
    for model in (KANNADA_POLISH_MODEL, MODEL):
        try:
            text = await _groq_chat(messages, temperature=0.3, max_tokens=2000, model=model)
            return text, True
        except Exception as e:
            print(f"⚠️  Kannada polish failed with {model}: {e}")
    print("⚠️  Using raw Sarvam translation for this reply")
    return formal_kannada, False


async def _direct_kannada(english_text: str, user_query: str = ""):
    """One step: the 120B model writes the final Kannada. None on failure."""
    messages = [{"role": "user", "content": KANNADA_DIRECT_PROMPT.format(
        formal_kannada=english_text,
        user_query=user_query or "(not available)",
    )}]
    try:
        text = await _groq_chat(messages, temperature=0.3, max_tokens=2000, model=KANNADA_POLISH_MODEL)
        # Must actually be Kannada (not English left as-is).
        if sum("\u0C80" <= ch <= "\u0CFF" for ch in text) < 5:
            print("⚠️  Direct Kannada came back without Kannada script — using translate+polish")
            return None
        return text
    except Exception as e:
        print(f"⚠️  Direct Kannada failed ({e}) — using translate+polish")
        return None


async def _localize(text: str, language: str, script: str, user_query: str = "",
                    pipeline_mode: str | None = None) -> dict:
    """
    Turns Groq's output into what the user sees and hears.
    For en/hi the text is already final. For Kannada this runs
    translate -> polish -> (optional) romanize.
    """
    if language != "kn":
        return {
            "display_text": text,
            "speech_text": text,
            "speech_language": language,
            "kannada_pipeline": None,
            "timings": {},
        }

    pipeline = {"translated": False, "polished": False, "romanized": False}
    timings = {}
    mode = pipeline_mode or KANNADA_PIPELINE

    kannada = None
    if mode == "direct":
        started = time.perf_counter()
        kannada = await _direct_kannada(text, user_query)
        timings["direct"] = _ms(started)
        pipeline["direct"] = kannada is not None

    if kannada is None:
        kannada = await _translate_and_polish(text, user_query, pipeline, timings)
        if kannada is None:
            # Never silently answer a Kannada speaker in English — log it loudly.
            print("⚠️  Sarvam translation failed — replying in English for this Kannada query")
            pipeline["fallback"] = "english"
            return {
                "display_text": text,
                "speech_text": text,
                "speech_language": "en",
                "kannada_pipeline": pipeline,
                "timings": timings,
            }

    display_text = kannada
    if script == "romanized":
        started = time.perf_counter()
        roman = await asyncio.to_thread(romanize, kannada, "kn")
        timings["romanize"] = _ms(started)
        if roman:
            display_text = roman
            pipeline["romanized"] = True
        else:
            print("⚠️  Romanization failed — showing Kannada script instead")

    return {
        "display_text": display_text,
        "speech_text": kannada,         # TTS always gets Kannada script
        "speech_language": "kn",
        "kannada_pipeline": pipeline,
        "timings": timings,
    }


async def _translate_and_polish(text: str, user_query: str, pipeline: dict, timings: dict):
    """Sarvam translation, then the 120B polish. None if translation fails."""
    started = time.perf_counter()
    kannada = await asyncio.to_thread(translate_to_kannada, text)
    timings["translate"] = _ms(started)
    if not kannada:
        return None
    pipeline["translated"] = True

    started = time.perf_counter()
    kannada, pipeline["polished"] = await _polish_kannada(kannada, user_query)
    timings["polish"] = _ms(started)
    return kannada


async def _make_reply_text(engine2_result, knowledge_result, language, script, query,
                           intent_id, needs_escalation, debug, timings):
    """Steps 1 (English/Hindi text) and 2 (Kannada pipeline / script)."""
    # ── 1. Generate the base text ────────────────────────────────────
    generation_ok = True
    started = time.perf_counter()
    try:
        if intent_id == "greet":
            debug["path"] = "greet"
            base_text = await _generate_simple(GREET_INSTRUCTION, language, script, query)
        elif (intent_id in BRANCH_SPECIFIC_INTENTS and not needs_escalation
              and not (engine2_result.get("entities") or {}).get("branch")
              and not (engine2_result.get("entities") or {}).get("rank")):   # rank -> predictor answers
            # (A very worried parent still gets the warm grounded reply.)
            debug["path"] = "ask_branch"
            base_text = await _generate_simple(ASK_BRANCH_INSTRUCTION, language, script, query)
        elif intent_id == "fallback" and not needs_escalation:
            # A worried/frustrated user with an out-of-scope question
            # gets escalation (grounded path below), not a polite redirect.
            debug["path"] = "fallback"
            base_text = await _generate_simple(FALLBACK_INSTRUCTION, language, script, query)
        elif (not (knowledge_result or {}).get("found") and not needs_escalation
              and engine2_result.get("response_mode", "informational") in FACT_ONLY_MODES):
            # Fix A: no data -> fixed message, the model is never asked.
            debug["path"] = "not_found"
            timings["generate"] = _ms(started)
            return True, {**_fixed_reply(NOT_FOUND_MESSAGES, language, script), "kannada_pipeline": None}
        else:
            debug["path"] = "grounded"
            base_text = await _generate_grounded(engine2_result, knowledge_result, language, script)
    except Exception as e:
        print(f"❌ Response generation error: {type(e).__name__}: {e}")
        generation_ok = False
        debug["error"] = str(e)
    timings["generate"] = _ms(started)

    # ── 2. Localize (Kannada pipeline / script) ──────────────────────
    if generation_ok:
        localized = await _localize(base_text, language, script, query)
        debug["kannada_pipeline"] = localized["kannada_pipeline"]
        timings.update(localized.get("timings", {}))
    else:
        message = ERROR_MESSAGES[(language, script)]
        native_message = ERROR_MESSAGES[(language, "native")]
        localized = {
            "display_text": message,
            "speech_text": native_message if language == "kn" else message,
            "speech_language": language,
        }

    return generation_ok, localized


# ── Main entry point ────────────────────────────────────────────────────

async def generate_response(
    engine2_result: dict,
    knowledge_result: dict,
    conversation_context: list = None,
    script: str | None = None,
    include_audio: bool = True,
) -> dict:
    """
    Main entry point for Engine 5.

    engine2_result:       full output from classify_intent() (Engine 2)
    knowledge_result:     full output from fetch_knowledge() (Engine 3);
                          may be None for greet/fallback
    conversation_context: reserved for the Memory Engine (Engine 4) —
                          not used yet; adding it later needs no redesign here
    script:               "native", "romanized", or None for the language default
    include_audio:        False skips TTS (faster, for text-only testing)

    Returns:
        {
          "success": bool,              # False only if Groq generation failed
          "response_text": str,         # what to SHOW (in the chosen script)
          "response_text_native": str,  # native-script text (what was spoken)
          "language": "en" | "hi" | "kn",
          "script": "native" | "romanized",
          "audio_base64": str | None,   # WAV audio, base64
          "audio_format": "wav" | None,
          "tts_success": bool,
          "debug": {...}                # path taken, pipeline steps, errors
        }
    Never raises — every failure has a fallback.
    """
    intent_id = engine2_result.get("intent", "fallback")
    language = _resolve_language(engine2_result.get("language", "en"))
    script = _resolve_script(language, script)
    needs_escalation = engine2_result.get("needs_escalation", False)
    query = engine2_result.get("query", "")

    debug = {"path": None, "kannada_pipeline": None, "error": None, "tts_error": None}
    timings = {}   # milliseconds per step, returned in debug["timings_ms"]

    # ── 1+2. Reply text (from the reply cache when possible) ─────────
    cache_key = _reply_cache_key(engine2_result, knowledge_result, language, script, query)
    cached = _reply_cache_get(cache_key)
    if cached is not None:
        generation_ok = True
        localized = dict(cached["localized"])
        debug["path"] = cached["path"]
        debug["kannada_pipeline"] = cached["kannada_pipeline"]
        debug["reply_cache"] = "hit"
    else:
        generation_ok, localized = await _make_reply_text(
            engine2_result, knowledge_result, language, script, query,
            intent_id, needs_escalation, debug, timings,
        )
        # Remember it only if it came out fully right (no fallback).
        if (cache_key and generation_ok and localized["speech_language"] == language
                and not (localized.get("kannada_pipeline") or {}).get("fallback")):
            _reply_cache_put(cache_key, {
                "localized": dict(localized),
                "path": debug["path"],
                "kannada_pipeline": debug["kannada_pipeline"],
            })
        debug["reply_cache"] = "miss" if cache_key else "not_cacheable"

    # Contact details: show everything, but speak one short sentence.
    if (intent_id in CONTACT_SPEECH_INTENTS and generation_ok
            and localized.get("speech_language") in CONTACT_SPEECH):
        localized = {**localized, "speech_text": CONTACT_SPEECH[localized["speech_language"]]}
        debug["short_speech"] = True

    # ── 3. Voice ─────────────────────────────────────────────────────
    audio_base64, audio_format, tts_success = None, None, False
    if include_audio:
        started = time.perf_counter()
        tts = await asyncio.to_thread(
            synthesize_speech, localized["speech_text"], localized["speech_language"]
        )
        timings["tts"] = _ms(started)
        if tts["success"]:
            audio_base64 = tts["audio_base64"]
            audio_format = tts["audio_format"]
            tts_success = True
        else:
            debug["tts_error"] = tts.get("error")

    debug["timings_ms"] = timings

    return {
        "success": generation_ok,
        "response_text": localized["display_text"],
        "response_text_native": localized["speech_text"],
        "speech_language": localized["speech_language"],   # language of the spoken text
        "language": language,
        "script": script,
        "audio_base64": audio_base64,
        "audio_format": audio_format,
        "tts_success": tts_success,
        "debug": debug,
    }
