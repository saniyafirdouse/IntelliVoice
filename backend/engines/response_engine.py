"""
Engine 5 — Response Generation

Takes Engine 2's classification output + Engine 3's retrieved knowledge,
and generates a natural, empathetic response using Groq — strictly
constrained to only use provided facts (RAG principle), never invent
information. This is a communication layer only; all facts and
decisions were already made by Engines 2 and 3.
"""

import os
from groq import Groq
from dotenv import load_dotenv
from engines.kannada_translator import translate_to_kannada

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "openai/gpt-oss-20b"  # same model already validated for intent classification

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
    "kn": {
        "romanized": (
            "Respond in natural, conversational Kannada WRITTEN IN ROMAN/"
            "ENGLISH LETTERS, NOT Kannada script. The way real people actually "
            "text/speak on a phone call. Keep technical terms and numbers in "
            "English/numerals.\n"
            "Example of RIGHT: 'CSE fee 145000 rupees ide, yearly.'"
            "When responding in reassurance mode specifically, use simple sentence "
            "patterns like these (adapt naturally, don't copy word-for-word):\n"
            "- Acknowledge: 'Nimma chinte arthaagutte' (I understand your worry)\n"
            "- Normalize: 'Tumba parents ge idee thara chinte irutte' (many parents "
            "have this same worry)\n"
            "- Reassure: 'SVIT alli mentors mattu faculty support ide, students ge "
            "sahaya maaduttare' (SVIT has mentor and faculty support, they help "
            "students)\n"
            "- Invite more: 'Innu yenadaru kelbeku antha anisidre, keliri' (if you "
            "want to ask anything else, please ask)\n"
            "Keep grammar SIMPLE — avoid complex sentence structures, since overly "
            "elaborate Kannada grammar is more likely to come out wrong."
        ),
        "native": (
            "Respond in natural, conversational Kannada WRITTEN IN KANNADA "
            "SCRIPT (ಕನ್ನಡ ಲಿಪಿ), for readers who read Kannada script. Even in "
            "Kannada script, keep technical terms (branch names, exam names, "
            "quota names, course names, and numbers) in English/Roman letters "
            "and numerals — do not transliterate them into Kannada script."
            "When responding in reassurance mode specifically, use simple sentence "
            "patterns like these (adapt naturally, don't copy word-for-word):\n"
            "- Acknowledge: 'Nimma chinte arthaagutte' (I understand your worry)\n"
            "- Normalize: 'Tumba parents ge idee thara chinte irutte' (many parents "
            "have this same worry)\n"
            "- Reassure: 'SVIT alli mentors mattu faculty support ide, students ge "
            "sahaya maaduttare' (SVIT has mentor and faculty support, they help "
            "students)\n"
            "- Invite more: 'Innu yenadaru kelbeku antha anisidre, keliri' (if you "
            "want to ask anything else, please ask)\n"
            "Keep grammar SIMPLE — avoid complex sentence structures, since overly "
            "elaborate Kannada grammar is more likely to come out wrong."
        ),
    },
}

