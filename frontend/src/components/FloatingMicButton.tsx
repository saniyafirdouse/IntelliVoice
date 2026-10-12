import { useNavigate } from "react-router-dom";
import { Icon } from "./Icon";

interface Props {
  /** Visual style from the Stitch design. */
  variant: "marketing" | "app";
  /** On the chat page the button records directly; elsewhere it opens the chat page. */
  onClick?: () => void;
  active?: boolean;
}

export function FloatingMicButton({ variant, onClick, active = false }: Props) {
  const navigate = useNavigate();
  const handle = onClick ?? (() => navigate("/chat"));

  if (variant === "marketing") {
    return (
      <div className="fixed bottom-6 right-6 z-40">
        <button
          type="button"
          aria-label="Open the IntelliVoice voice assistant"
          onClick={handle}
          className="w-14 h-14 rounded-full flex items-center justify-center text-white shadow-2xl hover:scale-110 active:scale-95 transition-all duration-300 group cursor-pointer"
          style={{ background: "rgba(126, 130, 194, 0.88)", border: "1px solid rgba(255, 255, 255, 0.55)", boxShadow: "rgba(126, 130, 194, 0.6) 0px 0px 32px" }}
        >
          <Icon name="mic" className="text-[30px] group-hover:animate-pulse" />
        </button>
      </div>
    );
  }
  return (
    <div className="fixed bottom-space-lg right-space-lg z-40">
      <button
        type="button"
        aria-label={active ? "Stop recording and send" : onClick ? "Tap to speak your question" : "Open the IntelliVoice voice assistant"}
        onClick={handle}
        className="w-14 h-14 rounded-full flex items-center justify-center hover:scale-105 active:scale-95 transition-all duration-200"
        style={{
          background: active ? "linear-gradient(135deg, rgb(220, 38, 38), rgb(185, 28, 28))" : "rgb(126, 130, 194)",
          color: "#fff",
          boxShadow: "rgba(126, 130, 194, 0.55) 0px 0px 28px",
          border: "1px solid rgba(255, 255, 255, 0.3)",
        }}
      >
        <Icon name={active ? "stop" : "mic"} className="text-[28px]" />
      </button>
    </div>
  );
}
