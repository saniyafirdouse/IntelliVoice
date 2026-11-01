// Copies the Silero speech-detector files into public/vad/ (2026-10-31).
// Runs by itself after `npm install` ("postinstall"); also `npm run vad-assets`.
// The voice chat loads them from /vad/ — nothing is fetched from the internet.
import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const out = join(root, "public", "vad");
const files = [
  ["node_modules/@ricky0123/vad-web/dist/vad.worklet.bundle.min.js", "vad.worklet.bundle.min.js"],
  ["node_modules/@ricky0123/vad-web/dist/silero_vad_v5.onnx", "silero_vad_v5.onnx"],
  ["node_modules/@ricky0123/vad-web/dist/silero_vad_legacy.onnx", "silero_vad_legacy.onnx"],
];
// (The onnxruntime .wasm/.mjs files are NOT copied: lib/speechDetector.ts imports them
// through Vite, because Vite refuses to import() files from public/.)

mkdirSync(out, { recursive: true });
let copied = 0;
for (const [from, to] of files) {
  const src = join(root, from);
  if (!existsSync(src)) {
    console.warn(`[vad-assets] missing ${from} — the voice chat will use loudness only`);
    continue;
  }
  copyFileSync(src, join(out, to));
  copied += 1;
}
console.log(`[vad-assets] ${copied}/${files.length} speech-detector files copied to public/vad/`);
