"use client";

import { useEffect, useState } from "react";
import type { Agent } from "@/lib/mockData";

type Phase = "review" | "merging" | "conflicts" | "done";

interface Props {
  open: boolean;
  agent: Agent | null;
  onClose: () => void;
}

export function MergeModal({ open, agent, onClose }: Props) {
  const [phase, setPhase] = useState<Phase>("review");

  useEffect(() => {
    if (!open) return;
    setPhase("review");
  }, [open, agent?.id]);

  if (!open || !agent) return null;

  const conflicts = [
    {
      path: "src/auth/oauth/callback.ts",
      lines: 3,
      state:
        phase === "conflicts" ? "resolving" : phase === "done" ? "resolved" : "conflict",
    },
    {
      path: "src/auth/saml/state.ts",
      lines: 1,
      state: phase === "done" ? "resolved" : phase === "conflicts" ? "resolving" : "conflict",
    },
  ];

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal wide" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <div className="modal-eyebrow">graft · merge into trunk</div>
            <h3 className="modal-title">
              Merge{" "}
              <em style={{ fontStyle: "italic", color: "var(--leaf-light)" }}>{agent.name}</em> →
              main
            </h3>
          </div>
          <button className="modal-close" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="merge-flow">
          <div className="merge-side">
            <div className="head">FROM</div>
            <div className="branch">{agent.branch}</div>
            <div className="stat-line">
              {agent.edits} commits, {agent.files} files
            </div>
            <div className="stat-line">
              <span className="add">+ 247</span> &nbsp; <span className="del">− 89</span>
            </div>
            <div
              className="stat-line"
              style={{ color: "var(--ash)", fontSize: 11, marginTop: 12 }}
            >
              last activity {agent.runtime} ago
            </div>
          </div>

          <div className="merge-arrow">
            <svg viewBox="0 0 200 80" fill="none">
              <defs>
                <linearGradient id="merge-flow-g" x1="0" x2="1">
                  <stop offset="0%" stopColor="var(--leaf-light)" />
                  <stop offset="100%" stopColor="var(--sage)" />
                </linearGradient>
              </defs>
              <path
                d="M 10 20 Q 70 20, 100 40 T 190 60"
                stroke="url(#merge-flow-g)"
                strokeWidth="2"
                fill="none"
                strokeLinecap="round"
              />
              <path
                d="M 184 56 L 192 60 L 184 64"
                stroke="var(--sage)"
                strokeWidth="2"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <circle cx="10" cy="20" r="4" fill="var(--leaf-light)" />
              <circle cx="190" cy="60" r="4" fill="var(--sage)" />
            </svg>
            <span
              className="label"
              style={{ color: phase === "done" ? "var(--leaf-light)" : "var(--amber)" }}
            >
              {phase === "review"
                ? "ready to graft"
                : phase === "merging"
                  ? "running git merge…"
                  : phase === "conflicts"
                    ? "ai resolving · 2 files"
                    : "grafted ✓"}
            </span>
          </div>

          <div className="merge-side target">
            <div className="head">INTO</div>
            <div className="branch">main</div>
            <div className="stat-line">
              at <span style={{ color: "var(--bone)" }}>8a31bd4</span>
            </div>
            <div className="stat-line">{agent.spawnedAt} min behind branch base</div>
            <div
              className="stat-line"
              style={{ color: "var(--ash)", fontSize: 11, marginTop: 12 }}
            >
              fast-forward not possible
            </div>
          </div>
        </div>

        <div className="merge-conflicts">
          <div className="head">
            <div className="title">2 files in conflict</div>
            <div className="ai-pill">
              <span
                style={{
                  width: 5,
                  height: 5,
                  borderRadius: 3,
                  background: "var(--amber)",
                  display: "inline-block",
                }}
              />
              ai conflict resolution
            </div>
          </div>
          <div className="conflict-list">
            {conflicts.map((c, i) => (
              <div key={i} className={`conflict-row ${c.state}`}>
                <span className="icon">
                  {c.state === "resolved" ? "✓" : c.state === "resolving" ? "↻" : "⚠"}
                </span>
                <span className="path">{c.path}</span>
                <span className="stat">{c.lines} hunks</span>
                <span className="state">
                  {c.state === "conflict"
                    ? "conflict"
                    : c.state === "resolving"
                      ? "resolving…"
                      : "resolved"}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="modal-foot">
          <span className="hint">
            falls back to <span style={{ color: "var(--leaf-light)" }}>claude --print</span> if
            conflicts
          </span>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn-ghost" onClick={onClose}>
              Close
            </button>
            {phase === "review" && (
              <button
                className="btn btn-primary"
                onClick={() => {
                  setPhase("merging");
                  setTimeout(() => setPhase("conflicts"), 900);
                  setTimeout(() => setPhase("done"), 2400);
                }}
              >
                Run merge
              </button>
            )}
            {phase === "done" && (
              <button className="btn btn-primary" onClick={onClose}>
                Done
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