# Native-speaker-provided example phrases, indexed by emotion, so the
# model has concrete Kannada patterns to follow instead of composing
# complex grammar from scratch (which was producing incoherent output).
# NOTE: sourced from ChatGPT, pending final Bhuvana verification.
KANNADA_EMOTION_EXAMPLES = {
    "romanized": {
        "worried": [
            "Nimma chinte artha agutte. Nimma magu admission bagge worry aagodu sahajave.",
            "Marks bagge chinte maadodu understandable. Students ge college alli guidance mattu support sigutte.",
        ],
        "confused": [
            "Nimge confusion ide anta artha agutte. Naanu simple aagi explain maadthini.",
            "Parvagilla, idanna step by step nodona.",
        ],
        "frustrated": [
            "Nimge frustration aagirodu artha agutte. Naanu nimge clear aagi information kodthini.",
            "Sorry, nimge sariyagi information siglilla andre, naavu idanna clear maadona.",
        ],
        "excited": [
            "Howdu, adu olleya vishaya. Nimma maguvige tumba olleya opportunity aagabahudu.",
            "Super, nimge information helpful aagide anta khushi.",
        ],
        "neutral": [
            "Howdu, nimma question ge answer helthini.",
            "Sure, ee information na nimge clear aagi helthini.",
        ],
    },
    "native": {
        "worried": [
            "ನಿಮ್ಮ ಚಿಂತೆ ಅರ್ಥ ಆಗುತ್ತದೆ. ನಿಮ್ಮ ಮಗು admission ಬಗ್ಗೆ worry ಆಗೋದು ಸಹಜವೇ.",
            "Marks ಬಗ್ಗೆ ಚಿಂತೆ ಮಾಡೋದು understandable. Students ಗೆ college ಅಲ್ಲಿ guidance ಮತ್ತು support ಸಿಗುತ್ತದೆ.",
        ],
        "confused": [
            "ನಿಮಗೆ confusion ಇದೆ ಅಂತ ಅರ್ಥ ಆಗುತ್ತದೆ. ನಾನು simple ಆಗಿ explain ಮಾಡ್ತೀನಿ.",
            "ಪರವಾಗಿಲ್ಲ, ಇದನ್ನ step by step ನೋಡೋಣ.",
        ],
        "frustrated": [
            "ನಿಮಗೆ frustration ಆಗಿರೋದು ಅರ್ಥ ಆಗುತ್ತದೆ. ನಾನು ನಿಮಗೆ clear ಆಗಿ information ಕೊಡ್ತೀನಿ.",
            "Sorry, ನಿಮಗೆ ಸರಿಯಾಗಿ information ಸಿಗ್ಲಿಲ್ಲ ಅಂದ್ರೆ, ನಾವು ಇದನ್ನ clear ಮಾಡೋಣ.",
        ],
        "excited": [
            "ಹೌದು, ಅದು ಒಳ್ಳೆಯ ವಿಷಯ. ನಿಮ್ಮ ಮಗುವಿಗೆ ತುಂಬಾ ಒಳ್ಳೆಯ opportunity ಆಗಬಹುದು.",
            "Super, ನಿಮಗೆ information helpful ಆಗಿದೆ ಅಂತ ಖುಷಿ.",
        ],
        "neutral": [
            "ಹೌದು, ನಿಮ್ಮ question ಗೆ answer ಹೇಳ್ತೀನಿ.",
            "Sure, ಈ information ನ ನಿಮಗೆ clear ಆಗಿ ಹೇಳ್ತೀನಿ.",
        ],
    },
}

KANNADA_ESCALATION_HANDOFF = {
    "romanized": "Naanu nimmanna admission office jothe connect maadthini, avaru nimge sariyada information kodtare.",
    "native": "ನಾನು ನಿಮ್ಮನ್ನ admission office ಜೊತೆ connect ಮಾಡ್ತೀನಿ, ಅವರು ನಿಮಗೆ ಸರಿಯಾದ information ಕೊಡ್ತಾರೆ.",
}

SYSTEM_PROMPT_BASE = """You are IntelliVoice, SVIT college's admissions assistant — replacing a human staff member on a phone call, not acting like a typical chatbot.

ABSOLUTE RULES:
1. Use ONLY the facts given to you in "Retrieved Data" below. Never invent a number, fee, cutoff, or any fact not explicitly provided.
2. If Retrieved Data says NOT FOUND, say plainly you don't have that information right now and offer to connect them to the admission office — never guess.
3. If multiple options are given, present ALL of them honestly — never pick one and pretend it's the only answer.
4. Never say anything negative about another college.
5. When comparing or recommending branches, never favor one — present facts, let the person decide.
6. If the user asks about a multi-year or total cost and you only have a per-year figure: state the current per-year figure as an exact fact, THEN clearly mention that fees can change year to year (institutional decisions, renovations, policy changes — real and common). If a rough multi-year estimate is genuinely useful, phrase it as an approximation only — using words like "roughly," "approximately," "as of now this could be around" — never state a calculated multi-year total as if it were a confirmed, precise fact.
7. Pay attention to the SPECIFIC words the user used in their own question (e.g., if they said "yearly," say "yearly" back; if they used a Hindi/Kannada word like "varshik," use that same word back). Mirror their own vocabulary and register as closely as natural, rather than substituting your own formal or casual synonym.
8. NEVER use markdown formatting — no asterisks for bold, no bullet points/dashes, no headers, no literal "\\n" newline characters. Write ONLY as plain, natural spoken sentences and paragraphs, exactly the way a person would actually talk on a phone call. If comparing multiple things, weave them into flowing sentences (e.g. "CSE focuses on... while AIML focuses on...") instead of a list structure.
9. {language_instruction}
"""

