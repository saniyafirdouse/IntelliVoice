// Expo stall page (2026-11-01): a big QR code of this site's address, so visitors
// talk to Eva on their own phones. Open it at /expo on the second screen (or print it).
// The address comes from the browser bar, so it is always the current Cloudflare
// tunnel address on expo day. Not linked from the menu on purpose.
import { useEffect, useState } from "react";
import { EvaAvatar } from "../components/EvaAvatar";
import { Icon } from "../components/Icon";

export default function ExpoPage() {
  const [url, setUrl] = useState("");
  const [qrFailed, setQrFailed] = useState(false);
  useEffect(() => {
    document.title = "Talk to Eva · IntelliVoice";
    setUrl(`${window.location.origin}/chat`);
  }, []);
  const local = /localhost|127\.0\.0\.1/.test(url);
  // QR picture from a free QR service (the tunnel needs the internet anyway); the address is also shown as text.
  const qr = url ? `https://api.qrserver.com/v1/create-qr-code/?size=640x640&margin=12&data=${encodeURIComponent(url)}` : "";

  return (
    <main className="min-h-screen w-full flex items-center justify-center p-6 relative text-white" style={{ background: "#14101c" }}>
      <div className="absolute inset-0 bg-cover bg-center" style={{ backgroundImage: 'url("/assets/campus-front.jpg")', filter: "brightness(0.45) blur(3px)" }} aria-hidden="true" />
      <div className="relative w-full max-w-5xl grid grid-cols-1 md:grid-cols-2 gap-8 items-center rounded-[28px] p-8 md:p-12"
        style={{ background: "linear-gradient(160deg, rgba(34, 24, 52, 0.88), rgba(18, 14, 28, 0.92))", border: "1px solid rgba(232, 211, 163, 0.45)", boxShadow: "0 24px 60px rgba(0,0,0,0.5)" }}>
        <div className="flex flex-col gap-5">
          <div className="flex items-center gap-4">
            <EvaAvatar size={84} />
            <div>
              <p className="text-[15px] font-semibold" style={{ color: "#e8d3a3" }}>SVIT Admissions · IntelliVoice</p>
              <h1 className="text-[40px] md:text-[48px] font-bold leading-tight">Talk to Eva</h1>
            </div>
          </div>
          <p className="text-[19px] text-white/90 leading-relaxed">Ask about admissions, fees, cutoffs, hostel, buses and placements, in English, ಕನ್ನಡ or हिंदी.</p>
          <ol className="flex flex-col gap-3 list-none p-0 m-0">
            {[
              { icon: "qr_code_scanner", text: "Scan the code with your phone camera" },
              { icon: "mic", text: "Allow the microphone when asked" },
              { icon: "record_voice_over", text: "Say “Hey Eva” or tap Speak to Eva, and ask" },
            ].map((s, i) => (
              <li key={s.icon} className="flex items-center gap-3 text-[17px]">
                <span className="w-9 h-9 rounded-full flex items-center justify-center font-bold flex-shrink-0" style={{ background: "#e8d3a3", color: "#2d1f45" }}>{i + 1}</span>
                <Icon name={s.icon} className="text-[22px] text-white/80" />
                {s.text}
              </li>
            ))}
          </ol>
          <p className="text-[13.5px] text-white/60">Each phone can ask 10 questions every 5 minutes, so everyone gets a turn. Works best in Chrome.</p>
        </div>

        <div className="flex flex-col items-center gap-4">
          <div className="rounded-2xl p-4 bg-white" style={{ boxShadow: "0 0 0 6px rgba(232, 211, 163, 0.5)" }}>
            {qr && !qrFailed ? (
              <img src={qr} alt={`QR code for ${url}`} width={320} height={320} className="w-[min(70vw,320px)] h-[min(70vw,320px)]" onError={() => setQrFailed(true)} />
            ) : (
              <div className="w-[min(70vw,320px)] h-[min(70vw,320px)] flex items-center justify-center text-center text-[#2d1f45] p-4">
                {qrFailed ? "The QR picture needs the internet. Type the address below instead." : "Preparing the code…"}
              </div>
            )}
          </div>
          <p className="text-[17px] font-semibold break-all text-center" style={{ color: "#e8d3a3" }}>{url}</p>
          {local && (
            <p className="text-[13px] text-center px-3 py-2 rounded-xl" style={{ background: "rgba(255, 138, 128, 0.15)", color: "#ffb4ab" }}>
              This is the laptop's own address — phones can't open it. Start the Cloudflare tunnel and open this page through the tunnel address.
            </p>
          )}
        </div>
      </div>
    </main>
  );
}
