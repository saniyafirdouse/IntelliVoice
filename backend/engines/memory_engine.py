"""
engines/memory_engine.py — Engine 4: Session Memory
IntelliVoice (SVIT admission voice assistant)
 
What this engine does
---------------------
Remembers what was said earlier in a conversation so follow-up questions work.
 
    Turn 1: "What is the CSE fee under management quota?"
            entities = {branch: CSE, quota: management}
    Turn 2: "And for ECE?"
            entities = {branch: ECE}                      <- Engine 2 only sees ECE
            resolved = {branch: ECE, quota: management}   <- Memory fills in quota
 
Where it sits in the pipeline (routes/voice.py):
    Engine 1 (language) -> Engine 2 (intent/entities)
      -> Memory.resolve_entities()   # fill gaps from earlier turns
      -> Engine 3 (MongoDB lookup with the resolved entities)
      -> Engine 5 (response, given Memory.get_context() as conversation_context)
      -> Memory.add_turn()           # save this turn for the next one
 
Storage is an in-memory dict for now. Every read/write goes through the
methods below, so swapping to MongoDB later only changes this file.
"""
 
import time
from copy import deepcopy
from typing import Optional
 
# Keep only the most recent turns per session (spoken chats are short).
MAX_TURNS_PER_SESSION = 20
 
# A session with no activity for this long is treated as finished.
SESSION_TTL_SECONDS = 60 * 60  # 1 hour
 
 
class MemoryEngine:
    def __init__(self):
        # session_id -> {"turns": [...], "active_entities": {...},
        #                "language": str | None, "last_active": float}
        self._sessions: dict[str, dict] = {}
 
    # ------------------------------------------------------------------ #
    # internal helpers
    # ------------------------------------------------------------------ #
    def _new_session(self) -> dict:
        return {
            "turns": [],
            "active_entities": {},
            "language": None,
            "last_active": time.time(),
        }
 
    def _get_session(self, session_id: str, create: bool = True) -> Optional[dict]:
        session = self._sessions.get(session_id)
 
        # Expire stale sessions lazily (no background job needed).
        if session and time.time() - session["last_active"] > SESSION_TTL_SECONDS:
            del self._sessions[session_id]
            session = None
 
        if session is None and create:
            session = self._new_session()
            self._sessions[session_id] = session
        return session
 
    @staticmethod
    def _clean(entities: Optional[dict]) -> dict:
        """Drop empty values so they never overwrite real remembered ones."""
        if not entities:
            return {}
        return {k: v for k, v in entities.items() if v not in (None, "", [], {})}
 
    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #
    def resolve_entities(
        self, session_id: str, current_entities: Optional[dict], needs_memory: bool
    ) -> dict:
        """
        Merge this turn's entities with what the user said earlier.
 
        - needs_memory=False -> return this turn's entities unchanged (no-op).
        - needs_memory=True  -> start from remembered entities, then let anything
                                the user said THIS turn override them.
 
        The returned dict is what you pass to Engine 3 as the search filter,
        so the DB query and the conversation always agree.
        """
        current = self._clean(current_entities)
        if not needs_memory:
            return deepcopy(current)
 
        session = self._get_session(session_id, create=False)
        if session is None:
            return deepcopy(current)
 
        merged = deepcopy(session["active_entities"])
        merged.update(current)  # new info wins over old info
        return merged
 
    def add_turn(
        self,
        session_id: str,
        user_text: str,
        intent: str,
        entities: Optional[dict],
        response_text: str,
        language: Optional[str] = None,
    ) -> None:
        """
        Save one completed turn. Call AFTER the response is generated.
        `entities` should be the RESOLVED entities (output of resolve_entities),
        so the remembered state matches what was actually answered.
        """
        session = self._get_session(session_id)
        clean_entities = self._clean(entities)
 
        session["turns"].append(
            {
                "turn_number": len(session["turns"]) + 1,
                "timestamp": time.time(),
                "user_text": user_text,
                "intent": intent,
                "entities": deepcopy(clean_entities),
                "response_text": response_text,
                "language": language,
            }
        )
        if len(session["turns"]) > MAX_TURNS_PER_SESSION:
            session["turns"] = session["turns"][-MAX_TURNS_PER_SESSION:]
 
        session["active_entities"].update(clean_entities)
        if language:
            session["language"] = language
        session["last_active"] = time.time()
 
    def get_context(self, session_id: str, last_n: int = 3) -> dict:
        """
        Summary of the conversation so far, for Engine 5's
        `conversation_context` parameter. Turns are oldest -> newest.
        """
        session = self._get_session(session_id, create=False)
        if session is None:
            return {
                "turns": [],
                "active_entities": {},
                "last_intent": None,
                "language": None,
                "turn_count": 0,
            }
 
        turns = session["turns"]
        recent = turns[-last_n:] if last_n > 0 else []
        return {
            "turns": [
                {
                    "user_text": t["user_text"],
                    "intent": t["intent"],
                    "response_text": t["response_text"],
                }
                for t in recent
            ],
            "active_entities": deepcopy(session["active_entities"]),
            "last_intent": turns[-1]["intent"] if turns else None,
            "language": session["language"],
            "turn_count": len(turns),
        }
 
    def clear_session(self, session_id: str) -> bool:
        """Forget a conversation (e.g. user taps 'New chat'). True if it existed."""
        return self._sessions.pop(session_id, None) is not None
 
 
# One shared instance for the whole app — import this in routes/voice.py:
#     from engines.memory_engine import memory_engine
memory_engine = MemoryEngine()