RESPONSE_MODE_INSTRUCTIONS = {
    "informational": (
        "Give a direct, clear answer using the retrieved facts. Keep it "
        "conversational, not robotic or list-like unless the data is "
        "inherently list-shaped (e.g., multiple fee options)."
    ),

    "reassurance": (
        "The person is feeling {emotion}. Follow this exact structure:\n"
        "1. Acknowledge their concern genuinely (1 sentence) — do not jump "
        "straight to facts.\n"
        "2. Normalize it — make clear this is a common, understandable concern.\n"
        "3. If Retrieved Data has relevant facts, weave them in as reassurance. "
        "If Retrieved Data says NOT FOUND, do NOT dwell on that or apologize "
        "for missing data — this is an emotional-support moment, not a data "
        "lookup. Simply reassure them in general, genuine terms (e.g. that "
        "support systems, mentorship, and guidance exist for exactly this "
        "kind of concern) without needing a specific database fact.\n"
        "4. End by inviting them to ask anything else — leave the door open."
    ),

    "comparison": (
        "Present the requested comparison using only the retrieved facts about "
        "each branch. Structure it clearly (e.g., by subject focus, career "
        "scope). End by noting the right choice depends on the student's own "
        "interests — never state one branch is objectively \"better.\""
    ),

    "recommendation": (
        "Base your suggestion on what the person said about their interests. "
        "Never just rank branches. Explain briefly why the suggested branch(es) "
        "fit what they described, using only retrieved facts."
    ),

    "escalation": (
        "Acknowledge whatever you could answer using retrieved facts (if any). "
        "Then clearly and warmly let them know you're connecting them with the "
        "admission office for full support, and that this is normal — not a "
        "failure to help them."
    ),
}


def format_retrieved_data(knowledge_result: dict) -> str:
    """
    Formats Engine 3's output into the exact text block the prompt needs.
    Handles all three real cases Engine 3 actually produces: single match,
    multiple matches (ambiguous query), and not found.
    """
    if not knowledge_result or not knowledge_result.get("found"):
        return "NOT FOUND — no matching record exists yet."

    match_type = knowledge_result.get("match_type", "single")
    data = knowledge_result["data"]

    if match_type == "multiple":
        lines = ["Multiple options — present all of them:"]
        for i, item in enumerate(data, 1):
            lines.append(f"{i}. {item}")
        return "\n".join(lines)

    return str(data)


async def _self_check_kannada(text: str) -> str:
    """
    Safety net for Kannada output specifically, since free-generation has
    shown real grammatical failures in complex sentences. This is a
    second Groq call that reviews and corrects the Kannada text before
    it's returned to the user — an ongoing quality gate for ANY future
    query, not just ones we happened to manually test.
    """
    check_prompt = f"""Review this Kannada sentence for grammatical correctness and natural flow. Kannada speakers should find it clear and natural, not confusing or garbled.

If it is already correct and natural, return it EXACTLY unchanged.
If there is a grammar mistake, confusing phrasing, or incorrect word usage, rewrite it correctly — keep the same meaning, keep any English/technical terms (branch names, numbers, KCET, etc.) exactly as they are, just fix the Kannada grammar/flow.

Text: {text}

Respond with ONLY the final Kannada text, nothing else — no explanation."""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": check_prompt}],
            temperature=0.2,
            max_tokens=1500,  # reasoning model spends tokens on internal
                               # thinking before the visible answer —
                               # 600 wasn't enough headroom for both
        )
        checked_text = response.choices[0].message.content.strip()

        # Safety net: if the check somehow still comes back empty
        # (e.g. hit length limit again), never return blank —
        # fall back to the original, already-good text instead
        if not checked_text:
            return text

        return checked_text
    except Exception:
        return text

