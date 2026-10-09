import type { CSSProperties } from "react";

interface IconProps {
  name: string;
  className?: string;
  filled?: boolean;
  style?: CSSProperties;
}

/** Google Material Symbols icon (font loaded in index.html). */
export function Icon({ name, className = "", filled = false, style }: IconProps) {
  return (
    <span
      aria-hidden="true"
      className={`material-symbols-outlined ${className}`}
      style={filled ? { fontVariationSettings: '"FILL" 1', ...style } : style}
    >
      {name}
    </span>
  );
}
