"use client";

import { Fragment } from "react";
import type { Agent } from "@/lib/mockData";
import { BranchGlyph } from "./BranchGlyph";
import { StatusPill } from "./StatusPill";

interface Props {
  agent: Agent | undefined;
  onSpawnRequest: () => void;
  onMergeRequest: (a: Agent) => void;
}

export function DetailPanel({ agent, onSpawnRequest, onMergeRequest }: Props) {
  if (!agent) {
    return (
      <aside className="detail">
        <div className="detail-empty">
          <div>
            <div className="glyph">
              <svg width="56" height="56" viewBox="0 0 56 56" fill="none">
                <path d="M 28 4 L 28 52" stroke="currentColor" strokeWidth="2" />
                <path d="M 28 18 Q 16 18 14 26" stroke="currentColor" strokeWidth="1.5" fill="none" />
                <path d="M 28 28 Q 42 28 44 36" stroke="currentColor" strokeWidth="1.5" fill="none" />
                <circle cx="14" cy="26" r="3" fill="currentColor" opacity="0.6" />
                <circle cx="44" cy="36" r="3" fill="currentColor" opacity="0.6" />
                <circle cx="28" cy="6" r="3" fill="var(--leaf-light)" />
              </svg>
            </div>
            <div className="title">Select a branch</div>
            <p>Click a branch in the forest, or spawn a new one.</p>
          </div>
        </div>
        <div className="detail-actions">
          <button
            className="btn btn-primary"
            style={{ flex: 1, justifyContent: "center" }}
            onClick={onSpawnRequest}
          >
            <span>+ Spawn agent</span>
            <span className="kbd">S</span>
          </button>
        </div>
      </aside>
    );
  }

  const a = agent;

  return (
    <aside className="detail">
      <div className="detail-head">
        <div className="detail-eyebrow">
          <span className="branch-glyph">
            <BranchGlyph />
          </span>
          <span style={{ fontFamily: "var(--mono)" }}>{a.branch}</span>
        </div>
        <h3 className="detail-title">{a.name}</h3>
        <p className="detail-task">{a.task}</p>
        <div className="detail-meta">
          <StatusPill status={a.status} />
          <span>
            <b>{a.runtime}</b> runtime
          </span>
          <span>
            <b>{a.edits}</b> edits / <b>{a.files}</b> files
          </span>
        </div>
      </div>

      <div className="detail-stats">
        <div className="stat">
          <div className="stat-label">Tokens in</div>
          <div className="stat-value">{a.tokensIn.toLocaleString()}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Tokens out</div>
          <div className="stat-value">{a.tokensOut.toLocaleString()}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Compose project</div>
          <div className="stat-value" style={{ fontSize: 12 }}>
            treehouse_{a.id.replace(/-/g, "_")}
          </div>
        </div>
        <div className="stat">
          <div className="stat-label">Worktree</div>
          <div className="stat-value" style={{ fontSize: 12 }}>
            ./.treehouse/worktrees/{a.name}
          </div>
        </div>
      </div>

      <div className="ports">
        <div className="ports-title">Port allocations · :{a.portBase}xx</div>
        <div className="ports-list">
          {a.ports.map((p, i) => (
            <Fragment key={i}>
              <div className="svc">{p.svc}</div>
              <div className="num">
                <span style={{ color: "var(--ash-2)" }}>:{p.container}</span>
              </div>
              <div className="num host">→ :{p.host}</div>
            </Fragment>
          ))}
        </div>
      </div>

      <div className="logs">
        <div className="logs-head">
          <div className="title">stream-json · live</div>
          <span className="tag">tail -f</span>
        </div>
        <div className="logs-body">
          {a.log && a.log.length > 0 ? (
            a.log.map((l, i) => {
              if (l.tag === "indent") {
                return (
                  <div key={i} className="log-line indent">
                    <span className="ts"> </span>
                    <span className="text">↳ {l.text}</span>
                  </div>
                );
              }
              return (
                <div key={i} className="log-line">
                  <span className="ts">{l.ts}</span>
                  <span className={`tag ${l.tag}`}>[{l.tag}]</span>
                  <span className="text">{l.text}</span>
                </div>
              );
            })
          ) : (
            <div
              style={{
                color: "var(--ash-2)",
                fontStyle: "italic",
                fontFamily: "var(--serif)",
                fontSize: 14,
                padding: "20px 0",
              }}
            >
              {a.status === "pending"
                ? "Awaiting subprocess start…"
                : a.status === "merged"
                  ? "Branch merged. Logs archived."
                  : a.status === "failed"
                    ? "Subprocess exited with non-zero status."
                    : "No log entries yet."}
            </div>
          )}
        </div>
      </div>

      <div className="detail-actions">
        {(a.status === "done" || a.status === "running") && (
          <button className="btn btn-primary" onClick={() => onMergeRequest(a)}>
            Merge to main
          </button>
        )}
        {a.status === "running" && <button className="btn">Pause</button>}
        {a.status === "failed" && <button className="btn">Retry</button>}
        <button className="btn btn-ghost" style={{ marginLeft: "auto" }}>
          Open shell
        </button>
        {a.status !== "merged" && <button className="btn btn-danger">Destroy</button>}
      </div>
    </aside>
  );
}
