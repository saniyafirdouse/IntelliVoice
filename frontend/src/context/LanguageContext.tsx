import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { storage } from "../lib/storage";
import type { LangCode } from "../lib/types";

/**
 * Two separate choices made by the user:
 *  • speechLanguage   – the language they will SPEAK / type in (helps Whisper)
 *  • responseLanguage – the language and script IntelliVoice replies in,
 *                       including Kannada / Hindi written in English letters (romanized)
 */

export type SpeechLanguage = "auto" | LangCode;
export type ResponseLanguage = "same" | "en" | "kn" | "kn-Latn" | "hi" | "hi-Latn";

export const SPEECH_OPTIONS: { value: SpeechLanguage; label: string }[] = [
  { value: "auto", label: "Auto-detect (incl. mixed)" },
  { value: "en", label: "English" },
  { value: "kn", label: "ಕನ್ನಡ · Kannada" },
  { value: "hi", label: "हिंदी · Hindi" },
];

export const RESPONSE_OPTIONS: { value: ResponseLanguage; label: string }[] = [
  { value: "same", label: "Same as my question" },
  { value: "en", label: "English" },
  { value: "kn", label: "ಕನ್ನಡ · Kannada script" },
  { value: "kn-Latn", label: "Kannada in English letters" },
  { value: "hi", label: "हिंदी · Hindi script" },
  { value: "hi-Latn", label: "Hindi in English letters" },
];

export const RESPONSE_SHORT: Record<ResponseLanguage, string> = {
  same: "Same as question",
  en: "English",
  kn: "ಕನ್ನಡ",
  "kn-Latn": "Kannada (English letters)",
  hi: "हिंदी",
  "hi-Latn": "Hindi (English letters)",
};

const SPEECH_KEY = "intellivoice_speech_lang";
const RESPONSE_KEY = "intellivoice_response_lang";

interface LanguageValue {
  speechLanguage: SpeechLanguage;
  responseLanguage: ResponseLanguage;
  setSpeechLanguage: (l: SpeechLanguage) => void;
  setResponseLanguage: (l: ResponseLanguage) => void;
  /** The quick ENG / KN / HI switch: sets both to the same language. */
  quickLanguage: LangCode | null;
  setQuickLanguage: (l: LangCode) => void;
  /** Kannada / Hindi replies written in English letters (romanized). */
  romanized: boolean;
  setRomanized: (on: boolean) => void;
  /** Back to "detect my language, reply in the same" (also handles mixed speech). */
  clearQuickLanguage: () => void;
}

const LanguageContext = createContext<LanguageValue | null>(null);

const isSpeech = (v: string | null): v is SpeechLanguage => SPEECH_OPTIONS.some((o) => o.value === v);
const isResponse = (v: string | null): v is ResponseLanguage => RESPONSE_OPTIONS.some((o) => o.value === v);

// The language menu offers: Auto, English, Kannada, Kannada in English letters, Hindi,
// Hindi in English letters. Older versions (separate "speak in" / "reply in" boxes)
// could save other mixes, e.g. "speak English, reply Hindi" — that forced Whisper to
// English while the parent spoke Hindi, and the menu couldn't show it. Such leftovers
// are reset to Auto-detect (2026-10-14).
const isMenuChoice = (s: SpeechLanguage, r: ResponseLanguage) =>
  (s === "auto" && r === "same") || (s !== "auto" && (r === s || r === `${s}-Latn`));

function loadSaved(): { speech: SpeechLanguage; response: ResponseLanguage } {
  const s = storage.get(SPEECH_KEY);
  const r = storage.get(RESPONSE_KEY);
  const speech: SpeechLanguage = isSpeech(s) ? s : "auto";
  const response: ResponseLanguage = isResponse(r) ? r : "same";
  return isMenuChoice(speech, response) ? { speech, response } : { speech: "auto", response: "same" };
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [saved] = useState(loadSaved);
  const [speechLanguage, setSpeech] = useState<SpeechLanguage>(saved.speech);
  const [responseLanguage, setResponse] = useState<ResponseLanguage>(saved.response);

  const value = useMemo<LanguageValue>(() => {
    const setSpeechLanguage = (l: SpeechLanguage) => { setSpeech(l); storage.set(SPEECH_KEY, l); };
    const setResponseLanguage = (l: ResponseLanguage) => { setResponse(l); storage.set(RESPONSE_KEY, l); };
    const quickLanguage: LangCode | null =
      speechLanguage !== "auto" && (responseLanguage === speechLanguage || responseLanguage === `${speechLanguage}-Latn`)
        ? speechLanguage
        : null;
    return {
      speechLanguage,
      responseLanguage,
      setSpeechLanguage,
      setResponseLanguage,
      quickLanguage,
      // keeps the "English letters" choice when switching between Kannada and Hindi
      setQuickLanguage: (l: LangCode) => {
        setSpeechLanguage(l);
        setResponseLanguage(l !== "en" && responseLanguage.endsWith("-Latn") ? (`${l}-Latn` as ResponseLanguage) : l);
      },
      romanized: responseLanguage.endsWith("-Latn"),
      setRomanized: (on: boolean) => {
        const base = (responseLanguage.replace("-Latn", "") as ResponseLanguage);
        if (base === "kn" || base === "hi") setResponseLanguage(on ? (`${base}-Latn` as ResponseLanguage) : base);
      },
      clearQuickLanguage: () => { setSpeechLanguage("auto"); setResponseLanguage("same"); },
    };
  }, [speechLanguage, responseLanguage]);

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage(): LanguageValue {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useLanguage must be used inside <LanguageProvider>");
  return ctx;
}
