import type { AgentStatus } from "@/lib/mockData";

const LABELS: Record<AgentStatus, string> = {
  running: "running",
  pending: "pending",
  done: "done",
  failed: "failed",
  merging: "merging",
  merged: "merged",
};

export function StatusPill({ status }: { status: AgentStatus }) {
  return (
    <span className={`pill ${status}`}>
      <span className="dot" />
      {LABELS[status]}
    </span>
  );
}
