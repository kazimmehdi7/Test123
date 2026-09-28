import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Core tokens — used across ~450 call sites, kept stable.
        paper: "#F6F4EF",
        surface: "#FFFFFF",
        ink: "#14181C",
        muted: "#5B6470",
        rule: "#DDD8CD",
        customs: "#1E4E8C",
        go: "#1B7A4A",
        hold: "#B0741A",
        stop: "#B23A1E",
        // New: deeper/tint variants for layered depth and accent chips, additive only.
        "customs-deep": "#0F2E52",
        "customs-tint": "#EAF0F8",
        "go-tint": "#E8F5EE",
        "hold-tint": "#FBF1E1",
        "stop-tint": "#FBEBE6",
        "rule-strong": "#C9C2B3",
        "surface-sunken": "#FBFAF7",
      },
      fontFamily: { sans: ['"Public Sans"', "system-ui", "sans-serif"] },
      borderRadius: { sm: "4px", DEFAULT: "6px", lg: "10px", xl: "14px" },
      boxShadow: {
        xs: "0 1px 1px rgba(20, 24, 28, 0.04)",
        sm: "0 1px 2px rgba(20, 24, 28, 0.05), 0 1px 1px rgba(20, 24, 28, 0.04)",
        md: "0 6px 16px rgba(20, 24, 28, 0.08), 0 2px 6px rgba(20, 24, 28, 0.05)",
        lg: "0 16px 40px rgba(20, 24, 28, 0.14), 0 4px 10px rgba(20, 24, 28, 0.06)",
        glow: "0 0 0 1px rgba(30, 78, 140, 0.12), 0 8px 24px rgba(30, 78, 140, 0.14)",
      },
      backgroundImage: {
        "grad-customs": "linear-gradient(180deg, #24589E, #123259)",
        "grad-mesh": "radial-gradient(1100px 560px at 12% -10%, rgba(30,78,140,0.08), transparent 60%), radial-gradient(900px 480px at 100% 0%, rgba(178,58,30,0.05), transparent 55%)",
      },
      keyframes: {
        shimmer: { "0%": { backgroundPosition: "-200% 0" }, "100%": { backgroundPosition: "200% 0" } },
      },
      animation: { shimmer: "shimmer 2.2s linear infinite" },
    },
  },
  plugins: [],
} satisfies Config;
