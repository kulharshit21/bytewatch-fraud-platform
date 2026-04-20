import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#07111f",
        foreground: "#f4f7fb",
        panel: "#0f1b2d",
        panelMuted: "#10233c",
        border: "#1b324f",
        accent: "#4fc3a1",
        warning: "#f6bd60",
        danger: "#ff6b6b",
        muted: "#9fb3c8",
      },
      boxShadow: {
        panel: "0 20px 45px rgba(4, 8, 15, 0.35)",
      },
      fontFamily: {
        sans: ["var(--font-plex-sans)"],
        mono: ["var(--font-plex-mono)"],
      },
    },
  },
  plugins: [],
};

export default config;
