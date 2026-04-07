import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        primary: { DEFAULT: "#0066CC", dark: "#0052A3" },
        secondary: "#1E3A5F",
        accent: "#00A3FF",
        surface: "#FFFFFF",
        border: "#E2E8F0",
      },
      fontFamily: {
        sans: ["Pretendard", "-apple-system", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;
