// Hands-free voice conversation (like ChatGPT voice mode) — 2026-10-13.
//
// One tap starts it. Then, in a loop:
//   listening -> (you stop talking for ~2 s) -> thinking -> speaking -> listening ...
// The microphone stays open for the whole conversation, but nothing is recorded
// while IntelliVoice is speaking (so it never hears itself). Tap to interrupt,
// End to stop. Every turn goes through the normal chat, so it also appears in
// the chat history.

import { useCallback, useEffect, useRef, useState } from "react";
import { audioSource } from "../../lib/audio";
import type { QueryResponse } from "../../lib/types";

export type ConversationPhase = "off" | "starting" | "listening" | "thinking" | "speaking" | "error";

const SILENCE_MS = 2000;          // pause after speech that ends your turn (2 s: room for a thinking pause)
const MIN_SPEECH_MS = 350;        // shorter sounds (a cough, a click) are ignored
const MAX_TURN_MS = 25_000;       // a single question can't run longer than this
const IDLE_RESTART_MS = 15_000;   // nobody spoke: start a fresh recording (keeps files small)
const IDLE_END_MS = 90_000;       // nobody spoke for this long: end the conversation
const CALIBRATE_MS = 400;         // measure the room's background noise first
const NOISE_CAP = 0.04;           // background noise can never be assumed louder than this
// Talking over IntelliVoice ("barge-in"): while it speaks, the mic keeps listening.
const ECHO_LEARN_MS = 400;        // ignore the first moment of each reply (echo cancelling settles)
const ECHO_CAP = 0.04;            // its own voice in the mic is never assumed louder than this
const BARGE_IN_MS = 400;          // then a clearly louder voice for this long interrupts it
const BARGE_MIN_LEVEL = 0.065;    // (higher = its own voice from the speakers can't interrupt it)
const BARGE_GAP_MS = 150;         // short dips between syllables don't reset the interrupt timer
const KEEP_TALKING = 0.55;        // once you're talking, softer sounds (word endings) still count as voice

interface Options {
  /** Sends the recording through the normal chat; resolves with the reply (or null on error). */
  ask: (audio: Blob) => Promise<QueryResponse | null>;
  onEnd?: () => void;
}

function pickMimeType(): string {
  if (typeof MediaRecorder === "undefined") return "";
  const types = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];
  return types.find((t) => MediaRecorder.isTypeSupported(t)) ?? "";
}

