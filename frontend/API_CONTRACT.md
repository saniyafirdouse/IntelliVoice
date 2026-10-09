# IntelliVoice — Frontend ↔ Backend API Contract

**Status:** proposal from the frontend (Pooja), to be confirmed by San (backend).
The frontend (React + TypeScript, with a Node.js/Express server) is already built against this. If the backend needs a different shape, change it here first and tell the frontend team. The matching TypeScript types are in `src/lib/types.ts`.

**How requests flow:** browser → Express server (Node.js, port 3001) → FastAPI (port 8000).
The browser only talks to the Express server, which forwards every `/api/...` and `/auth/...` request to FastAPI unchanged. FastAPI's address is set by `BACKEND_URL` in `.env` (default `http://localhost:8000`).

---

## 1. Ask a question — `POST /api/query`

One endpoint for both voice and typed questions. The request is **`multipart/form-data`**.

| Field | Required | Notes |
|---|---|---|
| `session_id` | yes | Created by the browser (UUID) and kept for the whole chat. The Memory Engine should key on this. "New Chat" sends a new ID. |
| `audio` | one of `audio` / `text` | Recorded voice, usually `audio/webm` (Opus codec) from Chrome/Edge, filename `question.webm`. Whisper reads this through ffmpeg, so **ffmpeg must be installed** on the backend machine. Max ~30 s. |
| `text` | one of `audio` / `text` | Typed question, or a quick-question button. Max 500 characters. Skip Whisper for these. |
| `context` | no | JSON string from the optional "Your Query Context" box, e.g. `{"rank": 25000, "category": "GM", "branch": "CSE"}`. Any value may be `null`. |
| `speech_language` | yes | What the user said they will **speak / type** in: `auto`, `en`, `kn` or `hi`. For voice, pass it to Whisper as the `language` setting (skip it for `auto`). With `auto`, Engine 1 (MuRIL) detects the language and code-mixing as usual. |
| `response_language` | yes | What the user wants the **reply** in: `same` (same language as the question), `en`, `kn` (Kannada script), `kn-Latn` (Kannada in English letters), `hi` (Hindi script), `hi-Latn` (Hindi in English letters). Both the text and the spoken audio should follow this choice. |

Header `Authorization: Bearer <token>` is sent only if the user is signed in. **Login is optional**, so the endpoint must work without it.

### Response — `200 OK`, JSON

```json
{
  "session_id": "same id that was sent",
  "transcript": "CSE fee kitni hai?",

  "language": { "primary": "hi", "confidence": 0.87, "is_code_switched": true },

  "understanding": {
    "intent": "fee_structure",
    "confidence": 0.94,
    "entities": { "branch": "CSE", "exam": "KCET" },
    "emotion": "neutral",
    "response_mode": "informational"
  },

  "memory": { "topic": "Fee Structure", "context_used": ["CSE", "KCET"] },

  "response": {
    "text": "Spoken-style answer, in the language/script the user chose.",
    "language": "kn",
    "text_romanized": "Optional: same answer in English letters (only when language is kn or hi)"
  },

  "data": null,

  "audio": { "format": "wav", "base64": "<Sarvam Bulbul audio, base64>", "voice": "Simran" },

  "escalation": { "needed": false, "message": null, "contact": null },

  "source": "SVIT Admissions Database"
}
```

**What the page does with each field**

| Field | Shown as |
|---|---|
| `transcript` | Replaces "Transcribing your voice…" in the user's bubble. Send it for typed questions too (just echo the text). |
| `language` | Badge on the user's bubble: "Hindi detected (code-mixed) · 87%". `primary` must be `en`, `hi` or `kn`. |
| `understanding` | Left "Engine 2: Understanding" panel. `confidence` is 0–1. `entities` is a flat object, and values may be strings or arrays. `response_mode` is one of `informational`, `reassurance`, `comparison`, `recommendation`, `escalation`. |
| `memory.topic` / `memory.context_used` | The "Current Topic" banner and the "Using context: …" tag. Leave `topic` null to keep the banner hidden. |
| `response.text` | The answer bubble. Plain text, no markdown. |
| `response.language` | The language/script `text` is written in: `en`, `kn`, `kn-Latn`, `hi` or `hi-Latn`. Shown as the reply's label (e.g. "Kannada (English letters)"). When `response_language` was `same`, send the language actually used. |
| `response.text_romanized` | Optional. When present and `response.language` is `kn` or `hi`, a "Show in English letters" button appears under the reply. |
| `data` | Optional table, e.g. for comparisons: `{ "title": "...", "columns": ["Category", "Cutoff"], "rows": [["GM", "18420"]] }`. Values must come from MongoDB. Use `null` when there's no table. |
| `audio` | Play button and auto-play. `format`: `wav` (default) / `mp3`. Instead of `base64` you can send `"url"`. If TTS fails, send `"audio": null`, and the text still shows. |
| `escalation` | When `response_mode` is `escalation` or `needed` is true, a "Need help from the admissions office?" card appears. `contact` may be `{ "phone": "...", "email": "..." }`, and **only with verified SVIT details**. |
| `source` | Small "Source: …" line under the answer. |

Every field except `response.text` is optional, and the page simply hides what's missing. So the backend can start with only `transcript`, `response.text` and `audio`, and add the rest later.

### Errors

Return a normal HTTP error with FastAPI's default shape, and the message is shown to the user as-is:

```json
{ "detail": "I couldn't hear anything in that recording. Please try again." }
```

Examples: `400` empty/unreadable audio, `422` missing both `audio` and `text`, `500` engine failure. The page gives up after **45 seconds** and shows a "took too long" message.

---

## 2. Login / sign-up (optional accounts)

Used by `login.html` / `signup.html` through `assets/auth.js`. JSON bodies.

- `POST /auth/signup` with `{ "name", "email", "phone", "password" }` returns `201 { "token", "user": { "name", "email", "role": "student" } }`
- `POST /auth/login` with `{ "email", "password", "role": "student" | "admin" }` returns `200 { "token", "user": { "name", "email", "role" } }`
- Errors return `4xx { "detail": "message for the user" }`

Passwords must be **stored hashed** (e.g. bcrypt via `passlib`), never in plain text. There's no public admin sign-up: the team creates admin accounts directly in MongoDB.

---

## 3. CORS

Not needed. The browser never calls FastAPI directly: the Express server forwards the requests, so they look same-origin to the browser. If FastAPI isn't running, the Express server answers `502` with a clear `detail` message, which the chat page shows.

---

## 4. Testing without the backend

Run `npm run demo` in the frontend folder. The Express server then answers `/api/query` and `/auth/*` itself with sample replies, labelled "Demo mode · sample reply" and playing a short beep instead of a voice. That lets you test the whole page flow without any real data.
