import type { AudioInfo } from "./types";

export function mimeFor(format?: string): string {
  switch ((format ?? "wav").toLowerCase()) {
    case "mp3": return "audio/mpeg";
    case "ogg": return "audio/ogg";
    case "webm": return "audio/webm";
    default: return "audio/wav";
  }
}

function base64ToBlob(b64: string, type: string): Blob {
  const clean = b64.replace(/^data:[^,]+,/, "");
  const bin = atob(clean);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new Blob([bytes], { type });
}

/** Returns a playable URL for the reply audio, plus a cleanup function. */
export function audioSource(audio: AudioInfo | null | undefined): { src: string; revoke: () => void } | null {
  if (!audio) return null;
  if (audio.base64) {
    try {
      const url = URL.createObjectURL(base64ToBlob(audio.base64, mimeFor(audio.format)));
      return { src: url, revoke: () => URL.revokeObjectURL(url) };
    } catch {
      return null;
    }
  }
  if (audio.url) return { src: audio.url, revoke: () => undefined };
  return null;
}
