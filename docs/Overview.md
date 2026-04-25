# Treehouse — Project Overview

## What it is

Treehouse is a Python CLI + TUI for **parallel runtime isolation of AI coding agents**. It lets multiple Claude Code sessions work on the same repository simultaneously without colliding on git state, Docker containers, ports, databases, or `.env` files. Each agent gets its own fully isolated workspace; results are merged back to `main` with AI-assisted conflict resolution.

The premise: the bottleneck for multi-agent coding is environment isolation, not code generation.

## Tech Stack

- **Language:** Python 3.12+
- **Build:** Hatchling, distributed as the `treehouse` console script
- **CLI:** Typer
- **TUI:** Textual
- **API:** FastAPI + Uvicorn (WebSocket)
- **Config:** PyYAML
- **Web dashboard (planned):** Next.js + React, served from `web/` (not yet present in the repo, but a `treehouse web` command exists)

Dependencies declared in `pyproject.toml:10-17`.

## Repository Layout

```
treehouse/
├── pyproject.toml             # Hatchling build, treehouse CLI entry
├── README.md
├── LICENSE
├── docs/plans/                # Original design + 17-task implementation plan + use cases
│   ├── 2026-04-24-treehouse-design.md
│   ├── 2026-04-24-treehouse-implementation.md
│   └── 2026-04-24-treehouse-usecases.md
├── treehouse/                 # Python package
│   ├── __init__.py            # __version__ = "0.1.0"
│   ├── cli.py                 # Typer CLI: init / spawn / list / merge / stop / destroy / dashboard / server / web
│   ├── config.py              # .treehouse/config.yml + workspaces.yml load/save
│   ├── core/
│   │   ├── models.py          # AgentStatus enum, AgentWorkspace dataclass
│   │   ├── ports.py           # PortAllocator with range-aware mapping
│   │   ├── worktree.py        # WorktreeManager (git worktree create/destroy/list)
│   │   ├── docker.py          # DockerManager (compose generation + up/down)
│   │   ├── env.py             # rewrite_env (port-substitution into .env)
│   │   ├── agent.py           # AgentRunner (Claude Code subprocess, stream-json parse)
│   │   └── merger.py          # MergeManager + MergeResult + ai_resolve()
│   ├── server/
│   │   ├── state.py           # StateManager (in-memory workspaces + log/status callbacks)
│   │   └── api.py             # FastAPI app, /health, /agents, /ws WebSocket
│   └── tui/
│       ├── app.py             # TreehouseApp (Textual)
│       ├── agent_table.py     # DataTable widget
│       ├── log_viewer.py      # RichLog widget
│       └── dialogs.py         # SpawnDialog modal
└── tests/                     # pytest suite covering each core module + integration
    ├── test_models.py / test_ports.py / test_worktree.py
    ├── test_docker.py / test_env.py / test_agent.py
    ├── test_merger.py / test_config.py / test_state.py
    ├── test_api.py
    └── test_integration.py
```

## Architecture

A four-layer stack. The Python core does all real work; everything else is a presentation surface.

```
┌─────────────────────────────────┐
│  Next.js Dashboard (planned)    │  WebSocket client on :3000
├─────────────────────────────────┤
│  Textual TUI                    │  Reads in-memory workspaces directly
├─────────────────────────────────┤
│  FastAPI WebSocket Server       │  /ws on :8080, broadcasts state at 1Hz
├─────────────────────────────────┤
│  Python Core                    │  git worktree, docker compose, agent subprocess
└─────────────────────────────────┘
```

State lives in two places:
- **In-process:** `dict[str, AgentWorkspace]`, mutated by core operations.
- **On disk:** `.treehouse/config.yml` (project config) and `.treehouse/workspaces.yml` (persisted workspace records, written via `TreehouseConfig.save_workspaces`). The persistence step is what lets the CLI survive across invocations — `cli.py:_load_workspaces / _save_workspaces`.

Note: `AgentWorkspace.process` and `log_buffer` are in-memory only; only durable fields (name, branch, ports, status, etc.) are serialized via `to_dict` / `from_dict` (`treehouse/core/models.py:40-62`).

## Data Model (`treehouse/core/models.py`)

