/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,jsx}", "./components/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0B0E14",
        surface: "#12161F",
        surfaceHover: "#171C28",
        border: "#232838",
        text: "#E4E7EE",
        muted: "#8189A0",
        accent: "#7C8CF8",
        accentMuted: "#4A4F8C",
        success: "#4ADE80",
        danger: "#F87171",
        warning: "#FBBF6E",
      },
      fontFamily: {
        sans: ["var(--font-plex-sans)", "sans-serif"],
        mono: ["var(--font-plex-mono)", "monospace"],
      },
      borderRadius: {
        sm: "3px",
        md: "5px",
      },
    },
  },
  plugins: [],
};
