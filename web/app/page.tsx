"use client";

import { useEffect, useMemo, useState } from "react";
import { AGENTS, NOW, TIMELINE_END, TRUNK_COMMITS, type Agent } from "@/lib/mockData";
import { TopBar } from "./components/TopBar";
import { ForestLegend } from "./components/ForestLegend";
import { ForestTimeline } from "./components/ForestTimeline";
import { AgentTable } from "./components/AgentTable";
import { DetailPanel } from "./components/DetailPanel";
import { SpawnModal } from "./components/SpawnModal";
import { MergeModal } from "./components/MergeModal";

type Theme = "dark" | "light";

export default function Page() {
  const [activeId, setActiveId] = useState<string>("auth-fix");
  const [agents] = useState<Agent[]>(AGENTS);
  const [spawnOpen, setSpawnOpen] = useState(false);
  const [mergeFor, setMergeFor] = useState<Agent | null>(null);
  const [theme, setTheme] = useState<Theme>("dark");
  const [detailOpen, setDetailOpen] = useState(true);

  // Read persisted theme + detail-panel visibility on mount (avoid SSR mismatch)
  useEffect(() => {
    try {
      const saved = localStorage.getItem("treehouse-theme");
      if (saved === "light" || saved === "dark") setTheme(saved);
      const savedDetail = localStorage.getItem("treehouse-detail-open");
      if (savedDetail === "false") setDetailOpen(false);
    } catch {}
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem("treehouse-detail-open", String(detailOpen));
    } catch {}
  }, [detailOpen]);

  useEffect(() => {
    if (theme === "light") {
      document.body.classList.add("theme-light");
    } else {
      document.body.classList.remove("theme-light");
    }
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem("treehouse-theme", theme);
    } catch {}
  }, [theme]);

  const active = agents.find((a) => a.id === activeId);

  const stats = useMemo(() => {
    const s = { running: 0, pending: 0, done: 0, failed: 0, merging: 0, merged: 0 };
    let totalTokens = 0,
      totalEdits = 0,
      containers = 0;
    for (const a of agents) {
      s[a.status] = (s[a.status] || 0) + 1;
      totalTokens += a.tokensIn + a.tokensOut;
      totalEdits += a.edits;
      if (
        a.status === "running" ||
        a.status === "done" ||
        a.status === "merging" ||
        a.status === "failed"
      ) {
        containers += a.ports.length;
      }
    }
    return { ...s, totalTokens, totalEdits, containers };
  }, [agents]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA")) return;
      if (e.key === "s" || e.key === "S") setSpawnOpen(true);
      if (e.key === "Escape") {
        setSpawnOpen(false);
        setMergeFor(null);
      }
      if ((e.key === "m" || e.key === "M") && active) setMergeFor(active);
      if (e.key === "d" || e.key === "D") setDetailOpen((v) => !v);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [active]);

  return (
    <>
      <TopBar
        onSpawn={() => setSpawnOpen(true)}
        theme={theme}
        onToggleTheme={() => setTheme(theme === "dark" ? "light" : "dark")}
        detailOpen={detailOpen}
        onToggleDetail={() => setDetailOpen((v) => !v)}
      />
      <div className={`shell${detailOpen ? "" : " no-detail"}`}>
        <div className="main-col">
          <div className="section-head">
            <div>
              <h2>The forest</h2>
            </div>
            <div className="legend">
              <span>
                <span className="legend-dot" style={{ background: "var(--st-running)" }} />
                running
              </span>
              <span>
                <span className="legend-dot" style={{ background: "var(--st-done)" }} />
                done
              </span>
              <span>
                <span className="legend-dot" style={{ background: "var(--st-merging)" }} />
                merging
              </span>
              <span>
                <span className="legend-dot" style={{ background: "var(--st-failed)" }} />
                failed
              </span>
              <span>
                <span className="legend-dot" style={{ background: "var(--st-merged)" }} />
                merged
              </span>
            </div>
          </div>

          <ForestLegend stats={stats} />

          <ForestTimeline
            agents={agents}
            trunkCommits={TRUNK_COMMITS}
            totalMins={TIMELINE_END}
            now={NOW}
            activeId={activeId}
            onSelect={setActiveId}
          />

          <div className="section-head" style={{ marginTop: 8 }}>
            <h2>Branches</h2>
            <span className="sub">{agents.length} workspaces · sorted by activity</span>
          </div>

          <AgentTable agents={agents} activeId={activeId} onSelect={setActiveId} />
        </div>

        {detailOpen && (
          <div className="side-col">
            <DetailPanel
              agent={active}
              onSpawnRequest={() => setSpawnOpen(true)}
              onMergeRequest={(a) => setMergeFor(a)}
            />
          </div>
        )}
      </div>

      <SpawnModal
        open={spawnOpen}
        onClose={() => setSpawnOpen(false)}
        onSpawn={() => {}}
        nextPortBase={3113}
      />
      <MergeModal open={!!mergeFor} agent={mergeFor} onClose={() => setMergeFor(null)} />
    </>
  );
}
