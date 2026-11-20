// "Request a callback" (2026-11-20).
// The backend already saves callback requests (routes/callbacks.py, POST /api/callback) and
// the admission office sees them in the admin panel (Admin -> Callbacks).
// Used in the "Talk to a Human Officer" pop-up and under replies Eva couldn't answer.
// Signed-in students: name filled in, and the request shows under "Your chats -> Callbacks".
// 2026-11-20 (San): offered only when the admission office is CLOSED (evenings, Sundays) —
// during office hours "Call now" is the better choice. Also "Save contact" (vCard).
import { useState, type FormEvent } from "react";
import { Icon } from "../../components/Icon";
import { useAuth } from "../../context/AuthContext";
import { ApiError, requestCallback } from "../../lib/api";
import { storage } from "../../lib/storage";

// ── office hours (India time): Mon–Fri 8:30 am – 4:10 pm, Sat 8:30 am – 12:50 pm ──
const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const OPEN_MIN = 8 * 60 + 30;
const closeMin = (day: number) => (day === 6 ? 12 * 60 + 50 : day === 0 ? -1 : 16 * 60 + 10);

/** Is the SVIT admission office open right now? and when does it open next (for the message). */
export function officeStatus(now = new Date()): { open: boolean; nextOpen: string } {
  const parts = Object.fromEntries(new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Kolkata", weekday: "short", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
  }).formatToParts(now).map((p) => [p.type, p.value]));
  const day = DAYS.indexOf(parts.weekday);
  const minute = Number(parts.hour) * 60 + Number(parts.minute);
  const open = day > 0 && minute >= OPEN_MIN && minute < closeMin(day);
  if (open) return { open, nextOpen: "" };
  if (day > 0 && minute < OPEN_MIN) return { open, nextOpen: "today at 8:30 am" };
  const next = day === 6 || day === 0 ? 1 : day + 1;          // after Saturday / Sunday -> Monday
  return { open, nextOpen: next === (day + 1) % 7 ? `tomorrow (${DAY_NAMES[next]}) at 8:30 am` : `on ${DAY_NAMES[next]} at 8:30 am` };
}

/** "Save contact": a contact card (vCard). On phones it opens "Add to contacts". */
export function saveSvitContact() {
  const card = [
    "BEGIN:VCARD", "VERSION:3.0",
    "N:Admissions;SVIT;;;", "FN:SVIT Admissions",
    "ORG:Sai Vidya Institute of Technology", "TITLE:Admission Office",
    "TEL;TYPE=WORK,VOICE:+918028468191", "TEL;TYPE=CELL:+919108575191",
    "EMAIL;TYPE=WORK:admissions@saividya.ac.in",
    "ADR;TYPE=WORK:;;Rajanukunte, via Yelahanka;Bengaluru;Karnataka;560119;India",
    "URL:https://saividya.ac.in", "END:VCARD",
  ].join("\r\n");
  const url = URL.createObjectURL(new Blob([card], { type: "text/vcard;charset=utf-8" }));
  const a = Object.assign(document.createElement("a"), { href: url, download: "SVIT-Admissions.vcf" });
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 2000);
}

const TIMES = ["Any time (office hours)", "Morning (8:30 am – 12 noon)", "Afternoon (12 noon – 4 pm)"];  // when they call back
const FIELD = "w-full h-11 px-3.5 rounded-xl text-[15px] text-white placeholder:text-white/45 outline-none focus:ring-2 focus:ring-white/40";
const FIELD_STYLE = { background: "rgba(10, 9, 7, 0.38)", border: "1px solid rgba(255, 245, 225, 0.25)" } as const;

