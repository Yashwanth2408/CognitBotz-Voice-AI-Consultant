import type { Config } from "tailwindcss"

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          bg: "#050505",
          surface: "#111111",
          panel: "#171717",
          border: "#2b2b2b",
          muted: "#8a8a8a",
          text: "#f2f2f2",
        },
        accent: {
          primary: "#ffffff",
          secondary: "#b6b6b6",
          danger: "#ef4444",
        },
      },
      animation: {
        "pulse-subtle": "pulse-subtle 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "glow": "glow 2s ease-in-out infinite",
      },
      keyframes: {
        "pulse-subtle": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.7" },
        },
        "glow": {
          "0%, 100%": { boxShadow: "0 0 0 rgba(255, 255, 255, 0)" },
          "50%": { boxShadow: "0 0 0 rgba(255, 255, 255, 0)" },
        },
      },
    },
  },
  plugins: [],
}
export default config
