# Treehouse — Web Dashboard

## What it is

The `web/` directory is a **Next.js 15 dashboard** that visualises Treehouse workspaces as a forest: `main` is the trunk, each agent is a branch growing off it, and leaves at the branch tips signal status. It is the browser counterpart to the Textual TUI shipped with the Python CLI — same domain model (workspaces, statuses, ports, log lines), different presentation.

The current build is **mock-data only**. Everything renders from `lib/mockData.ts`; nothing is wired to the FastAPI server in `treehouse/server/api.py` yet. The UI, interactions, and visual language are complete; the data layer is the next integration point.

## Tech Stack

- **Framework:** Next.js 15.5 (App Router) + React 18.3
- **Language:** TypeScript 5.5 (strict)
- **Styling:** A single hand-written `globals.css` (~870 lines) using CSS custom properties for theming. No CSS-in-JS, no utility framework, no component library.
- **Fonts:** Cormorant Garamond (serif), Inter Tight (sans), JetBrains Mono (mono) — loaded from Google Fonts in `app/layout.tsx:14-19`
- **Icons / glyphs:** All inline SVG, hand-authored
- **State:** Local React state only (`useState`, `useEffect`, `useMemo`). No Redux, Zustand, or React Query.
- **Dependencies:** just `next`, `react`, `react-dom` — see `web/package.json:11-15`

## Layout

```
web/
├── package.json           # next 15.5.15, react 18.3.1
├── next.config.js         # reactStrictMode only
├── tsconfig.json
├── app/
│   ├── layout.tsx         # Root <html>, fonts, dark theme default
│   ├── page.tsx           # The whole dashboard — single client component
│   ├── globals.css        # Design tokens, light/dark theme, every component style
│   └── components/
│       ├── TopBar.tsx          # Branding, repo crumbs, keyboard hints, spawn CTA
│       ├── ForestLegend.tsx    # Aggregate stats row (RUNNING/DONE/MERGING/...)
│       ├── ForestTimeline.tsx  # The hero: SVG trunk + branches + leaves
│       ├── AgentTable.tsx      # Branches table below the forest
│       ├── DetailPanel.tsx     # Right-hand drawer for the selected agent
│       ├── SpawnModal.tsx      # "+ Spawn agent" dialog
│       ├── MergeModal.tsx      # "graft → main" dialog with conflict resolution UI
│       ├── StatusPill.tsx      # Coloured status chip
│       ├── LeafIcon.tsx        # Reusable leaf SVG
│       ├── BranchGlyph.tsx     # Reusable branch-graph SVG
│       └── ThemeToggle.tsx     # Sun / moon switch
└── lib/
    └── mockData.ts        # AGENTS, TRUNK_COMMITS, NOW, TIMELINE_END, types
```

## Domain model

Defined in `web/lib/mockData.ts:1-48`. Mirrors the Python `AgentWorkspace` dataclass (`treehouse/core/models.py`) — six statuses (`running | pending | done | failed | merging | merged`), per-agent port allocations, token/edit counters, and a stream-json log feed.

```ts
interface Agent {
  id: string; name: string; branch: string; task: string;
  status: AgentStatus;
  portBase: number;
  spawnedAt: number; startedAt: number | null; endedAt: number | null;
  mergedAt?: number;
  runtime: string;
  tokensIn: number; tokensOut: number;
  edits: number; files: number;
  ports: { svc: string; container: number; host: number }[];
  log: { ts: string; tag: LogTag; text: string }[];
}
```

Times are tracked as **minutes from t0**, not Date objects — the timeline in the mock spans 0 to 200 minutes, with `NOW = 180`.

## The page

`app/page.tsx` is a single `"use client"` component that owns all top-level state:

| State | Purpose |
|---|---|
| `activeId` | Which agent the right-hand `DetailPanel` is showing |
| `agents` | Currently `AGENTS` from `mockData`; will become server-fed |
| `spawnOpen` / `mergeFor` | Modal visibility |
| `theme` | `"dark" \| "light"`, persisted to `localStorage` under `treehouse-theme` |

Global keyboard shortcuts (`page.tsx:65-78`):

- `S` → open SpawnModal
- `M` → open MergeModal for active agent
- `Esc` → close any modal

Aggregate stats for `ForestLegend` are recomputed via `useMemo` over `agents` (`page.tsx:44-63`).

## The forest visualisation

`ForestTimeline.tsx` is the centrepiece — ~470 lines of hand-rolled SVG. Worth understanding because the rest of the UI hangs off it.

**Geometry.** Constants at the top of the file fix the layout:

