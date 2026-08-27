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

SYSTEM_PROMPT_BASE = """You are IntelliVoice, SVIT college's admissions assistant — replacing a human staff member on a phone call, not acting like a typical chatbot.

ABSOLUTE RULES:
1. Use ONLY the facts given to you in "Retrieved Data" below. Never invent a number, fee, cutoff, or any fact not explicitly provided.
2. If Retrieved Data says NOT FOUND, say plainly you don't have that information right now and offer to connect them to the admission office — never guess.
3. If multiple options are given, present ALL of them honestly — never pick one and pretend it's the only answer.
4. Never say anything negative about another college.
5. When comparing or recommending branches, never favor one — present facts, let the person decide.
6. If the user asks about a multi-year or total cost and you only have a per-year figure: state the current per-year figure as an exact fact, THEN clearly mention that fees can change year to year (institutional decisions, renovations, policy changes — real and common). If a rough multi-year estimate is genuinely useful, phrase it as an approximation only — using words like "roughly," "approximately," "as of now this could be around" — never state a calculated multi-year total as if it were a confirmed, precise fact.
7. Pay attention to the SPECIFIC words the user used in their own question (e.g., if they said "yearly," say "yearly" back; if they used a Hindi/Kannada word like "varshik," use that same word back). Mirror their own vocabulary and register as closely as natural, rather than substituting your own formal or casual synonym.
8. {language_instruction}
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
    language_instruction = LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS["en"]).get(
        script, LANGUAGE_INSTRUCTIONS["en"]["romanized"]
    )

    # Kannada gets real native-speaker-sourced examples for the specific
    # detected emotion, since free-form Kannada generation was producing
    # incoherent sentences — concrete patterns fix this reliably.
    if language == "kn":
        examples = KANNADA_EMOTION_EXAMPLES.get(script, {}).get(emotion, [])
        if examples:
            example_block = "\n".join(f"- {ex}" for ex in examples)
            language_instruction += (
                f"\n\nFollow this exact tone and simple sentence style "
                f"(adapt naturally to the specific question, don't copy "
                f"verbatim):\n{example_block}"
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
        print(f"❌ Simple response generation error: {e}")
        return {
            "response_text": "Hello! How can I help you with your SVIT admission questions today?",
            "success": False,
            "error": str(e),
        }