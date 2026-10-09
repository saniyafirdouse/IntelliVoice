# IntelliVoice — Frontend

Multilingual voice assistant for SVIT admissions (English · ಕನ್ನಡ · हिंदी).
**React + TypeScript** (built with Vite, styled with Tailwind CSS) and a small **Node.js / Express** server.

```
Browser ──► Express server (Node.js, :3001) ──► FastAPI backend (Python, :8000)
            serves the React app                 Whisper → 6 engines → Sarvam TTS
            forwards /api and /auth
```

## 1. First-time setup

1. Install **Node.js 20 LTS** (or newer) from https://nodejs.org.
2. In this folder, run:

   ```bash
   npm install
   copy .env.example .env      # Windows   (Mac/Linux: cp .env.example .env)
   ```

## 2. Run it

| Command | What it does |
|---|---|
| `npm run demo` | **No backend needed.** Sample replies, clearly labelled "Demo mode". Open http://localhost:5173 |
| `npm run dev` | Development with the real backend. Start San's FastAPI on port 8000 first, then open http://localhost:5173 |
| `npm run build` | Type-checks everything and builds the final site into `dist/` |
| `npm start` | Runs the built site and the forwarding server together on http://localhost:3001 (use this for the showcase) |

With `npm run dev` / `npm run demo`, changes to the code appear in the browser instantly.

For the microphone to work, open the site at `localhost` (as above) and allow microphone access when the browser asks.

## 3. Folder structure

```
public/assets/          campus photos + SVIT logo
server/
  index.ts              Express server: serves the app, forwards /api + /auth to FastAPI
  demo.ts               sample replies for demo mode
src/
  main.tsx, App.tsx     app entry + page routes (/, /chat, /about, /help, /login, /signup)
  components/           shared pieces: SiteHeader, SiteFooter, PageShell, FloatingMicButton, Icon …
  context/              AuthContext (optional login), LanguageContext (speaking + reply language)
  hooks/                useRecorder (microphone), useSectionBackground, useOpenChat, useElapsed
  lib/                  api.ts (calls to the backend), types.ts (response shapes), storage, audio
  data/faq.ts           Help & FAQ questions
  pages/
    HomePage.tsx, AboutPage.tsx, FaqPage.tsx, NotFoundPage.tsx
    chat/               ChatPage + its parts (useChat state, PipelineBar, SidePanels, Messages, MicDock)
    auth/               LoginPage, SignupPage
  styles/               page styles from the Stitch design, scoped per page
tailwind.config.ts      design tokens (colours, fonts, sizes) exported from Stitch
API_CONTRACT.md         exactly what the backend must accept and return
```

## 4. Common changes

- **Backend address** → `BACKEND_URL` in `.env`
- **Text on Home / About** → the lists at the top of `HomePage.tsx` / `AboutPage.tsx`
- **FAQ questions** → `src/data/faq.ts`
- **Language options** (speaking / reply, incl. "English letters") → `src/context/LanguageContext.tsx`
- **Where admins go after signing in** → `ADMIN_HOME` in `src/pages/auth/LoginPage.tsx`
- **Better campus photo** → replace the file in `public/assets/` with the same name

## 5. Git

Don't commit `node_modules/`, `dist/` or `.env`. The `.gitignore` already excludes them.
