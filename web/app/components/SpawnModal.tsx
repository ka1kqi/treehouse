"use client";

import { useState } from "react";
import { LeafIcon } from "./LeafIcon";

interface Props {
  open: boolean;
  onClose: () => void;
  onSpawn: (payload: { name: string; task: string; services: Services }) => void;
  nextPortBase?: number;
}

interface Services {
  web: boolean;
  api: boolean;
  db: boolean;
  redis: boolean;
}

export function SpawnModal({ open, onClose, onSpawn, nextPortBase }: Props) {
  const [name, setName] = useState("payment-retry");
  const [task, setTask] = useState(
    "Add idempotent retry to payment intent confirmation. Use the existing retry helper in /lib/retry.",
  );
  const [services, setServices] = useState<Services>({
    web: true,
    api: true,
    db: true,
    redis: false,
  });

  if (!open) return null;

  const branch = `treehouse/${name || "<name>"}`;
  const port = nextPortBase ?? 3109;
  const compose = `treehouse_${(name || "name").replace(/-/g, "_")}`;

  const portMap: { svc: string; c: number; h: number }[] = [];
  if (services.web) portMap.push({ svc: "web", c: 3000, h: 3000 + (port - 3100) });
  if (services.api) portMap.push({ svc: "api", c: 8000, h: 8000 + (port - 3100) });
  if (services.db) portMap.push({ svc: "db", c: 5432, h: 5500 + (port - 3100) });
  if (services.redis) portMap.push({ svc: "redis", c: 6379, h: 6400 + (port - 3100) });

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <div className="modal-eyebrow">+ new branch · plant a leaf</div>
            <h3 className="modal-title">Spawn agent</h3>
          </div>
          <button className="modal-close" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="modal-body">
          <div className="field">
            <label className="field-label">
              Branch name <span className="req">·</span>
            </label>
            <input
              className="field-input"
              value={name}
              onChange={(e) => setName(e.target.value.replace(/[^a-z0-9-]/g, ""))}
              placeholder="auth-fix"
              autoFocus
            />
            <div className="field-help">→ {branch}</div>
          </div>

          <div className="field">
            <label className="field-label">Task</label>
            <textarea
              className="field-textarea"
              value={task}
              onChange={(e) => setTask(e.target.value)}
              placeholder="Describe the task as you would to a senior engineer…"
              rows={4}
            />
            <div className="field-help">
              passed verbatim to <span style={{ color: "var(--leaf-light)" }}>claude --print</span>
            </div>
          </div>

          <div className="field">
            <label className="field-label">Services to isolate</label>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {(["web", "api", "db", "redis"] as const).map((s) => (
                <button
                  key={s}
                  className="btn btn-sm"
                  style={{
                    background: services[s] ? "var(--moss)" : "var(--bg)",
                    borderColor: services[s] ? "var(--moss-mid)" : "var(--line-2)",
                    color: services[s] ? "var(--bone)" : "var(--ash)",
                  }}
                  onClick={() => setServices({ ...services, [s]: !services[s] })}
                >
                  <LeafIcon size={10} color={services[s] ? "var(--leaf-light)" : "var(--ash-2)"} />
                  {s}
                </button>
              ))}
            </div>
          </div>

          <div className="preview-card">
            <div className="pc-eyebrow">Isolation preview</div>
            <div className="pc-row">
              <span className="k">branch</span>
              <span className="v">
                <span className="leaf">{branch}</span>
              </span>
            </div>
            <div className="pc-row">
              <span className="k">worktree</span>
              <span className="v">./.treehouse/worktrees/{name || "<name>"}</span>
            </div>
            <div className="pc-row">
              <span className="k">compose</span>
              <span className="v">{compose}</span>
            </div>
            <div className="pc-row">
              <span className="k">ports</span>
              <span className="v">
                {portMap.map((p, i) => (
                  <span key={i} style={{ marginRight: 14 }}>
                    {p.svc}
                    <span style={{ color: "var(--ash-2)" }}>:{p.c}</span>→
                    <span className="num">:{p.h}</span>
                  </span>
                ))}
              </span>
            </div>
          </div>
        </div>

        <div className="modal-foot">
          <span className="hint">
            <kbd>esc</kbd> to cancel · <kbd>⌘ ↵</kbd> to spawn
          </span>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn-ghost" onClick={onClose}>
              Cancel
            </button>
            <button
              className="btn btn-primary"
              onClick={() => {
                onSpawn({ name, task, services });
                onClose();
              }}
            >
              <LeafIcon size={11} color="var(--leaf-light)" /> Spawn branch
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
