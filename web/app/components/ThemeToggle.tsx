"use client";

interface Props {
  theme: "dark" | "light";
  onToggle: () => void;
}

export function ThemeToggle({ theme, onToggle }: Props) {
  return (
    <button
      className="theme-toggle"
      onClick={onToggle}
      aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
      title={theme === "dark" ? "Switch to sunlit clearing" : "Switch to dusk forest"}
    >
      <span className="tt-track">
        <span className="tt-thumb">
          {theme === "dark" ? (
            <svg width="11" height="11" viewBox="0 0 12 12" fill="none">
              <path d="M 9 7.5 A 4 4 0 1 1 4.5 3 A 3 3 0 0 0 9 7.5 Z" fill="currentColor" />
            </svg>
          ) : (
            <svg width="11" height="11" viewBox="0 0 12 12" fill="none">
              <circle cx="6" cy="6" r="2.4" fill="currentColor" />
              <g stroke="currentColor" strokeWidth="1" strokeLinecap="round">
                <line x1="6" y1="1" x2="6" y2="2.4" />
                <line x1="6" y1="9.6" x2="6" y2="11" />
                <line x1="1" y1="6" x2="2.4" y2="6" />
                <line x1="9.6" y1="6" x2="11" y2="6" />
                <line x1="2.4" y1="2.4" x2="3.4" y2="3.4" />
                <line x1="8.6" y1="8.6" x2="9.6" y2="9.6" />
                <line x1="2.4" y1="9.6" x2="3.4" y2="8.6" />
                <line x1="8.6" y1="3.4" x2="9.6" y2="2.4" />
              </g>
            </svg>
          )}
        </span>
      </span>
    </button>
  );
}
