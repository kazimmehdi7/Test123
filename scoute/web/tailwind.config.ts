import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#EEF1F3",
        surface: "#FFFFFF",
        ink: "#14212B",
        muted: "#5B6B78",
        rule: "#D5DCE1",
        customs: "#1E4E8C",
        go: "#1F7A4D",
        hold: "#B7791F",
        stop: "#B42318",
      },
      fontFamily: { sans: ['"Public Sans"', "system-ui", "sans-serif"] },
      borderRadius: { sm: "3px", DEFAULT: "4px" },
    },
  },
  plugins: [],
} satisfies Config;
