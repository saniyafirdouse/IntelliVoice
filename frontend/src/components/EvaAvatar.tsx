// Eva, the assistant's face (2026-11-01).
// Her round photo with the plum + champagne ring. Used next to chat replies,
// on the "Speak to Eva" button and (later) in the voice chat.
// The photo is public/assets/eva.jpg.

export const EVA_RING = "conic-gradient(from 210deg, #7c5ba6, #e8d3a3, #5b3f86, #e8d3a3, #7c5ba6)";

export function EvaAvatar({ size = 48, glow = false, className = "" }: { size?: number; glow?: boolean; className?: string }) {
  const ring = Math.max(2, Math.round(size / 22));
  return (
    <span
      className={`relative inline-block flex-shrink-0 rounded-full ${glow ? "eva-glow" : ""} ${className}`}
      style={{ width: size, height: size, padding: ring, background: EVA_RING, boxShadow: "0 6px 16px rgba(0,0,0,0.35)" }}
      aria-hidden="true"
    >
      <img src="/assets/eva.jpg" alt="" className="w-full h-full rounded-full object-cover" draggable={false} />
    </span>
  );
}
