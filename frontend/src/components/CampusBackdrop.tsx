import type { ReactNode } from "react";

export const CAMPUS_LAYERS = [
  { id: "bg-section-quad", label: "Main Quadrangle", anchor: "#section-hero", image: "/assets/campus-lobby.jpg" },
  { id: "bg-section-library", label: "Central Library", anchor: "#section-features", image: "/assets/campus-gate.webp" },
  { id: "bg-section-courtyard", label: "Campus Courtyard", anchor: "#section-cta", image: "/assets/campus-lawn.jpg" },
] as const;

/** Fixed full-screen campus photos that cross-fade (see useSectionBackground). */
export function CampusBackdrop({ active, overlay }: { active: string; overlay: ReactNode }) {
  return (
    <div className="fixed inset-0 z-0 overflow-hidden pointer-events-none" aria-hidden="true">
      {CAMPUS_LAYERS.map((layer) => (
        <div
          key={layer.id}
          className={`bg-layer${layer.id === active ? " active" : ""}`}
          style={{ backgroundImage: `url("${layer.image}")` }}
        />
      ))}
      {overlay}
    </div>
  );
}

/** Dots on the right edge that show / jump to the current campus view (desktop only). */
export function VantagePills({ active }: { active: string }) {
  return (
    <div className="fixed right-5 top-1/2 -translate-y-1/2 z-40 hidden lg:flex flex-col gap-4 pointer-events-auto">
      {CAMPUS_LAYERS.map((layer) => {
        const on = layer.id === active;
        return (
          <a
            key={layer.id}
            href={layer.anchor}
            className={`group flex items-center justify-end gap-2.5 text-xs hover:text-white transition-all ${on ? "text-white" : "text-white/70"}`}
          >
            <span className="px-2.5 py-1 rounded-full text-[11px] font-medium bg-[#EBE7F5]/20 backdrop-blur-md border border-white/30 opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap shadow-sm">
              {layer.label}
            </span>
            <span
              className={`rounded-full border transition-all duration-300 ${on
                ? "border-white/60 bg-white w-3 h-3 shadow-[0_0_12px_rgba(255,255,255,0.7)]"
                : "border-white/40 bg-white/20 w-2.5 h-2.5"}`}
            />
          </a>
        );
      })}
    </div>
  );
}
