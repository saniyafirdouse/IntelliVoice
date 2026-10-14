// "Talk to a Human Officer" pop-up (2026-10-14, v3: frosted glass in the site's warm/sage theme).
// Real SVIT contact details from backend/engines/college_profile.py.
// Call Now -> phone dialer, Send Email -> email app, View on Map -> Google Maps (SVIT pin).

import { useEffect, useRef, useState, type ReactNode } from "react";
import { Icon } from "../../components/Icon";

// ---- verified contact details (same as the backend's college_profile.py) ----
export const SVIT_CONTACT = {
  phoneDisplay: "080-2846-8191",
  phoneTel: "+918028468191",
  mobileDisplay: "+91 91085 75191",
  email: "admissions@saividya.ac.in",
  hours: ["Mon – Fri, 8:30 AM – 4:10 PM", "Saturday, 8:30 AM – 12:50 PM"],
  office: "Admissions Section, Sai Vidya Institute of Technology, Rajanukunte, via Yelahanka, Bengaluru – 560119",
  mapUrl: "https://maps.app.goo.gl/e2V7E3GS7vs4bnwRA",
};

// ---- glass palette (the site's warm + sage theme) ----
const C = {
  ink: "#ffffff",
  body: "rgba(255, 252, 245, 0.82)",
  muted: "rgba(240, 232, 214, 0.68)",
  line: "rgba(255, 245, 225, 0.16)",
  sage: "#ced8aa",                       // icons / accents
  sageTint: "rgba(157, 184, 124, 0.18)",
  callFill: "#c2cc99",                   // primary button (same as the site's sage)
  callText: "#1d2214",
};
const serif = { fontFamily: '"Cormorant Garamond", Georgia, serif' };

function CopyButton({ value, label }: { value: string; label: string }) {
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      aria-label={`Copy ${label}`}
      title={done ? "Copied" : `Copy ${label}`}
      onClick={() => { void navigator.clipboard?.writeText(value).then(() => { setDone(true); window.setTimeout(() => setDone(false), 1400); }).catch(() => undefined); }}
      className="h-8 px-2.5 flex-shrink-0 rounded-lg flex items-center gap-1 text-[12.5px] font-medium transition-colors hover:bg-white/10"
      style={{ color: done ? C.sage : C.muted }}
    >
      <Icon name={done ? "check" : "content_copy"} className="text-[16px]" />
      <span className="hidden sm:inline">{done ? "Copied" : "Copy"}</span>
    </button>
  );
}

function Row({ icon, label, children, action }: { icon: string; label: string; children: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex items-start gap-3.5 py-3.5">
      <span className="w-9 h-9 flex-shrink-0 rounded-lg flex items-center justify-center" style={{ background: C.sageTint, border: "1px solid rgba(206, 216, 170, 0.25)" }}>
        <Icon name={icon} className="text-[19px]" style={{ color: C.sage }} />
      </span>
      <div className="flex-1 min-w-0">
        <div className="text-[11.5px] font-semibold uppercase tracking-[0.08em]" style={{ color: C.muted }}>{label}</div>
        <div className="mt-0.5 text-[15px] leading-snug" style={{ color: C.ink }}>{children}</div>
      </div>
      {action}
    </div>
  );
}

const BTN = "h-11 px-4 rounded-xl flex items-center justify-center gap-2 text-[14.5px] font-semibold transition-colors";