```python
class AgentStatus(Enum):
    PENDING, RUNNING, DONE, FAILED, MERGING, MERGED

@dataclass
class AgentWorkspace:
    name: str                          # e.g. "auth-fix"
    task_prompt: str
    worktree_path: Path                # .treehouse/worktrees/<name>/
    port_base: int                     # e.g. 3101
    branch: str = "treehouse/<name>"   # auto-derived
    compose_project: str = "treehouse_<name_with_underscores>"
    status: AgentStatus = PENDING
    process: asyncio.subprocess.Process | None
    log_buffer: deque[str]             # maxlen 500
```

## Core Subsystems

### Port allocation (`core/ports.py`)
`PortAllocator(base_port=3100)` hands out sequential `port_base` integers starting at `3101`, with release/reuse via `_released`. `get_port_mapping(port_base, services)` produces `{service: {host, container}}` using range-keyed bases:

| Container port range | Host base |
|----------------------|-----------|
| 3000–3999 (web)      | 3100      |
| 5000–5999 (db)       | 5500      |
| 6000–6999 (redis)    | 6400      |
| 8000–8999 (api)      | 8100      |

So agent #1 (offset 1) gets `3101` / `5501` / `6401` / `8101`, agent #2 gets `3102` / `5502` / etc. — each agent gets a non-overlapping block across all common service ports.

### Git worktrees (`core/worktree.py`)
`WorktreeManager` runs `git worktree add <.treehouse/worktrees/{name}> -b treehouse/{name}` to create, and `worktree remove --force` + `branch -D` to destroy.

### Docker (`core/docker.py`)
`DockerManager.generate(...)` reads the project's source `docker-compose.yml`, rewrites `ports:` for each known service to `host:container`, and writes `<worktree>/docker-compose.treehouse.yml`. `start` / `stop` invoke `docker compose -f <file> -p <project> up -d` / `down -v`. Isolation comes from the unique `-p treehouse_<name>` project name (separate networks, volumes, container names).

