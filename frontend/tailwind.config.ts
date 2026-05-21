import type { Config } from "tailwindcss"

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        "dm-sans": ["DM Sans", "sans-serif"],
        "dm-mono": ["DM Mono", "monospace"],
      },
      colors: {
        // Dark theme color palette
        dark: {
          deepest: "#060607",
          main: "#0b0b0f",
          surface: "#141419",
          input: "#1a1a20",
          border: "#2a2a33",
          muted: "#727281",
          muted2: "#a2a2b3",
          card: "#16161d",
        },
        // Accent palette
        accent: {
          mauve: "#c4b5fd",
          rose: "#f9a8d4",
          user_from: "#ec4899",
          user_to: "#8b5cf6",
        },
      },
      backgroundColor: {
        "primary-dark": "#060607",
        "secondary-dark": "#0b0b0f",
      },
      borderColor: {
        "dark-border": "#2a2a33",
        "accent-border": "#3b3b47",
      },
      fontSize: {
        "body": ["14px", { lineHeight: "1.5", fontWeight: "400" }],
        "label": ["12px", { lineHeight: "1.4", fontWeight: "600", letterSpacing: "0.2px" }],
        "nav-title": ["15px", { lineHeight: "1.5", fontWeight: "600" }],
        "metric": ["28px", { lineHeight: "1.2", fontWeight: "600", letterSpacing: "-1px" }],
      },
      animation: {
        "pulse-dot": "pulse-dot 1.8s ease-in-out infinite",
        "bounce-dot": "bounce-dot 1.4s ease-in-out infinite",
        "orb-glow": "orb-glow 2s ease-in-out infinite",
        "voice-bar": "voice-bar 1s ease-in-out infinite",
        "progress-fill": "progress-fill 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94) forwards",
      },
      keyframes: {
        "pulse-dot": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.4" },
        },
        "bounce-dot": {
          "0%, 100%": { transform: "translateY(0)", opacity: "0.6" },
          "50%": { transform: "translateY(-8px)", opacity: "1" },
        },
        "orb-glow": {
          "0%, 100%": { boxShadow: "0 0 40px rgba(196, 181, 253, 0.25), 0 0 80px rgba(196, 181, 253, 0.12)" },
          "50%": { boxShadow: "0 0 60px rgba(196, 181, 253, 0.35), 0 0 120px rgba(196, 181, 253, 0.2)" },
        },
        "voice-bar": {
          "0%, 100%": { height: "6px" },
          "50%": { height: "28px" },
        },
        "progress-fill": {
          "from": { width: "0%" },
          "to": { width: "72%" },
        },
      },
      boxShadow: {
        "orb": "0 0 40px rgba(196, 181, 253, 0.25), 0 0 80px rgba(196, 181, 253, 0.12)",
        "orb-lg": "0 0 60px rgba(196, 181, 253, 0.35), 0 0 120px rgba(196, 181, 253, 0.2)",
      },
      backdropBlur: {
        "xl": "30px",
      },
    },
  },
  plugins: [],
}
export default config