```ts
const ROW_H = 44;         // vertical spacing between branches
const TRUNK_PAD_TOP = 60;
const TRUNK_PAD_BOTTOM = 70;
const LEFT_GUTTER = 230;  // space reserved for branch name labels
const RIGHT_PAD = 60;
const TIMELINE_PX = 1080; // logical width of the time axis
```

`timeToX(t, totalMins)` maps a time-in-minutes to an x-coordinate inside the SVG viewBox.

**Lane assignment.** Agents are sorted by `spawnedAt`, then alternated above/below the trunk (`i % 2 === 0` → above), with each successive pair pushed one row further out. See `ForestTimeline.tsx:116-124`. This produces the symmetric "branches sprouting up and down from a horizontal trunk" effect.

**Branch path.** Each branch is a single SVG path that:
1. starts at `(spawnedAt, TRUNK_Y)` on the trunk,
2. curves outward (cubic Bézier) to the agent's lane,
3. runs horizontally to `endedAt` (or to `now` if still running),
4. and — if `mergedAt` is set — curves back into the trunk.

`branchPath()` at `ForestTimeline.tsx:133-155` constructs this `d` string. Pending branches get a dashed `strokeDasharray`.

**Tip glyphs.** Drawn by the `Tip` component (`ForestTimeline.tsx:157-225`):

- `running` / `pending` → animated leaf cluster (three overlapping leaf paths). Running leaves get a pulsing aura via `<animate>`.
- `done` → solid filled circle with a subtle highlight dot
- `failed` → dashed leaf outline plus an X
- `merging` → pulsing ring around a filled centre
- `merged` → no tip (the branch has rejoined the trunk)

The active agent's tip scales 1.25× (`isActive` prop on `LeafCluster`).

**Trunk.** Two trapezoid paths (one shadow, one gradient) plus a `<pattern>`-filled overlay for bark texture (`ForestTimeline.tsx:307-319`). Trunk commits are little ellipse "knots" with the SHA labelled above (`:345-370`); an in-progress commit gets the same pulsing animation as a merging tip.

**The "NOW" line.** Vertical dashed marker at `timeToX(now, ...)` with a `NOW` letterspaced label at the bottom (`ForestTimeline.tsx:285-305`).

Everything shares the colour tokens from `globals.css` so light / dark themes recolour the forest without touching the SVG.

## Other components

- **`TopBar`** (`TopBar.tsx`) — brand mark (a custom multi-leaf SVG), repo breadcrumb (`linear-app / monorepo` placeholder), keyboard-shortcut hints, theme toggle, and the primary "+ Spawn agent" button.
- **`ForestLegend`** (`ForestLegend.tsx`) — two rows of label/number stats: status counts and resource totals (TOKENS / EDITS / CONTAINERS UP).
- **`AgentTable`** (`AgentTable.tsx`) — sortable-looking table with columns Branch / Task / Status / Runtime / Ports. Clicking a row sets `activeId`. Status leaf colour is mapped via the `LEAF_COLOR` record (`AgentTable.tsx:13-20`).
- **`DetailPanel`** (`DetailPanel.tsx`) — right column, ~390px wide. Shows branch name, task description, runtime / edits / files meta row, two stat cards (tokens in/out), `compose` project name, worktree path, **port allocation table** (svc / container port / host port), a "stream-json · live" log viewer, and contextual action buttons (`Merge to main`, `Pause`, `Retry`, `Open shell`, `Destroy`) — which buttons appear depends on status.
- **`SpawnModal`** (`SpawnModal.tsx`) — fields: branch name (sanitised to `[a-z0-9-]`), task textarea (verbatim payload to `claude --print`), service toggles (`web | api | db | redis`), and a live "Isolation preview" card showing the resulting branch / worktree / compose-project / port map. Port mapping logic at `SpawnModal.tsx:38-42` mirrors `treehouse/core/ports.py`.
- **`MergeModal`** (`MergeModal.tsx`) — three-pane "FROM → flow arrow → INTO" layout, plus a conflict list. Has a four-phase state machine (`review → merging → conflicts → done`) driven by `setTimeout` to demo the AI-resolution UX. Animation timings: 900ms to enter `conflicts`, another 1500ms to `done` (`MergeModal.tsx:178-181`).
- **`StatusPill`**, **`LeafIcon`**, **`BranchGlyph`**, **`ThemeToggle`** — small, single-purpose visual atoms.

## Theming

Two themes implemented purely via CSS custom properties on `:root` and `.theme-light` (`globals.css:5-92`):

- **Dark (default)** — "deep forest at dusk". Backgrounds in the `#10130f` → `#252b20` range; greens from `--moss-deep` through `--leaf-light` to `--sage`; warm parchment text (`--bone`, `--parchment`).
- **Light** — "sunlit clearing / parchment". Cream backgrounds (`#f0eadb`+), darker greens, dark text.

