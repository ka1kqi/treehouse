"use client";

import type { Agent } from "@/lib/mockData";
import { LeafIcon } from "./LeafIcon";
import { StatusPill } from "./StatusPill";

interface Props {
  agents: Agent[];
  activeId: string | null;
  onSelect: (id: string) => void;
}

const LEAF_COLOR: Record<string, string> = {
  running: "var(--leaf-light)",
  done: "var(--sage)",
  failed: "var(--rust)",
  merging: "var(--amber)",
  merged: "var(--ash)",
  pending: "var(--ash-2)",
};

export function AgentTable({ agents, activeId, onSelect }: Props) {
  return (
    <section className="agents">
      <table className="agents-table">
        <thead>
          <tr>
            <th style={{ width: 200 }}>Branch</th>
            <th>Task</th>
            <th style={{ width: 120 }}>Status</th>
            <th style={{ width: 110 }}>Runtime</th>
            <th style={{ width: 220 }}>Ports</th>
          </tr>
        </thead>
        <tbody>
          {agents.map((a) => (
            <tr
              key={a.id}
              className={a.id === activeId ? "active" : ""}
              onClick={() => onSelect(a.id)}
            >
              <td className="col-name">
                <span className="leaf-icon">
                  <LeafIcon size={11} color={LEAF_COLOR[a.status] ?? "var(--ash-2)"} />
                </span>
                {a.name}
              </td>
              <td className="col-task">{a.task}</td>
              <td>
                <StatusPill status={a.status} />
              </td>
              <td className="col-runtime">{a.runtime}</td>
              <td className="col-ports">
                {a.ports.slice(0, 4).map((p, i) => (
                  <span key={i}>
                    {i > 0 && <span className="pmono"> · </span>}
                    {p.svc}
                    <span className="pmono">:</span>
                    {p.host}
                  </span>
                ))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
