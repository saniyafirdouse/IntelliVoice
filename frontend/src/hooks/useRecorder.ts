import { useCallback, useEffect, useRef, useState } from "react";

export type RecorderError = "unsupported" | "denied" | "no-mic" | "failed";

interface Options {
  /** Called with the finished recording (only if it's long enough). */
  onRecorded: (audio: Blob) => void;
  onTooShort?: () => void;
  onError?: (kind: RecorderError) => void;
  maxMs?: number;
  minMs?: number;
}

const BAR_COUNT = 5;

function pickMimeType(): string {
  if (typeof MediaRecorder === "undefined") return "";
  const types = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];
  return types.find((t) => MediaRecorder.isTypeSupported(t)) ?? "";
}

/**
 * Microphone recorder built on MediaRecorder.
 * Also exposes live input levels (0–1) for the little equaliser bars.
 */
export function useRecorder({ onRecorded, onTooShort, onError, maxMs = 30_000, minMs = 600 }: Options) {
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
  const audioCtxRef = useRef<AudioContext | null>(null);

  // keep latest callbacks without re-creating start/stop
  const cb = useRef({ onRecorded, onTooShort, onError });
  cb.current = { onRecorded, onTooShort, onError };

  const stopMeter = () => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    audioCtxRef.current?.close().catch(() => undefined);
    audioCtxRef.current = null;
    setLevels(Array(BAR_COUNT).fill(0));
  };

  const startMeter = (stream: MediaStream) => {
    try {
      const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const ctx = new Ctx();
      audioCtxRef.current = ctx;
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 64;
      ctx.createMediaStreamSource(stream).connect(analyser);
      const data = new Uint8Array(analyser.frequencyBinCount);
      const tick = () => {
        analyser.getByteFrequencyData(data);
        setLevels(Array.from({ length: BAR_COUNT }, (_, i) => (data[2 + i * 3] ?? 0) / 255));
        rafRef.current = requestAnimationFrame(tick);
      };
      tick();
    } catch {
      /* the level meter is optional */
    }
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

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
    } catch (err) {
      startingRef.current = false;
      const name = (err as DOMException)?.name;
      cb.current.onError?.(name === "NotAllowedError" || name === "SecurityError" ? "denied" : name === "NotFoundError" ? "no-mic" : "failed");
      return;
    }

    const mimeType = pickMimeType();
    const rec = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    chunksRef.current = [];
    rec.ondataavailable = (e) => { if (e.data.size) chunksRef.current.push(e.data); };
    rec.onstop = () => {
      const duration = Date.now() - startedAtRef.current;
      const blob = new Blob(chunksRef.current, { type: rec.mimeType || mimeType || "audio/webm" });
      stream.getTracks().forEach((t) => t.stop());
      stopMeter();
      recorderRef.current = null;
      streamRef.current = null;
      setRecording(false);
      if (duration < minMs || !blob.size) cb.current.onTooShort?.();
      else cb.current.onRecorded(blob);
    };

    recorderRef.current = rec;
    streamRef.current = stream;
    startedAtRef.current = Date.now();
    rec.start();
    setRecording(true);
    startMeter(stream);
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
    audioCtxRef.current?.close().catch(() => undefined);
    const rec = recorderRef.current;
    if (rec) { rec.onstop = null; if (rec.state !== "inactive") rec.stop(); }
    streamRef.current?.getTracks().forEach((t) => t.stop());
  }, []);

  return { recording, levels, start, stop, toggle };
}
