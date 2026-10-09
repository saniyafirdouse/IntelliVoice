import type { Config } from "tailwindcss";
import forms from "@tailwindcss/forms";
import containerQueries from "@tailwindcss/container-queries";

// Design tokens exported from Google Stitch.
// "App" pages (Voice Chat, Help & FAQ, Sign In, Sign Up) use the plain token names.
// "Marketing" pages (Home, About) had slightly different values; those live under the "mk-" prefix.
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: { extend: {
  "colors": {
    "on-secondary-fixed-variant": "#3d417c",
    "inverse-primary": "#755564",
    "surface": "#121414",
    "secondary-fixed": "#e0e0ff",
    "surface-dim": "#121414",
    "on-tertiary-container": "#807e8a",
    "on-secondary": "#262a64",
    "on-primary": "#432835",
    "secondary-fixed-dim": "#bfc2ff",
    "inverse-on-surface": "#2f3131",
    "surface-bright": "#37393a",
    "outline-variant": "#4e4448",
    "surface-tint": "#e4bccc",
    "surface-container-lowest": "#0c0f0f",
    "tertiary": "#c8c5d2",
    "on-primary-fixed": "#2c1420",
    "on-background": "#e2e2e2",
    "primary-fixed": "#ffd8e8",
    "error-container": "#93000a",
    "surface-container": "#1e2020",
    "secondary": "#bfc2ff",
    "on-tertiary-fixed": "#1b1b24",
    "on-primary-container": "#997685",
    "on-secondary-fixed": "#10134f",
    "tertiary-fixed-dim": "#c8c5d2",
    "inverse-surface": "#e2e2e2",
    "primary-fixed-dim": "#e4bccc",
    "tertiary-fixed": "#e4e0ee",
    "surface-variant": "#333535",
    "background": "#121414",
    "on-error-container": "#ffdad6",
    "on-secondary-container": "#afb3f7",
    "on-primary-fixed-variant": "#5c3e4c",
    "primary-container": "#250e1a",
    "secondary-container": "#3f437f",
    "on-tertiary-fixed-variant": "#474550",
    "surface-container-high": "#282a2b",
    "on-error": "#690005",
    "tertiary-container": "#15151e",
    "outline": "#9a8d92",
    "surface-container-low": "#1a1c1c",
    "on-surface-variant": "#d2c3c7",
    "on-tertiary": "#302f3a",
    "error": "#ffb4ab",
    "on-surface": "#e2e2e2",
    "primary": "#e4bccc",
    "surface-container-highest": "#333535",
    "mk-secondary": "#bfc2ff",
    "mk-secondary-container": "#7E82C2",
    "mk-lavender-veil": "#EBE7F5",
    "mk-primary": "#e4bccc",
    "mk-surface": "rgba(235,231,245,0.2)",
    "mk-on-surface": "#ffffff",
    "mk-on-surface-variant": "#f0edf6"
  },
  "borderRadius": {
    "DEFAULT": "1rem",
    "lg": "2rem",
    "xl": "3rem",
    "full": "9999px"
  },
  "spacing": {
    "gutter-mobile": "1rem",
    "space-md": "1rem",
    "space-2xl": "4rem",
    "space-xl": "2.5rem",
    "space-xs": "0.25rem",
    "margin": "3rem",
    "gutter": "1.5rem",
    "margin-mobile": "1.25rem",
    "space-lg": "1.5rem",
    "space-sm": "0.5rem"
  },
  "fontFamily": {
    "label-md": [
      "Inter",
      "Noto Sans Kannada",
      "Noto Sans Devanagari",
      "sans-serif"
    ],
    "label-sm": [
      "Inter",
      "Noto Sans Kannada",
      "Noto Sans Devanagari",
      "sans-serif"
    ],
    "headline-lg-mobile": [
      "Outfit",
      "Noto Sans Kannada",
      "Noto Sans Devanagari",
      "sans-serif"
    ],
    "display": [
      "Outfit",
      "Noto Sans Kannada",
      "Noto Sans Devanagari",
      "sans-serif"
    ],
    "headline-sm": [
      "Outfit",
      "Noto Sans Kannada",
      "Noto Sans Devanagari",
      "sans-serif"
    ],
    "body-lg": [
      "Inter",
      "Noto Sans Kannada",
      "Noto Sans Devanagari",
      "sans-serif"
    ],
    "label-lg": [
      "Inter",
      "Noto Sans Kannada",
      "Noto Sans Devanagari",
      "sans-serif"
    ],
    "headline-md": [
      "Outfit",
      "Noto Sans Kannada",
      "Noto Sans Devanagari",
      "sans-serif"
    ],
    "headline-lg": [
      "Outfit",
      "Noto Sans Kannada",
      "Noto Sans Devanagari",
      "sans-serif"
    ],
    "title-md": [
      "Inter",
      "Noto Sans Kannada",
      "Noto Sans Devanagari",
      "sans-serif"
    ],
    "body-md": [
      "Inter",
      "Noto Sans Kannada",
      "Noto Sans Devanagari",
      "sans-serif"
    ],
    "title-lg": [
      "Outfit",
      "Noto Sans Kannada",
      "Noto Sans Devanagari",
      "sans-serif"
    ],
    "body-sm": [
      "Inter",
      "Noto Sans Kannada",
      "Noto Sans Devanagari",
      "sans-serif"
    ],
    "mk-display": [
      "Plus Jakarta Sans",
      "Outfit",
      "Noto Sans Kannada",
      "Noto Sans Devanagari",
      "sans-serif"
    ],
    "mk-headline-lg": [
      "Plus Jakarta Sans",
      "Outfit",
      "Noto Sans Kannada",
      "Noto Sans Devanagari",
      "sans-serif"
    ],
    "mk-body-md": [
      "Inter",
      "Noto Sans Kannada",
      "Noto Sans Devanagari",
      "sans-serif"
    ]
  },
  "fontSize": {
    "label-md": [
      "12px",
      {
        "lineHeight": "16px",
        "letterSpacing": "0.04em",
        "fontWeight": "500"
      }
    ],
    "label-sm": [
      "11px",
      {
        "lineHeight": "14px",
        "letterSpacing": "0.05em",
        "fontWeight": "600"
      }
    ],
    "headline-lg-mobile": [
      "30px",
      {
        "lineHeight": "38px",
        "letterSpacing": "-0.01em",
        "fontWeight": "600"
      }
    ],
    "display": [
      "56px",
      {
        "lineHeight": "64px",
        "letterSpacing": "-0.02em",
        "fontWeight": "600"
      }
    ],
    "headline-sm": [
      "22px",
      {
        "lineHeight": "30px",
        "fontWeight": "500"
      }
    ],
    "body-lg": [
      "16px",
      {
        "lineHeight": "26px",
        "fontWeight": "400"
      }
    ],
    "label-lg": [
      "14px",
      {
        "lineHeight": "20px",
        "letterSpacing": "0.02em",
        "fontWeight": "500"
      }
    ],
    "headline-md": [
      "28px",
      {
        "lineHeight": "36px",
        "letterSpacing": "-0.01em",
        "fontWeight": "500"
      }
    ],
    "headline-lg": [
      "40px",
      {
        "lineHeight": "48px",
        "letterSpacing": "-0.015em",
        "fontWeight": "600"
      }
    ],
    "title-md": [
      "16px",
      {
        "lineHeight": "24px",
        "fontWeight": "600"
      }
    ],
    "body-md": [
      "14px",
      {
        "lineHeight": "22px",
        "fontWeight": "400"
      }
    ],
    "title-lg": [
      "18px",
      {
        "lineHeight": "26px",
        "fontWeight": "600"
      }
    ],
    "body-sm": [
      "12px",
      {
        "lineHeight": "18px",
        "fontWeight": "400"
      }
    ]
  }
} },
  plugins: [forms({ strategy: "class" }), containerQueries],
} satisfies Config;
