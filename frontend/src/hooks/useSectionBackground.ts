import { useEffect, useRef, useState } from "react";

/**
 * Cross-fades the campus photos as the user scrolls.
 * Every <section data-bg="..."> inside the returned ref decides which background is active.
 */
export function useSectionBackground<T extends HTMLElement>(initial: string) {
  const ref = useRef<T>(null);
  const [active, setActive] = useState(initial);

  useEffect(() => {
    const root = ref.current;
    if (!root || typeof IntersectionObserver === "undefined") return;
    const sections = root.querySelectorAll<HTMLElement>("section[data-bg]");
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const id = (entry.target as HTMLElement).dataset.bg;
          if (entry.isIntersecting && id) setActive(id);
        });
      },
      { threshold: 0.35, rootMargin: "-10% 0px -10% 0px" },
    );
    sections.forEach((s) => observer.observe(s));
    return () => observer.disconnect();
  }, []);

  return { ref, active };
}
