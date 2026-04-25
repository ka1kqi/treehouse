interface Stats {
  running: number;
  pending: number;
  done: number;
  failed: number;
  merging: number;
  merged: number;
  totalTokens: number;
  totalEdits: number;
  containers: number;
}

export function ForestLegend({ stats }: { stats: Stats }) {
  return (
    <div className="forest-meta">
      <div className="stats">
        <span>
          <b>{stats.running}</b>RUNNING
        </span>
        <span>
          <b>{stats.done}</b>DONE
        </span>
        <span>
          <b>{stats.merging}</b>MERGING
        </span>
        <span>
          <b>{stats.failed}</b>FAILED
        </span>
        <span>
          <b>{stats.merged}</b>MERGED
        </span>
      </div>
      <div className="stats">
        <span>
          <b>{stats.totalTokens.toLocaleString()}</b>TOKENS
        </span>
        <span>
          <b>{stats.totalEdits}</b>EDITS
        </span>
        <span>
          <b>{stats.containers}</b>CONTAINERS UP
        </span>
      </div>
    </div>
  );
}
