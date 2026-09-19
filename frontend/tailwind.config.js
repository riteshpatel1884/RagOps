/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: ["./app/**/*.{js,jsx}", "./components/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // App-shell tokens
        bg: "rgb(var(--color-bg) / <alpha-value>)",
        surface: "rgb(var(--color-surface) / <alpha-value>)",
        surfaceHover: "rgb(var(--color-surface-hover) / <alpha-value>)",
        border: "rgb(var(--color-border) / <alpha-value>)",
        text: "rgb(var(--color-text) / <alpha-value>)",
        muted: "rgb(var(--color-muted) / <alpha-value>)",
        accent: "rgb(var(--color-accent) / <alpha-value>)",
        accentMuted: "rgb(var(--color-accent-muted) / <alpha-value>)",
        success: "rgb(var(--color-success) / <alpha-value>)",
        danger: "rgb(var(--color-danger) / <alpha-value>)",
        warning: "rgb(var(--color-warning) / <alpha-value>)",

        // Neutral scale used throughout the page content (headings, body
        // text, subtle backgrounds, borders). Overriding Tailwind's default
        // "slate" with theme-aware CSS vars means every existing
        // text-slate-*/bg-slate-*/border-slate-* class in the app already
        // adapts to light/dark automatically, with no per-page edits.
        slate: {
          50: "rgb(var(--color-slate-50) / <alpha-value>)",
          100: "rgb(var(--color-slate-100) / <alpha-value>)",
          200: "rgb(var(--color-slate-200) / <alpha-value>)",
          300: "rgb(var(--color-slate-300) / <alpha-value>)",
          400: "rgb(var(--color-slate-400) / <alpha-value>)",
          500: "rgb(var(--color-slate-500) / <alpha-value>)",
          600: "rgb(var(--color-slate-600) / <alpha-value>)",
          700: "rgb(var(--color-slate-700) / <alpha-value>)",
          800: "rgb(var(--color-slate-800) / <alpha-value>)",
          900: "rgb(var(--color-slate-900) / <alpha-value>)",
        },

        // Brand/accent scale. Several pages already reference bg-brand-600,
        // text-brand-700, etc. — this was previously undefined (those
        // classes silently rendered nothing). Defining it properly both
        // fixes that and gives the whole app one consistent indigo accent.
        brand: {
          50: "rgb(var(--color-brand-50) / <alpha-value>)",
          100: "rgb(var(--color-brand-100) / <alpha-value>)",
          200: "rgb(var(--color-brand-200) / <alpha-value>)",
          300: "rgb(var(--color-brand-300) / <alpha-value>)",
          400: "rgb(var(--color-brand-400) / <alpha-value>)",
          500: "rgb(var(--color-brand-500) / <alpha-value>)",
          600: "rgb(var(--color-brand-600) / <alpha-value>)",
          700: "rgb(var(--color-brand-700) / <alpha-value>)",
          800: "rgb(var(--color-brand-800) / <alpha-value>)",
          900: "rgb(var(--color-brand-900) / <alpha-value>)",
        },
      },
      fontFamily: {
        sans: ["var(--font-plex-sans)", "sans-serif"],
        mono: ["var(--font-plex-mono)", "monospace"],
      },
      borderRadius: {
        sm: "4px",
        md: "8px",
      },
      boxShadow: {
        card: "0 1px 2px 0 rgb(0 0 0 / 0.04), 0 1px 3px 0 rgb(0 0 0 / 0.06)",
      },
    },
  },
  plugins: [],
};
