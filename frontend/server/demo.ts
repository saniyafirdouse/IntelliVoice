import { Router } from "express";
import multer from "multer";

/**
 * DEMO MODE — sample answers so the frontend can be shown without the Python backend.
 * Every reply is clearly labelled "demo" and contains no real SVIT data.
 */

const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 10 * 1024 * 1024 } });

/** 0.6 s soft beep as base64 WAV, so audio playback can be tested. */
function demoTone(): string {
  const rate = 16_000;
  const n = Math.floor(rate * 0.6);
  const buf = Buffer.alloc(44 + n * 2);
  buf.write("RIFF", 0); buf.writeUInt32LE(36 + n * 2, 4); buf.write("WAVE", 8);
  buf.write("fmt ", 12); buf.writeUInt32LE(16, 16); buf.writeUInt16LE(1, 20); buf.writeUInt16LE(1, 22);
  buf.writeUInt32LE(rate, 24); buf.writeUInt32LE(rate * 2, 28); buf.writeUInt16LE(2, 32); buf.writeUInt16LE(16, 34);
  buf.write("data", 36); buf.writeUInt32LE(n * 2, 40);
  for (let i = 0; i < n; i++) {
    const env = Math.min(1, i / 800, (n - i) / 800);
    buf.writeInt16LE(Math.round(Math.sin((2 * Math.PI * 660 * i) / rate) * 6000 * env), 44 + i * 2);
  }
  return buf.toString("base64");
}
const TONE = demoTone();

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

// Sample (non-factual) reply in each language/script the user can choose.
const DEMO_TEXT: Record<string, string> = {
  en: "This is a sample reply in demo mode. Once the backend is connected, the real answer from the SVIT admissions database will appear here.",
  kn: "ಇದು ಡೆಮೊ ಮೋಡ್‌ನ ಮಾದರಿ ಉತ್ತರ. ಬ್ಯಾಕೆಂಡ್ ಸಂಪರ್ಕವಾದ ನಂತರ SVIT admissions database-ನಿಂದ ನಿಜವಾದ ಉತ್ತರ ಇಲ್ಲಿ ಬರುತ್ತದೆ.",
  "kn-Latn": "Idu demo mode-na maadari uttara. Backend connect aada mele SVIT admissions database-inda nijavaada uttara illi baratte.",
  hi: "यह डेमो मोड का एक नमूना जवाब है। बैकएंड जुड़ने के बाद SVIT admissions database से असली जवाब यहाँ दिखेगा।",
  "hi-Latn": "Yeh demo mode ka ek sample jawab hai. Backend judne ke baad SVIT admissions database se asli jawab yahan dikhega.",
};
const ROMAN_OF: Record<string, string> = { kn: "kn-Latn", hi: "hi-Latn" };
const pick = (v: unknown) => (typeof v === "string" ? v : "");

export function demoRouter(): Router {
  const router = Router();

  router.post("/api/query", upload.single("audio"), async (req, res) => {
    const isVoice = !!req.file;
    const text = typeof req.body.text === "string" ? req.body.text.trim() : "";
    if (!isVoice && !text) {
      res.status(422).json({ detail: "Please ask a question by voice or text." });
      return;
    }
    await wait(1500); // feel like a real pipeline
    const wantsHuman = /talk to|human|officer|admissions office/i.test(text);
    const speech = pick(req.body.speech_language) || "auto";
    const asked = speech !== "auto" ? speech : isVoice ? "hi" : "en"; // pretend detection in demo
    const chosen = pick(req.body.response_language) || "same";
    const replyLang = chosen === "same" ? asked : chosen;
    const replyText = DEMO_TEXT[replyLang] ?? DEMO_TEXT.en;
    const roman = ROMAN_OF[replyLang] ? DEMO_TEXT[ROMAN_OF[replyLang]] : undefined;
    res.json({
      demo: true,
      session_id: req.body.session_id,
      transcript: isVoice ? "(demo) CSE fee kitni hai?" : text,
      language: { primary: asked, confidence: 0.9, is_code_switched: isVoice && speech === "auto" },
      understanding: {
        intent: wantsHuman ? "talk_to_human" : "demo_intent",
        confidence: 0.9,
        entities: { branch: "CSE" },
        emotion: "neutral",
        response_mode: wantsHuman ? "escalation" : "informational",
      },
      memory: { topic: "Demo conversation", context_used: ["CSE"] },
      response: { text: replyText, language: replyLang, text_romanized: roman },
      data: null,
      audio: { format: "wav", base64: TONE, voice: "demo tone" },
      escalation: wantsHuman
        ? { needed: true, message: "In the real system, the admissions office contact details appear here.", contact: null }
        : { needed: false },
      source: "Demo mode (no database)",
    });
  });

  router.post("/auth/login", (req, res) => {
    const { email, password, role } = req.body ?? {};
    if (!email || !password) {
      res.status(400).json({ detail: "Please enter your email and password." });
      return;
    }
    const name = String(email).split("@")[0].replace(/[._-]+/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
    res.json({ token: "demo-token", user: { name: `${name} (demo)`, email, role: role === "admin" ? "admin" : "student" } });
  });

  router.post("/auth/signup", (req, res) => {
    const { name, email } = req.body ?? {};
    res.status(201).json({ token: "demo-token", user: { name: `${name} (demo)`, email, role: "student" } });
  });

  return router;
}
