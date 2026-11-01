// Clean microphone (2026-10-28): noise cancellation before the voice is sent.
//
// The browser's own noise suppression is mild (it mostly removes steady hiss).
// For a demo hall with fans, chatter and echo, the voice goes through three
// extra steps here, all inside the browser:
//
//   mic -> high-pass filter -> RNNoise (AI noise suppression) -> leveller -> recorder
//
//   1. High-pass filter: cuts low rumble/hum below ~130 Hz (fans, AC, projectors).
//   2. RNNoise: a small neural network (xiph.org) that removes background noise
//      and keeps speech. Runs as an AudioWorklet (package @sapphi-red/web-noise-suppressor).
//   3. Leveller (compressor + gain): soft and loud voices reach Whisper at a similar volume.
//
// If RNNoise can't start (old browser, no AudioWorklet), steps 1 and 3 still run.
// If even that fails, the plain microphone is used — recording never breaks.

import { RnnoiseWorkletNode, loadRnnoise } from "@sapphi-red/web-noise-suppressor";
import rnnoiseWorkletPath from "@sapphi-red/web-noise-suppressor/rnnoiseWorklet.js?url";
import rnnoiseWasmPath from "@sapphi-red/web-noise-suppressor/rnnoise.wasm?url";
import rnnoiseWasmSimdPath from "@sapphi-red/web-noise-suppressor/rnnoise_simd.wasm?url";

export interface CleanMic {
  /** The cleaned voice — record this. */
  stream: MediaStream;
  /** The microphone as it is (before cleaning). */
  raw: MediaStream;
  /** Analyser on the cleaned voice (levels, speech detection). */
  analyser: AnalyserNode | null;
  ctx: AudioContext | null;
  /** True when RNNoise is active. */
  denoised: boolean;
  /** Stops the microphone and frees everything. */
  close: () => void;
}

const MIC_CONSTRAINTS: MediaTrackConstraints = {
  echoCancellation: true,
  noiseSuppression: true,
  autoGainControl: true,
  channelCount: 1,
};

let wasmPromise: Promise<ArrayBuffer> | null = null;   // the model is downloaded once

type Ctx = typeof AudioContext;
const AudioCtx = (): Ctx | undefined =>
  window.AudioContext || (window as unknown as { webkitAudioContext?: Ctx }).webkitAudioContext;

/** Opens the microphone with noise cancellation. Throws like getUserMedia if the mic can't be opened. */
export async function openCleanMic(analyserFftSize = 1024): Promise<CleanMic> {
  const raw = await navigator.mediaDevices.getUserMedia({ audio: MIC_CONSTRAINTS });
  const stopRaw = () => raw.getTracks().forEach((t) => t.stop());
  const Ctor = AudioCtx();
  if (!Ctor) return { stream: raw, raw, analyser: null, ctx: null, denoised: false, close: stopRaw };

  let ctx: AudioContext | null = null;
  try {
    // RNNoise works at 48 kHz.
    ctx = new Ctor({ sampleRate: 48000 });
    let source: MediaStreamAudioSourceNode;
    try {
      source = ctx.createMediaStreamSource(raw);
    } catch {
      // Some browsers can't mix sample rates: use the device rate (no RNNoise then).
      await ctx.close().catch(() => undefined);
      ctx = new Ctor();
      source = ctx.createMediaStreamSource(raw);
    }

    // two filters in a row = a steep cut, so hum is removed but voices are not
    const highPass = ctx.createBiquadFilter();
    highPass.type = "highpass";
    highPass.frequency.value = 130;
    const highPass2 = ctx.createBiquadFilter();
    highPass2.type = "highpass";
    highPass2.frequency.value = 130;
    highPass.connect(highPass2);

    const leveller = ctx.createDynamicsCompressor();
    leveller.threshold.value = -32;
    leveller.knee.value = 12;
    leveller.ratio.value = 4;
    leveller.attack.value = 0.005;
    leveller.release.value = 0.25;
    const makeUp = ctx.createGain();
    makeUp.gain.value = 1.6;

    let rnnoise: RnnoiseWorkletNode | null = null;
    if (ctx.sampleRate === 48000 && ctx.audioWorklet) {
      try {
        wasmPromise ??= loadRnnoise({ url: rnnoiseWasmPath, simdUrl: rnnoiseWasmSimdPath });
        const wasmBinary = await wasmPromise;
        await ctx.audioWorklet.addModule(rnnoiseWorkletPath);
        rnnoise = new RnnoiseWorkletNode(ctx, { wasmBinary, maxChannels: 1 });
      } catch (err) {
        wasmPromise = null;
        console.warn("[cleanMic] RNNoise unavailable, using filter + leveller only", err);
        rnnoise = null;
      }
    }

    const out = ctx.createMediaStreamDestination();
    const analyser = ctx.createAnalyser();
    analyser.fftSize = analyserFftSize;

    source.connect(highPass);
    if (rnnoise) { highPass2.connect(rnnoise); rnnoise.connect(leveller); }
    else highPass2.connect(leveller);
    leveller.connect(makeUp);
    makeUp.connect(out);
    makeUp.connect(analyser);
    if (ctx.state === "suspended") await ctx.resume().catch(() => undefined);

    const ownCtx = ctx;
    return {
      stream: out.stream,
      raw,
      analyser,
      ctx: ownCtx,
      denoised: !!rnnoise,
      close: () => {
        stopRaw();
        out.stream.getTracks().forEach((t) => t.stop());
        try { rnnoise?.destroy(); } catch { /* already gone */ }
        ownCtx.close().catch(() => undefined);
      },
    };
  } catch (err) {
    console.warn("[cleanMic] using the plain microphone", err);
    ctx?.close().catch(() => undefined);
    return { stream: raw, raw, analyser: null, ctx: null, denoised: false, close: stopRaw };
  }
}

/** Loudness (0–1) of the latest audio frame. */
export function frameLevel(analyser: AnalyserNode | null, buf?: Uint8Array): number {
  if (!analyser) return 0;
  const data = buf && buf.length === analyser.fftSize ? buf : new Uint8Array(analyser.fftSize);
  analyser.getByteTimeDomainData(data);
  let sum = 0;
  for (let i = 0; i < data.length; i++) { const v = (data[i] - 128) / 128; sum += v * v; }
  return Math.sqrt(sum / data.length);
}
