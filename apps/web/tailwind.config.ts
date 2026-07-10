import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        filmBlack: "#050505",
        darkroom: "#141414",
        acidGreen: "#29f06f",
        hotRed: "#ff3b30",
        flashYellow: "#ffb000",
        deepPink: "#f20587"
      },
      fontFamily: {
        display: ["Arial Black", "Impact", "sans-serif"],
        body: ["Inter", "Arial", "sans-serif"]
      }
    }
  },
  plugins: []
};

export default config;