export function ContactDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { window.removeEventListener("keydown", onKey); document.body.style.overflow = prev; };
  }, [open, onClose]);

  if (!open) return null;
  const c = SVIT_CONTACT;

  return (
    <div
      className="fixed inset-0 z-[70] flex items-center justify-center p-4 overflow-y-auto"
      style={{ background: "rgba(14, 11, 8, 0.34)", backdropFilter: "blur(10px)", WebkitBackdropFilter: "blur(10px)" }}
      onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <style>{`
        @keyframes iv-pop { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
        .iv-pop { animation: iv-pop 0.2s ease-out; }
        @media (prefers-reduced-motion: reduce) { .iv-pop { animation: none; } }
      `}</style>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="iv-contact-title"
        className="iv-pop relative w-full max-w-[540px] my-auto rounded-[24px] overflow-hidden"
        style={{
          background: "linear-gradient(150deg, rgba(255, 246, 228, 0.22) 0%, rgba(96, 82, 62, 0.3) 45%, rgba(58, 68, 42, 0.36) 100%)",
          backdropFilter: "blur(26px) saturate(150%)",
          WebkitBackdropFilter: "blur(26px) saturate(150%)",
          border: "1px solid rgba(255, 245, 225, 0.32)",
          boxShadow: "0 24px 60px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.28), inset 0 -1px 0 rgba(255, 255, 255, 0.06)",
        }}
      >
        {/* subtle decoration: soft sage glow, warm glow, and the site's thin line with a light dot */}
        <div className="absolute -top-24 -right-20 w-64 h-64 rounded-full pointer-events-none" style={{ background: "radial-gradient(circle, rgba(157, 184, 124, 0.35), transparent 70%)" }} aria-hidden="true" />
        <div className="absolute -bottom-28 -left-16 w-72 h-72 rounded-full pointer-events-none" style={{ background: "radial-gradient(circle, rgba(233, 176, 122, 0.22), transparent 70%)" }} aria-hidden="true" />
        <svg viewBox="0 0 540 120" preserveAspectRatio="none" className="absolute right-0 top-[62px] w-[60%] h-[70px] pointer-events-none" aria-hidden="true">
          <path d="M0 96 C 90 92 150 40 260 52 S 420 104 540 30" fill="none" stroke="rgba(255, 250, 220, 0.35)" strokeWidth="1" />
          <circle cx="260" cy="52" r="7" fill="rgba(255, 255, 209, 0.25)" />
          <circle cx="260" cy="52" r="2.4" fill="#ffffd1" />
        </svg>
        <div className="absolute inset-x-8 top-0 h-px pointer-events-none" style={{ background: "linear-gradient(90deg, transparent, rgba(255, 245, 220, 0.8), transparent)" }} aria-hidden="true" />
        {/* header */}
        <div className="relative flex items-start gap-4 px-6 pt-6 pb-4">
          <span className="w-11 h-11 flex-shrink-0 rounded-xl flex items-center justify-center" style={{ background: C.sageTint, border: "1px solid rgba(206, 216, 170, 0.35)", boxShadow: "0 0 18px rgba(157, 184, 124, 0.25)" }}>
            <Icon name="support_agent" className="text-[24px]" style={{ color: C.sage }} />
          </span>
          <div className="flex-1 min-w-0">
            <h2 id="iv-contact-title" className="text-[29px] leading-tight" style={{ ...serif, fontWeight: 600, color: C.ink, textShadow: "0 1px 8px rgba(0,0,0,0.25)" }}>
              Talk to a <span style={{ color: C.sage }}>Human Officer</span>
            </h2>
            <p className="mt-1 text-[14.5px] leading-snug" style={{ color: C.body }}>
              Our admission team can help with admissions, fees, cutoffs, placements and hostels.
            </p>
          </div>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="w-9 h-9 -mr-1 -mt-1 flex-shrink-0 rounded-full flex items-center justify-center transition-colors hover:bg-white/15 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/60"
            style={{ color: C.muted }}
          >
            <Icon name="close" className="text-[22px]" />
          </button>
        </div>

        {/* details */}
        <div className="relative mx-6 px-4 rounded-2xl divide-y" style={{ background: "rgba(20, 18, 14, 0.18)", border: `1px solid ${C.line}` }}>
          <div style={{ borderColor: C.line }}>
            <Row icon="call" label="Phone" action={<CopyButton value={c.phoneDisplay} label="phone number" />}>
              {c.phoneDisplay}
              <span className="block text-[13px] whitespace-nowrap" style={{ color: C.muted }}>Mobile: {c.mobileDisplay}</span>
            </Row>
          </div>
          <div style={{ borderColor: C.line }}>
            <Row icon="mail" label="Email" action={<CopyButton value={c.email} label="email address" />}>
              <span className="whitespace-nowrap text-[14px] sm:text-[15px]">{c.email}</span>
            </Row>
          </div>
          <div style={{ borderColor: C.line }}>
            <Row icon="schedule" label="Office hours">{c.hours[0]}<span className="block">{c.hours[1]}</span></Row>
          </div>
          <div style={{ borderColor: C.line }}>
            <Row icon="location_on" label="Address">{c.office}</Row>
          </div>
        </div>

        {/* actions */}
        <div className="relative px-6 pt-5 pb-6 grid grid-cols-1 sm:grid-cols-3 gap-2.5">
          <a href={`tel:${c.phoneTel}`} className={`${BTN} hover:brightness-105`} style={{ background: C.callFill, color: C.callText, boxShadow: "0 8px 22px rgba(194, 204, 153, 0.3)" }}>
            <Icon name="call" className="text-[18px]" />
            Call now
          </a>
          <a href={`mailto:${c.email}?subject=${encodeURIComponent("Admission enquiry")}`} className={`${BTN} hover:bg-white/15`} style={{ color: C.ink, border: "1px solid rgba(255, 245, 225, 0.3)", background: "rgba(255, 250, 240, 0.08)" }}>
            <Icon name="mail" className="text-[18px]" />
            Send email
          </a>
          <a href={c.mapUrl} target="_blank" rel="noopener noreferrer" className={`${BTN} hover:bg-white/15`} style={{ color: C.ink, border: "1px solid rgba(255, 245, 225, 0.3)", background: "rgba(255, 250, 240, 0.08)" }}>
            <Icon name="map" className="text-[18px]" />
            View on map
          </a>
        </div>
      </div>
    </div>
  );
}
