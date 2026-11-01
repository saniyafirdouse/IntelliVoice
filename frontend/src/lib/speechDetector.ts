// Speech detector for the hands-free voice chat (2026-10-31).
//
// Before, the voice chat decided "someone is talking" only by LOUDNESS, so a fan,
// a door, chatter or a click could start a turn, and a pause could end it early.
// Silero VAD is a small AI model (about 2 MB) that recognises human SPEECH, frame
// by frame, inside the browser (package @ricky0123/vad-web, runs on onnxruntime-web).
// useVoiceConversation asks it "is this speech?" 30 times a second.
//
// Its files are copied to public/vad/ by `npm install` (scripts/copy-vad-assets.mjs),
// so nothing is downloaded from the internet at run time.
// If it can't start (old browser, files missing), the voice chat simply keeps
// using loudness as before — it never breaks the conversation.

export interface SpeechDetector {
  /** Probability (0–1) that the latest audio frame is speech. */
  readonly prob: number;
  /** When the latest probability arrived (performance.now()). */
  readonly at: number;
  close: () => void;
}

// The speech model and its worklet are plain files in public/vad/. The onnxruntime
// files are imported through Vite (as URLs), because onnxruntime loads its .mjs with
// import() — and Vite's dev server refuses to import() files from public/
// ("Failed to load url /vad/ort-wasm-simd-threaded.mjs").
import ortWasmUrl from "onnxruntime-web/ort-wasm-simd-threaded.wasm?url";
import ortMjsUrl from "onnxruntime-web/ort-wasm-simd-threaded.mjs?url";

const ASSETS = "/vad/";

export async function openSpeechDetector(stream: MediaStream): Promise<SpeechDetector | null> {
  try {
    const { MicVAD } = await import("@ricky0123/vad-web");
    const state = { prob: 0, at: 0 };
    const vad = await MicVAD.new({
      model: "v5",
      baseAssetPath: ASSETS,
      // onnxruntime accepts {mjs, wasm} URLs here as well as a folder; the type only says string
      onnxWASMBasePath: { mjs: ortMjsUrl, wasm: ortWasmUrl } as unknown as string,
      getStream: async () => stream,
      pauseStream: async () => undefined,          // the voice chat owns the microphone
      resumeStream: async (s: MediaStream) => s,
      startOnLoad: true,
      onFrameProcessed: (p) => { state.prob = p.isSpeech; state.at = performance.now(); },
      onSpeechStart: () => undefined,
      onSpeechEnd: () => undefined,
      onVADMisfire: () => undefined,
      onSpeechRealStart: () => undefined,
    });
    return {
      get prob() { return state.prob; },
      get at() { return state.at; },
      close: () => { void vad.destroy().catch(() => undefined); },
    };
  } catch (err) {
    console.warn("[speechDetector] Silero VAD unavailable — using loudness only", err);
    return null;
  }
}
