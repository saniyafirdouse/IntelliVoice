import { useCallback } from "react";
import { useNavigate } from "react-router-dom";

/** Opens the Voice Chat page and asks the given question straight away. */
export function useOpenChat() {
  const navigate = useNavigate();
  return useCallback((question?: string) => {
    navigate(question ? `/chat?q=${encodeURIComponent(question)}` : "/chat");
  }, [navigate]);
}