### Env rewriting (`core/env.py`)
`rewrite_env(source, output, port_mapping)` replaces standalone occurrences of each container port with its host port (regex `(?<!\d)PORT(?!\d)` — won't match inside longer numbers). If no source `.env` exists, writes a minimal `PORT=<host>`.

### Agent runner (`core/agent.py`)
`AgentRunner.start(workspace)` launches `claude --print --output-format stream-json --dangerously-skip-permissions --add-dir <worktree> "<task>"` as an asyncio subprocess. `stream_output` reads stdout line-by-line, parses each line as stream-json (or falls back to plain text), and appends a one-line summary to `workspace.log_buffer`. Tool-use lines render as `[Edit] ...` / `  -> ...`. `wait` flips status to `DONE`/`FAILED` based on returncode.

### Merger (`core/merger.py`)
`MergeManager.merge(branch)` runs `git merge --no-edit`. On conflict (`UU ` / `AA ` in `git status --porcelain`), `ai_resolve(name, task_prompt)` shells out to `claude --print --dangerously-skip-permissions` with a prompt naming the conflicted files and the original task; on success it `git add . && git commit -m "merge: resolve conflicts for treehouse/<name>"`. Conflict-merge failures call `abort_merge`.

### State + WebSocket (`server/state.py`, `server/api.py`)
`StateManager` holds the workspace dict and exposes `push_log` / `set_status` / `snapshot()` (JSON). The FastAPI app at `server/api.py:create_app`:

- `GET /health` → `{"status": "ok"}`
- `GET /agents` → JSON snapshot
- `WebSocket /ws` → on connect sends initial state, then receives `{type: spawn|stop|merge}` commands (currently only acks them — actual mutations stay in CLI/TUI), and broadcasts state at 1Hz on a startup background task.

CORS is wide open (`allow_origins=["*"]`) — fine for local dev, would need narrowing for any deployment.

### TUI (`tui/app.py`)
`TreehouseApp` is a Textual app with two panels: `AgentTable` (top, 40%) and `LogViewer` (bottom, 55%), refreshed every 1s. Keybindings: `s`=spawn, `m`=merge, `k`=kill, `d`=destroy, `q`=quit. `s` opens a `SpawnDialog` modal; on submit it creates a worktree + env, spawns the Claude subprocess via `run_worker`, and persists state with `_save()`. `action_merge` currently only notifies (no actual merge wired through the TUI yet).

## CLI Surface (`treehouse/cli.py`)

| Command | Effect |
|---------|--------|
| `treehouse init` | Creates `.treehouse/config.yml`, auto-detects `docker-compose.{yml,yaml}` / `compose.{yml,yaml}` |
| `treehouse spawn <name> "<task>"` | git worktree + (optional) docker compose up + .env rewrite + saves workspace state. Note: this command currently does **not** start the Claude subprocess — only the TUI's spawn flow does that. |
| `treehouse list` | Prints `name  branch  port:N  [status]` for every persisted workspace |
| `treehouse merge <name>` | `git diff` stat → `git merge --no-edit` → AI conflict resolution if needed |
| `treehouse stop <name>` | Marks workspace `FAILED` and persists (no process kill since process handles aren't persisted) |
| `treehouse destroy <name>` | `docker compose down -v` (if compose was used) + `git worktree remove --force` + branch delete + state save |
| `treehouse dashboard` | Launches the Textual TUI |
| `treehouse server [--port 8080]` | Runs the FastAPI WebSocket server |
| `treehouse web` | Runs `npm run dev` in `web/` (directory not present yet — would need to be created) |

A subtle bit in `_get_allocator`: it fast-forwards the allocator's internal counter past the highest persisted `port_base` so newly spawned agents don't reuse ports across CLI invocations (`cli.py:36-42`).

## Agent Lifecycle

1. **Spawn** — create branch + worktree, allocate port block, generate isolated compose file, `docker compose up -d`, rewrite `.env`, persist workspace, launch `claude` subprocess (TUI path) with the task prompt.
2. **Run** — subprocess emits `stream-json`; lines are parsed into log buffer entries.
3. **Monitor** — TUI / WebSocket clients poll the workspace dict at 1Hz.
4. **Complete** — claude exits 0 → `DONE`, non-zero → `FAILED`. Containers stay up for inspection.
5. **Merge** — sequential against an updated `main`; AI fallback on conflicts; status flips to `MERGED` on success.
6. **Destroy** — tears down containers, removes worktree + branch.

## Testing

`tests/` mirrors the package one-to-one and follows a strict TDD shape inherited from the implementation plan. Each test file targets a single module:

- Unit tests for `models`, `ports`, `worktree`, `docker`, `env`, `agent`, `merger`, `config`, `state` — they create real git repos / temp files via `tmp_path` rather than mocking.
- `test_api.py` uses `fastapi.testclient.TestClient` for HTTP + WebSocket checks.
- `test_integration.py` exercises the full spawn cycle (worktree → port → env rewrite → destroy) and a 5-agent no-collision scenario.

There is no `pytest` configuration block; tests run with the default pytest discovery. No CI is wired up in this repo.

## Known Gaps / Open Items

These are visible from reading the code rather than guesses; useful to know before extending:

- **`treehouse spawn` (CLI) doesn't actually start the agent subprocess** — only the TUI spawn flow runs `AgentRunner`. The CLI just sets up the workspace.
- **`treehouse stop` cannot kill a running process** — the process handle isn't persisted to disk, so cross-invocation termination isn't possible. The command only flips status to `FAILED`.
- **`web/` is referenced but absent** — the `treehouse web` command and the design doc both describe a Next.js dashboard that hasn't been committed yet.
- **`treehouse logs` is documented in the design doc** but not implemented in `cli.py`.
- **Compose service detection is hard-coded to `{"app": 3000}`** in CLI/TUI spawn (`cli.py:79,85`, `app.py:106`). Multi-service projects (db, redis, api) need their service map plumbed through.
- **TUI merge / kill actions are stubs** — `action_merge` and (in the design) `action_destroy_agent` only notify; they don't call `MergeManager` or terminate processes.
- **WebSocket commands are ack-only** — the server doesn't actually spawn/stop/merge in response to client messages; that logic still lives in CLI/TUI only.
- **CORS `allow_origins=["*"]`** — acceptable locally but not for any shared deployment.

## Recent History

```
a550971 fix: dashboard spawn uses persisted state and correct port allocation
145ef52 feat: persist workspace state to disk across CLI invocations
297b223 docs: add README and gitignore
dbeb217 feat: add spawn dialog to TUI
73c0f6b test: add integration tests for full spawn cycle
```

The repo was scaffolded in a single 24-hour push (per the design doc's "Scope" section) and the most recent work has focused on cross-invocation persistence — making the CLI and the TUI agree on the same workspace state.
