import { useCallback, useEffect, useRef, useState } from "react";
import { frameLevel, openCleanMic, type CleanMic } from "../lib/cleanMic";

export type RecorderError = "unsupported" | "denied" | "no-mic" | "failed";

interface Options {
  /** Called with the finished recording (only if it's long enough). */
  onRecorded: (audio: Blob) => void;
  onTooShort?: () => void;
  /** 2026-10-28: the recording had no speech in it — nothing is sent. */
  onNoSpeech?: () => void;
  onError?: (kind: RecorderError) => void;
  maxMs?: number;
  minMs?: number;
}

const BAR_COUNT = 5;
// Speech check (2026-10-28): a recording is only sent if real speech was heard.
const CALIBRATE_MS = 250;      // first moments: learn how loud the room is
const MIN_SPEECH_LEVEL = 0.02; // never count anything quieter than this as speech
const NOISE_FACTOR = 3;        // speech = clearly louder than the room
const NOISE_CAP = 0.012;       // the room is never assumed louder than this (people often start talking at once)
const MIN_VOICED_MS = 300;     // at least this much speech, or it was just noise / a click

function pickMimeType(): string {
  if (typeof MediaRecorder === "undefined") return "";
  const types = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];
  return types.find((t) => MediaRecorder.isTypeSupported(t)) ?? "";
}

/**
 * Microphone recorder built on MediaRecorder.
 * Also exposes live input levels (0–1) for the little equaliser bars.
 * 2026-10-28: records the noise-cancelled voice (lib/cleanMic.ts) and drops
 * recordings with no speech, so silence never reaches the server.
 */
export function useRecorder({ onRecorded, onTooShort, onNoSpeech, onError, maxMs = 30_000, minMs = 600 }: Options) {
  const [recording, setRecording] = useState(false);
  const [levels, setLevels] = useState<number[]>(() => Array(BAR_COUNT).fill(0));

  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const startedAtRef = useRef(0);
  const startingRef = useRef(false);
  const stopWantedRef = useRef(false);
  const maxTimerRef = useRef<number>();
  const rafRef = useRef<number>();
  const micRef = useRef<CleanMic | null>(null);
  const speechRef = useRef({ noise: 1, voicedMs: 0, last: 0, measured: false });

  // keep latest callbacks without re-creating start/stop
  const cb = useRef({ onRecorded, onTooShort, onNoSpeech, onError });
  cb.current = { onRecorded, onTooShort, onNoSpeech, onError };

  const stopMeter = () => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    setLevels(Array(BAR_COUNT).fill(0));
  };

  /** Equaliser bars + speech detection on the cleaned voice. */
  const startMeter = (mic: CleanMic) => {
    const analyser = mic.analyser;
    speechRef.current = { noise: 1, voicedMs: 0, last: performance.now(), measured: !!analyser };
    if (!analyser) return;
    const freq = new Uint8Array(analyser.frequencyBinCount);
    const wave = new Uint8Array(analyser.fftSize);
    const started = performance.now();
    const tick = () => {
      analyser.getByteFrequencyData(freq);
      const step = Math.max(1, Math.floor(freq.length / 24));
      setLevels(Array.from({ length: BAR_COUNT }, (_, i) => (freq[2 + i * step] ?? 0) / 255));
      const now = performance.now();
      const sp = speechRef.current;
      const level = frameLevel(analyser, wave);
      if (now - started < CALIBRATE_MS) sp.noise = Math.min(sp.noise, level, NOISE_CAP);
      const noise = Math.min(sp.noise, NOISE_CAP);
      if (level > Math.max(MIN_SPEECH_LEVEL, noise * NOISE_FACTOR)) sp.voicedMs += now - sp.last;
      sp.last = now;
      rafRef.current = requestAnimationFrame(tick);
    };
    tick();
  };

  const stop = useCallback(() => {
    if (startingRef.current) {
      stopWantedRef.current = true; // released before the mic finished starting
      return;
    }
    window.clearTimeout(maxTimerRef.current);
    const rec = recorderRef.current;
    if (rec && rec.state !== "inactive") rec.stop();
  }, []);

  const start = useCallback(async () => {
    if (recorderRef.current || startingRef.current) return;
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      cb.current.onError?.("unsupported");
      return;
    }
    startingRef.current = true;
    stopWantedRef.current = false;

    let mic: CleanMic;
    try {
      mic = await openCleanMic(1024);
    } catch (err) {
      startingRef.current = false;
      const name = (err as DOMException)?.name;
      cb.current.onError?.(name === "NotAllowedError" || name === "SecurityError" ? "denied" : name === "NotFoundError" ? "no-mic" : "failed");
      return;
    }

    const stream = mic.stream;
    const mimeType = pickMimeType();
    const rec = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    chunksRef.current = [];
    rec.ondataavailable = (e) => { if (e.data.size) chunksRef.current.push(e.data); };
    rec.onstop = () => {
      const duration = Date.now() - startedAtRef.current;
      const blob = new Blob(chunksRef.current, { type: rec.mimeType || mimeType || "audio/webm" });
      stopMeter();
      mic.close();
      micRef.current = null;
      recorderRef.current = null;
      streamRef.current = null;
      setRecording(false);
      const sp = speechRef.current;
      if (duration < minMs || !blob.size) cb.current.onTooShort?.();
      else if (sp.measured && sp.voicedMs < MIN_VOICED_MS) (cb.current.onNoSpeech ?? cb.current.onTooShort)?.();
      else cb.current.onRecorded(blob);
    };

    recorderRef.current = rec;
    streamRef.current = stream;
    micRef.current = mic;
    startedAtRef.current = Date.now();
    rec.start();
    setRecording(true);
    startMeter(mic);
    maxTimerRef.current = window.setTimeout(stop, maxMs);

    startingRef.current = false;
    if (stopWantedRef.current) stop();
  }, [maxMs, minMs, stop]);

  const toggle = useCallback(() => {
    if (recorderRef.current || startingRef.current) stop();
    else void start();
  }, [start, stop]);

  // release the microphone if the page is left mid-recording
  useEffect(() => () => {
    window.clearTimeout(maxTimerRef.current);
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    const rec = recorderRef.current;
    if (rec) { rec.onstop = null; if (rec.state !== "inactive") rec.stop(); }
    micRef.current?.close();
  }, []);

  return { recording, levels, start, stop, toggle };
}
