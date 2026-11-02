"""
utils/sarvam_keys.py — several Sarvam API keys, used one after another (2026-11-01).

Why: on the expo day many visitors use the voice, and one free Sarvam account's
credits can run out. Put the keys of 4-5 accounts in .env; when one key has no
credits left (or is wrong), IntelliVoice switches to the next key by itself and
repeats the same request — the visitor notices nothing.

.env (any of these; the keys are read in this order, duplicates ignored):
    SARVAM_API_KEYS=key_one,key_two,key_three,key_four,key_five
    SARVAM_API_KEY_1=key_one
    SARVAM_API_KEY_2=key_two          ... up to SARVAM_API_KEY_10
    SARVAM_API_KEY=key_one            (the old single key still works)

How it is used: the engines call get_client() instead of SarvamAI(...). It returns
a stand-in that behaves exactly like the Sarvam client
(client.text_to_speech.convert(...), client.text.translate(...),
client.speech_to_text.transcribe(...), client.text.transliterate(...)), but every
call goes through call_with_rotation():
  - "no credits" / payment needed (402), wrong or blocked key (401, 403)
        -> that key is skipped for KEY_RETRY_SECONDS, the next key is tried;
  - too many requests (429)
        -> that key rests for RATE_LIMIT_SECONDS, the next key is tried;
  - any other error (network, bad input, TypeError for an older sarvamai)
        -> raised as before, so the engines' own fallbacks keep working.
If every key is out, the last error is raised (same as one empty key today).

The logs only ever show the key NUMBER ("Sarvam key 2 of 5"), never the key.
"""

import os
import threading
import time

from dotenv import load_dotenv
from sarvamai import SarvamAI

load_dotenv()

KEY_RETRY_SECONDS = 30 * 60     # an exhausted / refused key is tried again after 30 min (credits may be added)
RATE_LIMIT_SECONDS = 60         # a key that said "too many requests" rests this long
MAX_NUMBERED_KEYS = 10

_CREDIT_WORDS = ("credit", "quota", "insufficient", "exhaust", "balance", "payment", "subscription")
_PLACEHOLDER_WORDS = ("your_", "placeholder", "paste", "xxxx", "key_here")


def _read_keys() -> list:
    found = []
    for part in (os.getenv("SARVAM_API_KEYS") or "").split(","):
        found.append(part)
    for i in range(1, MAX_NUMBERED_KEYS + 1):
        found.append(os.getenv(f"SARVAM_API_KEY_{i}") or "")
    found.append(os.getenv("SARVAM_API_KEY") or "")
    keys = []
    for key in found:
        key = key.strip().strip('"').strip("'")
        if not key or key in keys:
            continue
        if any(w in key.lower() for w in _PLACEHOLDER_WORDS):    # an unfilled placeholder line
            continue
        keys.append(key)
    return keys


class _KeyPool:
    def __init__(self):
        self._lock = threading.Lock()
        self._keys = _read_keys()
        self._clients = {}
        self._resting_until = {}     # key index -> time.time() when it may be used again
        self._current = 0
        if self._keys:
            print(f"🔑 Sarvam: {len(self._keys)} API key(s) loaded — using key 1 of {len(self._keys)}")

    @property
    def count(self) -> int:
        return len(self._keys)

    def _client(self, index: int) -> SarvamAI:
        client = self._clients.get(index)
        if client is None:
            client = SarvamAI(api_subscription_key=self._keys[index])
            self._clients[index] = client
        return client

    def _order(self) -> list:
        """Key numbers to try: the current one first, then the others; resting keys last."""
        now = time.time()
        with self._lock:
            n = len(self._keys)
            ring = [(self._current + i) % n for i in range(n)]
        ready = [i for i in ring if self._resting_until.get(i, 0) <= now]
        resting = [i for i in ring if self._resting_until.get(i, 0) > now]
        return ready + resting

    def _rest(self, index: int, seconds: float, reason: str) -> None:
        try:                                   # 2026-11-01: shown on the admin "System health" page
            from utils.system_health import record_problem
            record_problem("Sarvam", f"key {index + 1} of {len(self._keys)}: {reason}")
        except Exception:
            pass
        with self._lock:
            self._resting_until[index] = time.time() + seconds
            if self._current == index and len(self._keys) > 1:
                self._current = (index + 1) % len(self._keys)
                print(f"🔑 Sarvam key {index + 1} of {len(self._keys)}: {reason} — switching to key {self._current + 1}")
            else:
                print(f"🔑 Sarvam key {index + 1} of {len(self._keys)}: {reason}")

    def _use(self, index: int) -> None:
        with self._lock:
            self._resting_until.pop(index, None)
            if self._current != index:
                self._current = index
                print(f"🔑 Sarvam: now using key {index + 1} of {len(self._keys)}")

    def call(self, path: tuple, args: tuple, kwargs: dict):
        if not self._keys:
            raise RuntimeError("No Sarvam API key is set in .env (SARVAM_API_KEYS or SARVAM_API_KEY)")
        last_error = None
        for index in self._order():
            target = self._client(index)
            for name in path:
                target = getattr(target, name)
            try:
                result = target(*args, **kwargs)
            except TypeError:
                raise                      # wrong parameter for this sarvamai version: the engines retry
            except Exception as e:
                kind = _key_problem(e)
                if kind is None:
                    raise                  # not a key problem (network, bad input...): as before
                last_error = e
                if kind == "rate_limit":
                    self._rest(index, RATE_LIMIT_SECONDS, "too many requests")
                else:
                    self._rest(index, KEY_RETRY_SECONDS, "no credits left / key refused")
                continue
            self._use(index)
            return result
        raise last_error


def _key_problem(error: Exception):
    """'credits' (402/401/403 or a credits message), 'rate_limit' (429), or None."""
    status = getattr(error, "status_code", None)
    if status is None:
        status = getattr(getattr(error, "response", None), "status_code", None)
    text = f"{error} {getattr(error, 'body', '')}".lower()
    if status in (401, 402, 403):
        return "credits"
    if status == 429:
        return "credits" if any(w in text for w in _CREDIT_WORDS) else "rate_limit"
    if status is None and any(w in text for w in _CREDIT_WORDS) and ("402" in text or "no credit" in text):
        return "credits"
    return None


class _Path:
    """Behaves like any part of the Sarvam client: client.text.translate(...) -> one rotating call."""

    def __init__(self, pool: _KeyPool, path: tuple = ()):
        self._pool = pool
        self._path = path

    def __getattr__(self, name: str):
        if name.startswith("__"):
            raise AttributeError(name)
        return _Path(self._pool, self._path + (name,))

    def __call__(self, *args, **kwargs):
        return self._pool.call(self._path, args, kwargs)


_pool = None
_pool_lock = threading.Lock()


def get_client() -> _Path:
    """A Sarvam client that moves on to the next API key when one runs out of credits."""
    global _pool
    with _pool_lock:
        if _pool is None:
            _pool = _KeyPool()
        if not _pool.count:
            raise RuntimeError("No Sarvam API key is set in .env (SARVAM_API_KEYS or SARVAM_API_KEY)")
    return _Path(_pool)


def status() -> dict:
    """For logs / admin: how many keys, which one is in use (never the keys themselves)."""
    if _pool is None:
        get_client()
    return {"keys": _pool.count, "in_use": _pool._current + 1 if _pool.count else None,
            "resting": sorted(i + 1 for i, t in _pool._resting_until.items() if t > time.time())}
