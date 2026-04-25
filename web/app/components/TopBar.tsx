"use client";

import { ThemeToggle } from "./ThemeToggle";

interface Props {
  onSpawn: () => void;
  theme: "dark" | "light";
  onToggleTheme: () => void;
  detailOpen: boolean;
  onToggleDetail: () => void;
}

export function TopBar({ onSpawn, theme, onToggleTheme, detailOpen, onToggleDetail }: Props) {
  return (
    <header className="topbar">
      <div className="brand">
        <div className="brand-mark">
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
            <path d="M 16 30 L 16 14" stroke="var(--bark-light)" strokeWidth="2" strokeLinecap="round" />
            <path
              d="M 16 14 C 9 14, 6 9, 10 5 C 12 2, 16 2, 17 5 C 21 3, 26 6, 24 11 C 27 12, 26 16, 21 15 C 19 17, 14 17, 13 15 C 9 16, 7 13, 10 11 Z"
              fill="var(--moss-mid)"
              opacity="0.55"
            />
            <path
              d="M 16 13 C 11 13, 9 9, 12 6 C 15 4, 18 5, 19 7 C 22 6, 24 9, 22 12 C 20 14, 17 14, 16 13 Z"
              fill="var(--leaf)"
              opacity="0.85"
            />
            <circle cx="13" cy="9" r="1.4" fill="var(--leaf-light)" opacity="0.9" />
            <circle cx="20" cy="10" r="1" fill="var(--sage)" opacity="0.8" />
          </svg>
        </div>
        <div className="brand-name">
          Treehouse<em>.</em>
        </div>
        <div className="brand-sep" />
        <div className="brand-repo">
          <span>linear-app</span>
          <span className="slash">/</span>
          <span className="repo-name">monorepo</span>
        </div>
      </div>
      <div className="topbar-actions">
        <span className="kbd-hint" style={{ marginRight: 12 }}>
          <kbd>S</kbd> spawn · <kbd>M</kbd> merge · <kbd>D</kbd> detail · <kbd>?</kbd> help
        </span>
        <button className="btn btn-ghost btn-sm">Server :8080</button>
        <button
          className="btn btn-ghost btn-sm panel-toggle"
          onClick={onToggleDetail}
          aria-label={detailOpen ? "Hide detail panel" : "Show detail panel"}
          aria-pressed={detailOpen}
          title={detailOpen ? "Hide detail panel (D)" : "Show detail panel (D)"}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
            <rect
              x="1"
              y="2"
              width="12"
              height="10"
              rx="1.5"
              stroke="currentColor"
              strokeWidth="1.2"
              fill="none"
            />
            <line x1="9" y1="2" x2="9" y2="12" stroke="currentColor" strokeWidth="1.2" />
            <rect
              x="9"
              y="2"
              width="4"
              height="10"
              fill={detailOpen ? "currentColor" : "none"}
              opacity={detailOpen ? 0.35 : 0}
            />
          </svg>
          <span style={{ marginLeft: 6 }}>{detailOpen ? "Hide panel" : "Show panel"}</span>
          <span className="kbd" style={{ marginLeft: 6 }}>D</span>
        </button>
        <ThemeToggle theme={theme} onToggle={onToggleTheme} />
        <button className="btn btn-primary" onClick={onSpawn}>
          + Spawn agent <span className="kbd">S</span>
        </button>
      </div>
    </header>
  );
}