async def _casualize_kannada(formal_kannada: str) -> str:
    """
    Takes Sarvam AI's translated Kannada (code-mixed mode) and asks Groq
    to rebalance the English-to-Kannada ratio toward Kannada-dominant,
    accessible spoken language — a constrained edit, not free
    composition. Much safer for Groq than generating Kannada from
    scratch, since correctness is already guaranteed going in.
    """
    prompt = f"""You are refining a Kannada response for IntelliVoice, a college admissions voice assistant. The response will be SPOKEN to a parent over a phone call.
YOUR GOAL:
Rewrite the response so it sounds like NATURAL, SIMPLE, SPOKEN KARNATAKA KANNADA used by a real college counselor talking to a parent.
The response should feel warm, reassuring, clear, and conversational — NOT like a formal written Kannada response or a translated English paragraph.
LENGTH — VERY IMPORTANT:
Keep the response SHORT and easy to listen to.
- The final response should usually be around 3-4 medium to short  sentences.
- dontst mean evrytime the response must restrict to 3 lines itself it can be more or less depending on the query asked.
- It should roughly fit within 3 spoken lines.(dont try to fit every sentence forcefully into 3 lines. keep it natural)
- Do NOT give long explanations.
- Do NOT repeat the same point in different ways.
- Remove unnecessary details or repetition while preserving the important meaning. dont give unwanted words to make the sentence look long.
- The parent should be able to listen to the complete response comfortably without getting bored.
LANGUAGE:
Kannada must be the MAIN language.
Use roughly 70-80% Kannada and 20-30% natural English as a general guideline.
Use only a small amount of commonly used English where it sounds natural, such as:
CSE, college, students, marks, fee, admission, course, faculty, support, guidance, performance, placement, campus, branch, future, worry, doubt, etc.
IMPORTANT: never translate these English words into kannada.
-keep all technical or college related terms in English.
-copy and match the style and tone of the parent/student.
-if they speak more formalised stiff kannada match them.
-if they use English words in between the sentence retain those words in the response, dont replace them with translated kannada.
Do NOT force English into every sentence.
Do NOT use long English phrases such as:
- "right support, guidance, and focused study plan"
- "anxious feel aagodu completely normal"
- "chosen branch-nalli succeed aagabahudu"
- "academic support services"
Instead, use Kannada sentence structure with only a few natural English words.


IMPORTANT BALANCE:
Do NOT make the response too English-heavy.
WRONG:
"Nimma magana future bagge worry aagodu understandable. College alli proper support and guidance sigutte, so he can improve his performance."
Do NOT make it too formal or difficult Kannada either.
WRONG:
"ನಿಮ್ಮ ಮಗನ ಪ್ರಸ್ತುತ ಅಂಕಗಳು ಮತ್ತು ಸಿ.ಎಸ್.ಇ.ಯಲ್ಲಿ ನಿರ್ವಹಿಸುವ ಬಗ್ಗೆ ಅವನಿಗೆ ಇರುವ ಚಿಂತೆಗಳ ಬಗ್ಗೆ ನೀವು ಹೇಗೆ ಭಾವಿಸುತ್ತೀರಿ ಎಂಬುದು ನನಗೆ ಅರ್ಥವಾಗುತ್ತದೆ."
NATURAL STYLE:
"Nimma magana marks kadime ide, CSE alli manage maadtaana antha nimge worry ide antha nanage artha aagutte. Marks swalpa kadime iddru chinte maadbeda. Proper support mattu guidance sikkre, avanu improve maadkobahudu."
SPOKEN KANNADA:
Use simple, everyday Karnataka Kannada that sounds natural when spoken aloud.
AVOID:
- difficult Kannada words
- highly formal Kannada
- literary Kannada
- textbook Kannada
- newspaper-style Kannada
- government/official Kannada
- heavily Sanskritized Kannada
- complicated sentence structures
- unnatural direct translations from English
- overly casual slang
- Gen-Z slang
The parent may be elderly, from a rural area, or comfortable mainly in Kannada. The response must therefore be understandable even with very little English knowledge.
PARENT TONE:
- Be respectful and warm.
- Sound like a helpful college counselor.
- Do not sound robotic.
- Do not sound overly professional.
- Do not speak to the child directly.
- Do not use slang-heavy language.
The ideal style is:
A Kannada-speaking college counselor naturally reassuring a parent during a phone call.
NOT:
An AI reading out a translated paragraph.
NATURALNESS:
Do not simply preserve the original sentence structure if it sounds formal or unnatural.
For example:
FORMAL:
"ನಿಮ್ಮ ಚಿಂತೆಯನ್ನು ನಾನು ಅರ್ಥಮಾಡಿಕೊಳ್ಳುತ್ತೇನೆ."
NATURAL:
"Nimma worry nanage artha aagutte."
FORMAL:
"ವಿದ್ಯಾರ್ಥಿಗಳಿಗೆ ಶೈಕ್ಷಣಿಕ ಮಾರ್ಗದರ್ಶನ ಮತ್ತು ಬೆಂಬಲವನ್ನು ಒದಗಿಸಲಾಗುತ್ತದೆ."
NATURAL:
"Students-ge proper guidance mattu support sigutte."
FORMAL:
"ವಿದ್ಯಾರ್ಥಿಗಳು ತಮ್ಮ ಶೈಕ್ಷಣಿಕ ಕಾರ್ಯಕ್ಷಮತೆಯನ್ನು ಸುಧಾರಿಸಿಕೊಳ್ಳಬಹುದು."
NATURAL:
"Students improve maadkobahudu."
FORMAL:
"ನಿಮಗೆ ಇನ್ನೂ ಯಾವುದೇ ಪ್ರಶ್ನೆಗಳಿದ್ದರೆ, ದಯವಿಟ್ಟು ಕೇಳಿ."
NATURAL:
"Innu yaavudadru doubt idre keliri."
Do not blindly copy these examples. Use them only as examples of the desired level of simplicity and formality.


MEANING AND FACTS:
- Preserve the core meaning of the original response.
- Do NOT add new information.
- Do NOT invent facts, advice, promises, or reassurance.
- Preserve every important number, date, name, branch, course, exam name, fee, percentage, and factual detail exactly.
- Do not change the intent or emotional meaning.
- Do not invent difficult or unusual Kannada words.
- If a commonly used English term is clearer and more natural, keep that term.
IMPORTANT:
You may shorten the response when necessary to meet the 2-3 sentence limit, but do NOT remove important facts or change the meaning.
FINAL CHECK:
Before returning the response, silently check:
1. Is it SHORT enough to comfortably hear on a phone call?
2. Is it around 2-3 short sentences?
3. Is Kannada clearly the main language?
4. Is the English limited and natural?
5. Is the Kannada simple and easy to understand?
6. Does it sound like SPOKEN Karnataka Kannada?
7. Does it avoid formal/textbook Kannada?
8. Does it sound respectful and warm toward a parent?
9. Did I preserve the important meaning and facts?
10. Would a real Kannada-speaking counselor actually say this?
OUTPUT:
Return ONLY the final refined response.
Do not provide explanations.
Do not provide alternatives.
Do not provide translations.
Do not provide Romanization.
Do not use quotation marks.
Do not use bullet points.
Do not use markdown.
Do not add line breaks.
Response to refine:
{formal_kannada}
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1500,
        )
        result = response.choices[0].message.content.strip()
        return result if result else formal_kannada
    except Exception:
        return formal_kannada


async def generate_response(
    engine2_result: dict,
    knowledge_result: dict,
    conversation_context: list = None,
    script: str = "romanized",  # "romanized" (default) or "native"
) -> dict:
    """
    Main entry point for Engine 5.

    engine2_result:      full output from classify_intent() (Engine 2)
    knowledge_result:    full output from fetch_knowledge() (Engine 3)
    conversation_context: optional — for future Memory Engine integration.
                          Defaults to None until Bhuvana's Engine 4 is ready;
                          adding it later requires no redesign here.
    """
    intent_id = engine2_result["intent"]
    language = engine2_result.get("language", "en")
    emotion = engine2_result.get("emotion", "neutral")
    response_mode = engine2_result.get("response_mode", "informational")
    query = engine2_result.get("query", "")

    # ── Special paths with no knowledge lookup at all ──────────────────
    if intent_id == "greet":
        return await _generate_simple(
            "The user is greeting you. Respond with a warm, brief welcome "
            "and invite them to ask their question. No facts needed.",
            language, query,
        )
    if intent_id == "fallback":
        return await _generate_simple(
            "The user's question is unrelated to SVIT admissions (e.g. "
            "weather, sports, general knowledge). Politely acknowledge "
            "it's outside what you can help with, and gently steer the "
            "conversation back to admissions topics. Never attempt to "
            "actually answer the unrelated question.",
            language, query,
        )

    # ── Normal path — build the full constrained prompt ────────────────
    # Kannada is generated in English first, then translated + polished
    # via the 3-step pipeline at the end of this function — Groq does
    # not attempt direct Kannada composition anymore.
    effective_language = "en" if language == "kn" else language
    language_instruction = LANGUAGE_INSTRUCTIONS.get(effective_language, LANGUAGE_INSTRUCTIONS["en"]).get(
        script, LANGUAGE_INSTRUCTIONS["en"]["romanized"]
    )

    system_prompt = SYSTEM_PROMPT_BASE.format(language_instruction=language_instruction)

    mode_instruction = RESPONSE_MODE_INSTRUCTIONS.get(
        response_mode, RESPONSE_MODE_INSTRUCTIONS["informational"]
    )
    if response_mode == "reassurance":
        mode_instruction = mode_instruction.format(emotion=emotion)

    retrieved_data_text = format_retrieved_data(knowledge_result)

    user_message = f"""User's question: {query}

