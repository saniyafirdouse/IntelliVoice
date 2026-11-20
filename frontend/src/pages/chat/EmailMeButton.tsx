// "Email me" button (2026-11-20). Shown only to signed-in students, and only when the
// backend has an email account set up (SMTP_USER + SMTP_APP_PASSWORD in .env).
// Sends to the student's own login email.
import { useEffect, useState } from "react";
import { Icon } from "../../components/Icon";
import { useAuth } from "../../context/AuthContext";
import { ApiError, emailEnabled, emailMe } from "../../lib/api";

export function EmailMeButton({ kind, question, answer, label = "Email", className, style }: {
  kind: "answer" | "starred" | "checklist";
  question?: string;
  answer?: string;
  label?: string;
  className: string;
  style?: React.CSSProperties;
}) {
  const { token } = useAuth();
  const [enabled, setEnabled] = useState(false);
  const [state, setState] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [note, setNote] = useState("");

  useEffect(() => {
    let alive = true;
    if (token) emailEnabled(token).then((on) => { if (alive) setEnabled(on); });
    return () => { alive = false; };
  }, [token]);

  if (!token || !enabled) return null;

  const send = async () => {
    setState("sending");
    try {
      const res = await emailMe(token, { kind, question, answer });
      setNote(res.message);
      setState("sent");
    } catch (err) {
      setNote(err instanceof ApiError ? err.message : "Couldn't send the email. Please try again.");
      setState("error");
    }
  };

  return (
    <button type="button" onClick={() => void send()} disabled={state === "sending" || state === "sent"} className={className} style={style} title={note || "Send this to your email"}>
      <Icon name={state === "sent" ? "mark_email_read" : state === "error" ? "error" : "mail"} className="text-[18px]" />
      <span>{state === "sending" ? "Sending…" : state === "sent" ? "Sent to your email" : state === "error" ? "Not sent, retry" : label}</span>
    </button>
  );
}