Status tokens (`--st-running`, `--st-failed`, etc.) are theme-aware aliases of the palette tokens, which is why every coloured element in the SVG respects the toggle without per-component logic.

The toggle (`ThemeToggle.tsx`) flips a `theme-light` class on `<body>` and a `data-theme` attribute on `<html>`. State is restored from `localStorage` on mount (`page.tsx:23-28`) — note the deliberate use of `useEffect` rather than reading during render to avoid SSR hydration mismatches.

## Running it

### Prerequisites

- **Node.js 18.18+** (Next.js 15 requires it; 20 LTS recommended)
- **npm** (the repo ships a `package-lock.json`, so `npm` is the canonical package manager here — pnpm/yarn will work but will produce a second lockfile)
- No backend, database, or Docker is needed — the dashboard runs entirely off `lib/mockData.ts`

### First time

```bash
cd web
npm install         # installs next, react, react-dom and types
```

`web/node_modules/` is already present in the working tree from a prior install, so this step is only required after a fresh clone or when `package.json` changes.

### Day-to-day

All scripts live in `web/package.json:5-10`:

```bash
npm run dev         # next dev -p 3000   — hot-reloading dev server
npm run build       # next build         — production bundle into .next/
npm run start       # next start -p 3000 — serves the production build
npm run lint        # next lint
```

Then open <http://localhost:3000>. The page renders immediately — nothing async, no loading state, because the data is hard-coded.

### Port

The dev and prod servers are pinned to **port 3000** in the npm scripts. If 3000 is in use (note that Treehouse agents themselves often grab `:3101`, `:3102`, …), override it inline:

```bash
npx next dev -p 3030
```

Don't pick a port in the `:31xx` range — that's where spawned agents map their own `web` services and you'll collide.

### Trying the UI

Mock state lives in `web/lib/mockData.ts`. Eight agents are pre-seeded, one of every status, plus five trunk commits. Once the page is up:

- **`S`** — open the Spawn modal (also via the `+ Spawn agent` button top-right). Submit is wired to a no-op (`page.tsx:148`); the modal closes but no agent is added.
- **`M`** — open the Merge modal for the currently selected branch (only fires when an agent is selected). The merge sequence is demo-only — `setTimeout` chains `review → merging → conflicts → done` (`MergeModal.tsx:178-181`).
- **`Esc`** — dismiss either modal.
- **Click any branch, leaf, or table row** to select an agent and update the right-hand `DetailPanel`.
- **Sun/moon toggle** in the top bar switches dark ↔ light. The choice is persisted to `localStorage` under `treehouse-theme` and survives reloads.

### Hooking into the rest of Treehouse

The Python CLI defines a `treehouse web` command (see `Overview.md` and `pyproject.toml`), but it does **not** yet build, serve, or even spawn this Next.js app — and the React tree has no fetch calls into `treehouse/server/api.py` (`/agents`, `/ws`). Until that integration lands, run the dashboard standalone with `npm run dev` and treat it as a visual prototype.

### Production build sanity check

```bash
cd web
npm run build && npm run start
```

This validates that the codebase type-checks under `next build` (Next runs `tsc` as part of the build) and that the static prerender works for `app/page.tsx` despite it being a client component. Useful to run before any PR that touches `web/`.

### Common gotchas

- **Hydration warnings on first load** — the theme is read from `localStorage` inside `useEffect` precisely to avoid this; don't move that read into the render body (`page.tsx:23-28`).
- **`viewport: width=1440`** is hard-coded in `app/layout.tsx:13`. The layout assumes desktop widths and will look cramped below ~1280px. Mobile is out of scope.
- **Google Fonts** are loaded over the network at request time (`layout.tsx:14-19`). Offline development will fall back to the system serif/sans/mono in the `var(--serif/--sans/--mono)` stacks — the page still renders, just with different typography.

## What's next

Concretely, to make this real:

1. **Replace `lib/mockData.ts`** with a small fetch + WebSocket client that calls `/agents` once and subscribes to `/ws` for streamed log lines and status transitions. The shapes already line up with the FastAPI response model.
2. **Wire `SpawnModal`'s `onSpawn`** (currently a `() => {}` no-op at `page.tsx:148`) to a `POST /agents` endpoint.
3. **Wire the `MergeModal`** "Run merge" button to the merge endpoint and stream phase transitions instead of the current `setTimeout` demo.
4. **Move time math from "minutes since t0" to absolute timestamps** so the timeline can scroll / re-anchor as new commits land.
5. **Decide whether `treehouse web` should serve the built Next.js app** (export + static-serve from FastAPI) or just open the user's browser at a separately-running `next dev`.
