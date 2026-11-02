// "Hey Eva" wake word (2026-11-01).
//
// When switched on, the browser listens for the assistant's name and opens the
// hands-free voice chat by itself — no button needed. It uses the speech
// recognition built into Edge and Chrome (free, no key). Notes:
//   - Edge / Chrome only, and it needs the internet: while it is ON, the browser
//     sends the microphone audio to Microsoft's / Google's speech service to spot
//     the name. That is why it is OFF until the user switches it on.
//   - It pauses while the voice chat is open or the mic is recording (they need the
//     microphone), and starts listening for the name again afterwards.
//   - The browser stops listening by itself after a while; it is restarted.
// (Picovoice, the usual offline wake-word engine, ended its free plan on 30 June 2026.)

import { useEffect, useRef, useState } from "react";

// Minimal types: TypeScript's DOM library does not include the Speech Recognition API.
interface RecognitionAlternative { transcript: string }
interface RecognitionResult { readonly length: number; [i: number]: RecognitionAlternative }
interface RecognitionEvent { resultIndex: number; results: { readonly length: number; [i: number]: RecognitionResult } }
interface Recognition {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((e: RecognitionEvent) => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
}
type RecognitionCtor = new () => Recognition;

function recognitionCtor(): RecognitionCtor | undefined {
  const w = window as unknown as { SpeechRecognition?: RecognitionCtor; webkitSpeechRecognition?: RecognitionCtor };
  return w.SpeechRecognition || w.webkitSpeechRecognition;
}

// "Eva", "Hey Eva", and how it is often heard ("Ava", "Iva", "Eeva"); also in Kannada / Hindi letters.
// 2026-11-01: "Hey Eva" was often written as one word or as a look-alike ("heva", "hey ever",
// "hey eve", "a eva"), so those spellings count too; "Eva" alone still works.
const WAKE = new RegExp(
  "(^|[^a-z])(hey|hi|hello|ok|okay|a|he)\\s*(eva|eeva|evaa|ewa|iva|ava|ever|eve|eba|evva|yeva)([^a-z]|$)"
  + "|(^|[^a-z])(heyva|heva|hiva|heyeva|heyiva|haeva|heeva)([^a-z]|$)"
  + "|(^|[^a-z])(eva|eeva|evaa|ewa|iva|ava)([^a-z]|$)"
  + "|ಹೇ\\s*ಈವಾ|ಈವಾ|ಇವಾ|ಎವಾ|हे\\s*ईवा|ईवा|इवा|एवा",
  "i",
);

function chime() {
  try {
    const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    const ctx = new Ctx();
    [880, 1320].forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.frequency.value = freq;
      const t = ctx.currentTime + i * 0.12;
      gain.gain.setValueAtTime(0.0001, t);
      gain.gain.exponentialRampToValueAtTime(0.18, t + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.25);
      osc.connect(gain).connect(ctx.destination);
      osc.start(t);
      osc.stop(t + 0.3);
    });
    window.setTimeout(() => void ctx.close(), 800);
  } catch { /* no sound is fine */ }
}

export const wakeWordSupported = (): boolean => typeof window !== "undefined" && !!recognitionCtor();

export function useWakeWord({ enabled, paused, onWake }: { enabled: boolean; paused: boolean; onWake: () => void }) {
  const [listening, setListening] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const onWakeRef = useRef(onWake);
  onWakeRef.current = onWake;

  useEffect(() => {
    const Ctor = recognitionCtor();
    if (!enabled || paused || !Ctor) { setListening(false); return; }
    let stopped = false;
    let failures = 0;
    let restartTimer = 0;
    const rec = new Ctor();
    rec.lang = "en-IN";
    rec.continuous = true;
    rec.interimResults = true;
    rec.maxAlternatives = 3;

    rec.onresult = (e) => {
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const result = e.results[i];
        for (let j = 0; j < result.length; j++) {
          if (WAKE.test(result[j].transcript)) {
            stopped = true;
            rec.abort();
            setListening(false);
            chime();
            window.setTimeout(() => onWakeRef.current(), 250);   // after the chime, so it isn't recorded
            return;
          }
        }
      }
      failures = 0;
    };
    rec.onerror = (e) => {
      if (e.error === "not-allowed" || e.error === "service-not-allowed") {
        stopped = true;
        setError("Microphone access is blocked, so Eva can't listen for her name. Allow the microphone and switch it on again.");
      } else if (e.error !== "no-speech" && e.error !== "aborted") {
        failures += 1;
      }
    };
    rec.onend = () => {
      setListening(false);
      if (stopped) return;
      if (failures >= 5) { setError("Eva stopped listening for her name (no internet?). Switch it off and on to try again."); return; }
      restartTimer = window.setTimeout(() => {
        try { rec.start(); setListening(true); } catch { /* already running */ }
      }, Math.min(300 * 2 ** failures, 5000));
    };

    setError(null);
    try { rec.start(); setListening(true); } catch { setListening(false); }
    return () => {
      stopped = true;
      window.clearTimeout(restartTimer);
      rec.onresult = null; rec.onerror = null; rec.onend = null;
      try { rec.abort(); } catch { /* not running */ }
      setListening(false);
    };
  }, [enabled, paused]);

  return { supported: wakeWordSupported(), listening, error };
}
