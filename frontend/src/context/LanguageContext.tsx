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
}

const LanguageContext = createContext<LanguageValue | null>(null);

const isSpeech = (v: string | null): v is SpeechLanguage => SPEECH_OPTIONS.some((o) => o.value === v);
const isResponse = (v: string | null): v is ResponseLanguage => RESPONSE_OPTIONS.some((o) => o.value === v);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [speechLanguage, setSpeech] = useState<SpeechLanguage>(() => {
    const v = storage.get(SPEECH_KEY);
    return isSpeech(v) ? v : "auto";
  });
  const [responseLanguage, setResponse] = useState<ResponseLanguage>(() => {
    const v = storage.get(RESPONSE_KEY);
    return isResponse(v) ? v : "same";
  });

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
      setQuickLanguage: (l: LangCode) => { setSpeechLanguage(l); setResponseLanguage(l); },
    };
  }, [speechLanguage, responseLanguage]);

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage(): LanguageValue {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useLanguage must be used inside <LanguageProvider>");
  return ctx;
}
