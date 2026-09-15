import type { Config } from "tailwindcss";

// Design tokens ported 1:1 from the legacy index.html :root CSS variables,
// so the new frontend stays visually consistent with the shipped brand
// rather than introducing a new palette mid-migration.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: "#0b1f3a",
        blue: "#175ca8",
        "blue-soft": "#eaf3ff",
        red: "#d62839",
        "red-soft": "#fff0f2",
        ink: "#172033",
        muted: "#607086",
        line: "#dbe4ef",
        panel: "#ffffff",
        bg: "#f5f8fc",
        green: "#16834a",
        amber: "#c47a00",
      },
      borderRadius: {
        card: "8px",
      },
      boxShadow: {
        panel: "0 16px 40px rgba(11, 31, 58, .10)",
        cta: "0 10px 24px rgba(214, 40, 57, .22)",
      },
      fontFamily: {
        sans: [
          "Segoe UI",
          "system-ui",
          "-apple-system",
          "Arial",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
};

export default config;
