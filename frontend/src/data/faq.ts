// Help & FAQ content. Admission answers are NOT stored here on purpose: when a question is
// opened, the page asks Eva (text only, no voice) so the answer always comes from the SVIT
// admissions database and is never out of date (2026-11-01; before, it only linked to the chat).

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
    pill: "Admissions",
    icon: "how_to_reg",
    title: "Admissions (KCET, COMEDK, management, DCET, PGCET)",
    questions: [
      "How do I get admission to SVIT?",
      "What are the SVIT college codes for KCET, COMEDK and PGCET?",
      "What documents are needed for admission?",
      "Can diploma holders join SVIT through DCET?",
      "How do I join the MBA program?",
    ],
  },
  {
    id: "branches",
    pill: "Branches, Seats & Cutoffs",
    icon: "account_tree",
    title: "Branches, Seats & Cutoffs",
    questions: [
      "Which engineering branches does SVIT offer?",
      "How many seats does each branch have?",
      "What was the KCET cutoff for CSE last year?",
      "Is ISE still open for admission?",
    ],
  },
  {
    id: "fees",
    pill: "Fees & Scholarships",
    icon: "payments",
    title: "Fees & Scholarships",
    questions: [
      "What is the yearly fee for CSE through KCET?",
      "What is the management quota fee for CSE?",
      "What scholarships are available?",
    ],
  },
  {
    id: "campus",
    pill: "Hostel & Transport",
    icon: "apartment",
    title: "Hostel, Transport & Campus",
    questions: [
      "Is there a hostel for girls and boys, and what is the fee?",
      "Are there college buses, and what is the bus fee?",
      "What facilities are there on campus?",
    ],
  },
  {
    id: "placements",
    pill: "Placements",
    icon: "trending_up",
    title: "Placements & Recruiters",
    questions: [
      "What is the highest and average placement package?",
      "Which companies recruit from SVIT?",
    ],
  },
  {
    id: "eva",
    pill: "About Eva",
    icon: "graphic_eq",
    title: "About Eva (IntelliVoice)",
    questions: [
      "Which languages can I speak to Eva in?",
      "Are Eva's answers reliable?",
      "Do I need to sign in to use Eva?",
    ],
  },
];

// 2026-11-01: questions about Eva herself are answered here (they are not admission data).
// Every other question gets Eva's live answer from the SVIT admissions database when opened.
export const STATIC_ANSWERS: Record<string, string> = {
  "Which languages can I speak to Eva in?":
    "English, Kannada and Hindi, including a natural mix like \"CSE fees eshtu?\" or \"hostel ki fees kitni hai?\". Eva replies in the same language, or in the one you choose from the language menu, also in English letters if you prefer.",
  "Are Eva's answers reliable?":
    "Eva answers only from the SVIT admissions database and the college website. The AI only puts those facts into words; it never invents fees, cutoffs or dates. If something isn't in the data, Eva says so and gives you the admission office contact.",
  "Do I need to sign in to use Eva?":
    "No. Anyone can use Voice Chat without an account. Signing in only adds a short history of your past questions, which you can delete at any time.",
};

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