Intent: {intent_id}
Response mode instructions: {mode_instruction}

Retrieved Data: {retrieved_data_text}

Generate the response now, following all rules above."""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.4,  # factual consistency matters more than creativity here
            max_tokens=600,  # reassurance/escalation modes need room for 4-part
                              # structured responses, especially in Hindi/Kannada
                              # where tokenization uses more tokens per word
        )

        text = response.choices[0].message.content.strip()

        if language == "kn":
            formal_kannada = translate_to_kannada(text)
            if formal_kannada:
                text = await _casualize_kannada(formal_kannada)

        return {"response_text": text, "success": True}

    except Exception as e:
        print(f"❌ Response generation error: {e}")

        return {
            "response_text": (
                "I'm sorry, I'm having trouble generating a response right now. "
                "Please contact the SVIT admission office directly for help."
            ),
            "success": False,
            "error": str(e),
        }


async def _generate_simple(instruction: str, language: str, query: str) -> dict:
    """Simplified path for greet/fallback — no retrieved data involved."""
    language_instruction = LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS["en"])
    system_prompt = (
        f"You are IntelliVoice, SVIT college's admissions assistant.\n"
        f"{instruction}\n"
        f"{language_instruction}\n"
        f"Keep it brief — 1-2 sentences."
    )

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            temperature=0.5,
            max_tokens=150,
        )
        text = response.choices[0].message.content.strip()
        return {"response_text": text, "success": True}
    
    except Exception as e:
        print(f"❌ Response generation error: {e}")
        return {
            "response_text": "Hello! How can I help you with your SVIT admission questions today?",
            "success": False,
            "error": str(e),
        }