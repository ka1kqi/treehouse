export type AgentStatus =
  | "running"
  | "pending"
  | "done"
  | "failed"
  | "merging"
  | "merged";

export type LogTag = "read" | "edit" | "bash" | "think" | "indent";

export interface LogLine {
  ts: string;
  tag: LogTag;
  text: string;
}

export interface Port {
  svc: string;
  container: number;
  host: number;
}

export interface Agent {
  id: string;
  name: string;
  branch: string;
  task: string;
  status: AgentStatus;
  portBase: number;
  spawnedAt: number;
  startedAt: number | null;
  endedAt: number | null;
  mergedAt?: number;
  runtime: string;
  tokensIn: number;
  tokensOut: number;
  edits: number;
  files: number;
  ports: Port[];
  log: LogLine[];
}

export interface TrunkCommit {
  at: number;
  sha: string;
  msg: string;
  inProgress?: boolean;
}

// All times measured in minutes from t0.
export const NOW = 180;
export const TIMELINE_END = 200;

export const AGENTS: Agent[] = [
  {
    id: "auth-fix",
    name: "auth-fix",
    branch: "treehouse/auth-fix",
    task:
      "Fix the OAuth redirect loop when SAML is enabled — the `state` param is being dropped on the second callback hop.",
    status: "running",
    portBase: 3101,
    spawnedAt: 142,
    startedAt: 144,
    endedAt: null,
    runtime: "38m",
    tokensIn: 18420,
    tokensOut: 4612,
    edits: 7,
    files: 4,
    ports: [
      { svc: "web", container: 3000, host: 3101 },
      { svc: "api", container: 8000, host: 8101 },
      { svc: "db", container: 5432, host: 5501 },
      { svc: "redis", container: 6379, host: 6401 },
    ],
    log: [
      { ts: "14:02:11", tag: "read", text: "src/auth/oauth/callback.ts" },
      { ts: "14:02:14", tag: "read", text: "src/auth/saml/state.ts" },
      {
        ts: "14:02:22",
        tag: "think",
        text: "the state param is regenerated on the SAML hop; we lose the original nonce",
      },
      { ts: "14:03:03", tag: "edit", text: "src/auth/oauth/callback.ts" },
      { ts: "14:03:03", tag: "indent", text: "preserve original state through SAML round-trip" },
      { ts: "14:04:18", tag: "bash", text: "pnpm test auth/oauth" },
      { ts: "14:04:41", tag: "indent", text: "✓ 14 passed (1 skipped)" },
      { ts: "14:05:02", tag: "edit", text: "src/auth/saml/state.ts" },
      { ts: "14:05:02", tag: "indent", text: "thread original_state through buildSAMLRequest" },
      { ts: "14:06:10", tag: "bash", text: "pnpm test auth" },
    ],
  },
  {
    id: "billing-export",
    name: "billing-export",
    branch: "treehouse/billing-export",
    task: "Add CSV export to the billing dashboard, gated behind feature flag `billing.csv_export`.",
    status: "done",
    portBase: 3103,
    spawnedAt: 60,
    startedAt: 62,
    endedAt: 142,
    runtime: "1h 20m",
    tokensIn: 24302,
    tokensOut: 7910,
    edits: 9,
    files: 5,
    ports: [
      { svc: "web", container: 3000, host: 3103 },
      { svc: "api", container: 8000, host: 8103 },
      { svc: "db", container: 5432, host: 5503 },
      { svc: "redis", container: 6379, host: 6403 },
    ],
    log: [],
  },
  {
    id: "onboarding-copy",
    name: "onboarding-copy",
    branch: "treehouse/onboarding-copy",
    task: "Rewrite the empty-state copy across the onboarding flow — current strings flagged by content review.",
    status: "merged",
    portBase: 3104,
    spawnedAt: 20,
    startedAt: 22,
    endedAt: 70,
    mergedAt: 78,
    runtime: "48m",
    tokensIn: 8920,
    tokensOut: 3104,
    edits: 4,
    files: 3,
    ports: [{ svc: "web", container: 3000, host: 3104 }],
    log: [],
  },
  {
    id: "webhook-retry",
    name: "webhook-retry",
    branch: "treehouse/webhook-retry",
    task: "Implement exponential backoff on webhook delivery failures. Cap at 24h, jitter ±10%.",
    status: "merging",
    portBase: 3105,
    spawnedAt: 80,
    startedAt: 82,
    endedAt: 168,
    runtime: "1h 26m",
    tokensIn: 31204,
    tokensOut: 8821,
    edits: 11,
    files: 6,
    ports: [
      { svc: "api", container: 8000, host: 8105 },
      { svc: "db", container: 5432, host: 5505 },
      { svc: "redis", container: 6379, host: 6405 },
    ],
    log: [],
  },
  {
    id: "stale-sessions",
    name: "stale-sessions",
    branch: "treehouse/stale-sessions",
    task: "Garbage-collect sessions older than 30d from Redis on a nightly cron.",
    status: "failed",
    portBase: 3106,
    spawnedAt: 90,
    startedAt: 92,
    endedAt: 138,
    runtime: "46m",
    tokensIn: 14210,
    tokensOut: 3920,
    edits: 5,
    files: 3,
    ports: [
      { svc: "api", container: 8000, host: 8106 },
      { svc: "redis", container: 6379, host: 6406 },
    ],
    log: [],
  },
  {
    id: "cache-warmer",
    name: "cache-warmer",
    branch: "treehouse/cache-warmer",
    task: "Pre-warm the Redis tenant cache on cold deploys so the first request after rollout isn't 4s.",
    status: "running",
    portBase: 3102,
    spawnedAt: 142,
    startedAt: 143,
    endedAt: null,
    runtime: "38m",
    tokensIn: 9840,
    tokensOut: 2614,
    edits: 3,
    files: 2,
    ports: [
      { svc: "api", container: 8000, host: 8102 },
      { svc: "redis", container: 6379, host: 6402 },
    ],
    log: [],
  },
  {
    id: "index-rebuild",
    name: "index-rebuild",
    branch: "treehouse/index-rebuild",
    task: "Rebuild the search index with the new analyzer config; backfill from the last snapshot.",
    status: "done",
    portBase: 3107,
    spawnedAt: 80,
    startedAt: 82,
    endedAt: 156,
    runtime: "1h 16m",
    tokensIn: 22140,
    tokensOut: 6082,
    edits: 6,
    files: 4,
    ports: [
      { svc: "api", container: 8000, host: 8107 },
      { svc: "db", container: 5432, host: 5507 },
    ],
    log: [],
  },
  {
    id: "ui-polish",
    name: "ui-polish",
    branch: "treehouse/ui-polish",
    task: "Tighten spacing on settings pages; align with new tokens.",
    status: "pending",
    portBase: 3108,
    spawnedAt: 178,
    startedAt: null,
    endedAt: null,
    runtime: "—",
    tokensIn: 0,
    tokensOut: 0,
    edits: 0,
    files: 0,
    ports: [{ svc: "web", container: 3000, host: 3108 }],
    log: [],
  },
];

export const TRUNK_COMMITS: TrunkCommit[] = [
  { at: 4, sha: "a550971", msg: "fix: dashboard spawn uses persisted state" },
  { at: 38, sha: "145ef52", msg: "feat: persist workspaces across CLI invocations" },
  { at: 78, sha: "4c9e012", msg: "merge: onboarding-copy" },
  { at: 124, sha: "8a31bd4", msg: "chore: bump deps" },
  { at: 168, sha: "—", msg: "merge: webhook-retry (in progress)", inProgress: true },
];