export function useVoiceConversation({ ask, onEnd }: Options) {
  const [phase, setPhase] = useState<ConversationPhase>("off");
  const [error, setError] = useState<string | null>(null);
  const [lastQuestion, setLastQuestion] = useState<string>("");
  const [lastReply, setLastReply] = useState<string>("");
  const [startedAt, setStartedAt] = useState<number | null>(null);

  // Live level 0..1 for the animation (read every frame, so kept in a ref).
  const levelRef = useRef(0);

  const phaseRef = useRef<ConversationPhase>("off");
  const streamRef = useRef<MediaStream | null>(null);
  const ctxRef = useRef<AudioContext | null>(null);
  const micAnalyserRef = useRef<AnalyserNode | null>(null);
  const outAnalyserRef = useRef<AnalyserNode | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const revokeRef = useRef<(() => void) | null>(null);
  const rafRef = useRef<number>();
  const vad = useRef({ noise: 0.01, calibrateUntil: 0, speaking: false, speechStart: 0, lastVoice: 0, turnStart: 0, lastSpeechEver: 0,
                       speakStart: 0, echo: 0.02, bargeSince: 0, bargeAbove: 0 });
  const [turns, setTurns] = useState(0);   // questions answered in this conversation (all saved in the chat)
  const askRef = useRef(ask);
  askRef.current = ask;
  const onEndRef = useRef(onEnd);
  onEndRef.current = onEnd;

  const go = (p: ConversationPhase) => { phaseRef.current = p; setPhase(p); };
  const current = (): ConversationPhase => phaseRef.current;   // (re-read after awaits)

  const rms = (analyser: AnalyserNode | null) => {
    if (!analyser) return 0;
    const data = new Uint8Array(analyser.fftSize);
    analyser.getByteTimeDomainData(data);
    let sum = 0;
    for (let i = 0; i < data.length; i++) { const v = (data[i] - 128) / 128; sum += v * v; }
    return Math.sqrt(sum / data.length);
  };

  // ---------- recording one turn ----------
  const startRecorder = useCallback(() => {
    const stream = streamRef.current;
    if (!stream) return;
    const mimeType = pickMimeType();
    const rec = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    chunksRef.current = [];
    rec.ondataavailable = (e) => { if (e.data.size) chunksRef.current.push(e.data); };
    recorderRef.current = rec;
    rec.start();
    const now = performance.now();
    Object.assign(vad.current, { speaking: false, speechStart: 0, lastVoice: 0, turnStart: now });
  }, []);

  const stopRecorder = useCallback((): Promise<Blob | null> => new Promise((resolve) => {
    const rec = recorderRef.current;
    recorderRef.current = null;
    if (!rec || rec.state === "inactive") { resolve(null); return; }
    rec.onstop = () => resolve(new Blob(chunksRef.current, { type: rec.mimeType || "audio/webm" }));
    rec.stop();
  }), []);

  const listen = useCallback(() => {
    if (phaseRef.current === "off") return;
    go("listening");
    startRecorder();
  }, [startRecorder]);

  // ---------- reply playback ----------
  const stopPlayback = useCallback(() => {
    const a = audioRef.current;
    if (a) { a.onended = null; a.onerror = null; a.pause(); }
    audioRef.current = null;
    revokeRef.current?.();
    revokeRef.current = null;
  }, []);

  const speak = useCallback((res: QueryResponse) => {
    const source = audioSource(res.audio);
    if (!source) { window.setTimeout(listen, 400); return; }   // no voice for this reply: just continue
    const a = new Audio(source.src);
    audioRef.current = a;
    revokeRef.current = source.revoke;
    try {
      const ctx = ctxRef.current;
      if (ctx) {
        const analyser = ctx.createAnalyser();
        analyser.fftSize = 512;
        ctx.createMediaElementSource(a).connect(analyser);
        analyser.connect(ctx.destination);
        outAnalyserRef.current = analyser;
      }
    } catch { /* the animation just won't follow the voice */ }
    const done = () => { stopPlayback(); outAnalyserRef.current = null; if (phaseRef.current === "speaking") listen(); };
    a.onended = done;
    a.onerror = done;
    Object.assign(vad.current, { speakStart: performance.now(), echo: 0.02, bargeSince: 0, bargeAbove: 0 });
    go("speaking");
    a.play().catch(() => { stopPlayback(); listen(); });
  }, [listen, stopPlayback]);

  // ---------- one finished turn ----------
  const finishTurn = useCallback(async () => {
    const blob = await stopRecorder();
    if (!blob || !blob.size || phaseRef.current === "off") return;
    // New question: clear the previous question/answer from the screen, so it never
    // looks like IntelliVoice is answering the last question again.
    setLastQuestion("");
    setLastReply("");
    go("thinking");
    const res = await askRef.current(blob);
    if (current() === "off") return;
    if (!res) {
      setError("Sorry, something went wrong. Please ask again.");
      window.setTimeout(() => { setError(null); listen(); }, 1500);
      return;
    }
    if (res.transcript) setLastQuestion(res.transcript);
    setTurns((n) => n + 1);
    setLastReply(res.response?.text ?? "");
    speak(res);
  }, [listen, speak, stopRecorder]);

  // ---------- the frame loop: levels + voice detection ----------
  const tick = useCallback(() => {
    const p = phaseRef.current;
    const now = performance.now();
    const v = vad.current;
    if (p === "listening") {
      const level = rms(micAnalyserRef.current);
      levelRef.current = Math.min(1, level * 6);
      // Background noise: follows quiet moments quickly, loud moments only very slowly,
      // and is capped — so someone talking right away is never mistaken for "room noise".
      v.noise = level < v.noise ? v.noise * 0.7 + level * 0.3 : v.noise * 0.998 + level * 0.002;
      v.noise = Math.min(Math.max(v.noise, 0.003), NOISE_CAP);
      if (now >= v.calibrateUntil) {
        const threshold = Math.min(Math.max(0.02, v.noise * 3), 0.12);
        const needed = v.speaking ? Math.max(0.011, threshold * KEEP_TALKING) : threshold;
        if (level > needed) {
          if (!v.speaking) { v.speaking = true; v.speechStart = now; }
          v.lastVoice = now;
          v.lastSpeechEver = now;
        }
        const spokeLongEnough = v.speaking && v.lastVoice - v.speechStart >= MIN_SPEECH_MS;
        if (spokeLongEnough && now - v.lastVoice > SILENCE_MS) {
          void finishTurn();
        } else if (v.speaking && now - v.turnStart > MAX_TURN_MS) {
          void finishTurn();
        } else if (v.speaking && !spokeLongEnough && now - v.lastVoice > SILENCE_MS) {
          v.speaking = false;                             // just a short noise
        } else if (!v.speaking && now - v.turnStart > IDLE_RESTART_MS) {
          void stopRecorder().then(() => { if (phaseRef.current === "listening") startRecorder(); });
        }
        if (now - v.lastSpeechEver > IDLE_END_MS) { void end(); return; }
      }
    } else if (p === "speaking") {
      levelRef.current = Math.min(1, rms(outAnalyserRef.current) * 5);
      const mic = rms(micAnalyserRef.current);
      // How much of its own voice leaks into the mic: follows quiet moments quickly,
      // loud ones only slowly, and is capped — so talking right away still interrupts.
      v.echo = mic < v.echo ? v.echo * 0.8 + mic * 0.2 : v.echo * 0.99 + mic * 0.01;
      v.echo = Math.min(v.echo, ECHO_CAP);
      if (now - v.speakStart >= ECHO_LEARN_MS) {
        const threshold = Math.max(BARGE_MIN_LEVEL, v.echo * 2.5, v.noise * 4);
        if (mic > threshold) {
          if (!v.bargeSince) v.bargeSince = now;
          v.bargeAbove = now;
          if (now - v.bargeSince >= BARGE_IN_MS) {
            // You started talking: stop the reply and listen to you right away.
            stopPlayback();
            outAnalyserRef.current = null;
            listen();
            Object.assign(v, { speaking: true, speechStart: now - BARGE_IN_MS, lastVoice: now, lastSpeechEver: now });
          }
        } else if (now - v.bargeAbove > BARGE_GAP_MS) {
          v.bargeSince = 0;
        }
      }
    } else {
      levelRef.current *= 0.9;
    }
    rafRef.current = requestAnimationFrame(tick);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [finishTurn, startRecorder, stopRecorder]);

  // ---------- start / end ----------
  const begin = useCallback(async () => {
    if (phaseRef.current !== "off" && phaseRef.current !== "error") return;
    setError(null); setLastQuestion(""); setLastReply(""); setTurns(0);
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setError("Voice conversation is not supported in this browser."); go("error"); return;
    }
    go("starting");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
      streamRef.current = stream;
      const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const ctx = new Ctx();
      ctxRef.current = ctx;
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 1024;
      ctx.createMediaStreamSource(stream).connect(analyser);
      micAnalyserRef.current = analyser;
    } catch (err) {
      const name = (err as DOMException)?.name;
      setError(name === "NotAllowedError" || name === "SecurityError"
        ? "Microphone permission was denied. Please allow the microphone and try again."
        : "Couldn't start the microphone. Please check it and try again.");
      go("error");
      return;
    }
    const now = performance.now();
    Object.assign(vad.current, { noise: 0.02, calibrateUntil: now + CALIBRATE_MS, lastSpeechEver: now });
    setStartedAt(Date.now());
    listen();
    rafRef.current = requestAnimationFrame(tick);
  }, [listen, tick]);

  const cleanup = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    const rec = recorderRef.current;
    recorderRef.current = null;
    if (rec && rec.state !== "inactive") { rec.onstop = null; rec.stop(); }
    stopPlayback();
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    ctxRef.current?.close().catch(() => undefined);
    ctxRef.current = null;
    micAnalyserRef.current = null;
    outAnalyserRef.current = null;
    levelRef.current = 0;
  }, [stopPlayback]);

  const end = useCallback(async () => {
    if (phaseRef.current === "off") return;
    go("off");
    cleanup();
    setStartedAt(null);
    onEndRef.current?.();
  }, [cleanup]);

  /** Tap on the orb / main button: interrupt the reply, or send what you said right now. */
  const tap = useCallback(() => {
    const p = phaseRef.current;
    if (p === "speaking") { stopPlayback(); outAnalyserRef.current = null; listen(); }
    else if (p === "listening" && vad.current.speaking) void finishTurn();
  }, [finishTurn, listen, stopPlayback]);

  useEffect(() => () => { phaseRef.current = "off"; cleanup(); }, [cleanup]);

  return { phase, error, lastQuestion, lastReply, startedAt, turns, levelRef, begin, end, tap };
}
