// Help & FAQ content. Answers are NOT stored here on purpose:
// every question opens Voice Chat, so the answer comes from the SVIT admissions database.

export interface FaqCategory {
  id: string;
  pill: string;
  icon: string;
  title: string;
  questions: string[];
}

export const FAQ_CATEGORIES: FaqCategory[] = [
  {
    id: "admissions",
    pill: "Admissions & Cutoffs",
    icon: "how_to_reg",
    title: "Admissions & Cutoffs (KCET & COMEDK)",
    questions: [
      "How do I apply to SVIT? What are the official CET & COMEDK codes?",
      "What are the expected eligibility cutoff ranks for CSE, ISE, and AI branches?",
    ],
  },
  {
    id: "seat-matrix",
    pill: "Branch & Seat Matrix",
    icon: "account_tree",
    title: "Branch & Seat Matrix",
    questions: ["What is the sanctioned undergraduate intake and quota distribution per branch?"],
  },
  {
    id: "hostels",
    pill: "Hostels & Amenities",
    icon: "apartment",
    title: "Hostels & Campus Amenities",
    questions: ["What are the hostel accommodations, mess plans, and transport routes?"],
  },
  {
    id: "placements",
    pill: "Placements & Recruitment",
    icon: "trending_up",
    title: "Placements & Campus Recruitment",
    questions: ["What is the highest package, average CTC, and list of recruiting companies?"],
  },
  {
    id: "voice-pipeline",
    pill: "6-Engine Voice Pipeline",
    icon: "graphic_eq",
    title: "Voice Engine FAQ (6-Engine Multilingual Architecture)",
    questions: ["How is code-mixed Kannada, Hindi, and English auto-detected through the 6-engine pipeline?"],
  },
];

export const HOW_IT_WORKS = [
  { n: "01", icon: "chat", title: "Open Voice Chat", body: "Go to the Voice Chat page. No sign-up needed." },
  { n: "02", icon: "mic", title: "Tap the Mic", body: "Tap the microphone button and ask your admission question." },
  { n: "03", icon: "translate", title: "Speak Your Language", body: "Ask in English, Kannada, Hindi or a natural mix. Your speech is converted to text using OpenAI Whisper." },
  { n: "04", icon: "volume_up", title: "Hear the Answer", body: "IntelliVoice finds the answer in the SVIT admissions database and replies in your language, spoken aloud by Sarvam AI voices." },
];

export const RELIABILITY = [
  { icon: "verified", title: "Grounded Answers", body: "Facts come only from the SVIT admissions database. The AI phrases answers but never invents information." },
  { icon: "translate", title: "Understands Mixed Language", body: "Handles Kannada-English and Hindi-English mixed speech naturally." },
  { icon: "forum", title: "Remembers Your Conversation", body: "Follow-up questions use context from earlier in the same chat." },
  { icon: "support_agent", title: "Human Help When Needed", body: "If IntelliVoice can't answer, it directs you to the SVIT admissions office." },
];
