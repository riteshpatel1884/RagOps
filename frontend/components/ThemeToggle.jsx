"use client";

import { useEffect, useState } from "react";
import { Sun, Moon } from "lucide-react";

// Deliberately just two options — Light and Dark, each its own button — so
// which theme is active is never ambiguous the way a single flip-icon can be.
export default function ThemeToggle({ className = "" }) {
  const [theme, setTheme] = useState(null);

  useEffect(() => {
    setTheme(document.documentElement.classList.contains("dark") ? "dark" : "light");
  }, []);

  function choose(next) {
    document.documentElement.classList.toggle("dark", next === "dark");
    try {
      localStorage.setItem("ragops-theme", next);
    } catch (e) {
      /* ignore (private browsing, storage disabled, etc.) */
    }
    setTheme(next);
  }

  if (theme === null) {
    return <div className={`h-8 w-[68px] ${className}`} />;
  }

  return (
    <div className={`flex items-center gap-0.5 rounded-md border border-border bg-bg p-0.5 ${className}`}>
      <button
        type="button"
        onClick={() => choose("light")}
        aria-label="Light theme"
        aria-pressed={theme === "light"}
        className={`flex h-7 w-7 items-center justify-center rounded transition-colors ${
          theme === "light" ? "bg-surface text-text shadow-card" : "text-muted hover:text-text"
        }`}
      >
        <Sun size={14} />
      </button>
      <button
        type="button"
        onClick={() => choose("dark")}
        aria-label="Dark theme"
        aria-pressed={theme === "dark"}
        className={`flex h-7 w-7 items-center justify-center rounded transition-colors ${
          theme === "dark" ? "bg-surface text-text shadow-card" : "text-muted hover:text-text"
        }`}
      >
        <Moon size={14} />
      </button>
    </div>
  );
}