export function CallbackForm({ question, language, startOpen = false, onlyWhenClosed = true }: {
  question?: string; language?: string; startOpen?: boolean;
  /** true (default): shown only when the office is closed; during office hours people simply call */
  onlyWhenClosed?: boolean;
}) {
  const { token, user } = useAuth();
  const [open, setOpen] = useState(startOpen);
  const [name, setName] = useState(user?.name ?? "");
  const [phone, setPhone] = useState("");
  const [time, setTime] = useState(TIMES[0]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<{ reference: string; message: string } | null>(null);

  const office = officeStatus();
  if (onlyWhenClosed && office.open && !done) return null;

  if (done) {
    return (
      <div className="mt-3 px-4 py-3 rounded-xl text-[14.5px] text-white flex items-start gap-2.5" style={{ background: "rgba(120, 160, 90, 0.22)", border: "1px solid rgba(206, 216, 170, 0.5)" }} role="status">
        <Icon name="check_circle" className="text-[20px] mt-px" style={{ color: "#ced8aa" }} />
        <span>
          <strong>Request sent · Reference {done.reference}.</strong> {done.message}
          {token && <span className="block mt-1 text-white/75">You can follow it under “Your chats” → Callbacks.</span>}
        </span>
      </div>
    );
  }

  if (!open) {
    return (
      <div className="mt-3">
      <p className="text-[13.5px] text-white/80 flex items-start gap-1.5">
        <Icon name="schedule" className="text-[17px] mt-px" />
        <span>The admission office is closed now. It opens {office.nextOpen}. Leave your number and they'll call you then.</span>
      </p>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="mt-2 h-10 px-4 rounded-xl inline-flex items-center gap-2 text-[14.5px] font-semibold text-white transition-colors hover:bg-white/15"
        style={{ border: "1px solid rgba(255, 245, 225, 0.35)", background: "rgba(255, 250, 240, 0.08)" }}
      >
        <Icon name="phone_callback" className="text-[19px]" />
        Request a callback
      </button>
      </div>
    );
  }

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!name.trim()) { setError("Please enter your name."); return; }
    if (phone.replace(/\D/g, "").length < 10) { setError("Please enter a valid 10-digit phone number."); return; }
    setBusy(true);
    try {
      const res = await requestCallback({
        name: name.trim(),
        phone: phone.trim(),
        question: question?.slice(0, 500) || undefined,
        language,
        preferred_time: time,
        session_id: storage.get("iv_session_id", "session") || undefined,
      }, token);
      setDone({ reference: res.reference, message: res.message });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't send the request. Please try again or call the office.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={(e) => void submit(e)} className="mt-3 flex flex-col gap-2.5" aria-label="Request a callback">
      <p className="text-[14px] text-white/85 flex items-center gap-1.5">
        <Icon name="phone_callback" className="text-[18px]" />
        Leave your number and the admission office will call you back.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        <input className={FIELD} style={FIELD_STYLE} value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" maxLength={80} autoComplete="name" aria-label="Your name" />
        <input className={FIELD} style={FIELD_STYLE} value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="Phone number" inputMode="tel" maxLength={20} autoComplete="tel" aria-label="Phone number" />
      </div>
      <select className={FIELD} style={FIELD_STYLE} value={time} onChange={(e) => setTime(e.target.value)} aria-label="Best time to call">
        {TIMES.map((t) => <option key={t} value={t} className="text-black">{t}</option>)}
      </select>
      {question && <p className="text-[13px] text-white/60 truncate" title={question}>About: “{question}”</p>}
      {error && <p className="text-[13.5px]" style={{ color: "#ffb4ab" }} role="alert">{error}</p>}
      <div className="flex flex-wrap gap-2">
        <button type="submit" disabled={busy} className="h-10 px-5 rounded-xl text-[14.5px] font-semibold disabled:opacity-60" style={{ background: "#c2cc99", color: "#1d2214" }}>
          {busy ? "Sending…" : "Send request"}
        </button>
        <button type="button" onClick={() => setOpen(false)} className="h-10 px-4 rounded-xl text-[14px] text-white/80 hover:bg-white/10">Cancel</button>
      </div>
    </form>
  );
}
