# Treehouse — Design Document

Parallel runtime isolation for multi-agent coding.

## Problem

Multiple AI agents working on the same repo collide on ports, databases, env files, build artifacts, and git state. The bottleneck for multi-agent coding is environment isolation, not code generation.

## Solution

A Python CLI with both a TUI dashboard (Textual) and a web dashboard (Next.js via v0). Spawns fully isolated workspaces per agent: git worktree + Docker Compose project + rewritten `.env`. Launches Claude Code sessions, monitors progress in real-time, and merges results back with AI-assisted conflict resolution.

## Architecture

Layered architecture. Python core handles all system operations. A FastAPI WebSocket server exposes state to external clients. Two dashboard frontends sit on top: Textual TUI (in-process) and Next.js web dashboard (separate process, built with v0).

```
┌─────────────────────────────────┐
│  Next.js Dashboard (v0)         │  ← Web UI on :3000, connects via WebSocket
├─────────────────────────────────┤
│  Textual TUI                    │  ← Terminal UI, reads state directly
├─────────────────────────────────┤
│  FastAPI WebSocket Server       │  ← API on :8080, broadcasts state changes
├─────────────────────────────────┤
│  Python Core                    │  ← git, docker, agent management
└─────────────────────────────────┘
```

```
treehouse/
  pyproject.toml
  treehouse/
    __init__.py
    cli.py              # Typer CLI entry point
    config.py           # .treehouse/config.yml management
    core/
      __init__.py
      models.py         # AgentWorkspace dataclass + AgentStatus enum
      worktree.py       # git worktree create/destroy
      docker.py         # Compose project generation + lifecycle
      env.py            # .env rewriting with port allocation
      agent.py          # Claude Code subprocess management
      merger.py         # Sequential merge + AI conflict resolution
      ports.py          # Port allocation tracker
    server/
      __init__.py
      api.py            # FastAPI app with WebSocket endpoint
      state.py          # Shared state manager (bridge between core and clients)
    tui/
      __init__.py
      app.py            # Textual app main
      agent_table.py    # Top panel widget
      log_viewer.py     # Middle panel widget
      dialogs.py        # Spawn dialog, merge confirmation
  web/                  # Next.js dashboard (built with v0)
    package.json
    app/
      page.tsx          # Main dashboard page
      components/
        agent-table.tsx
        log-viewer.tsx
        spawn-dialog.tsx
```

Dependencies: `typer`, `textual`, `pyyaml`, `fastapi`, `uvicorn`, `websockets`.

## Data Model

```python
class AgentStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    MERGING = "merging"
    MERGED = "merged"

@dataclass
class AgentWorkspace:
    name: str                  # "auth-fix"
    branch: str                # "treehouse/auth-fix"
    worktree_path: Path        # .treehouse/worktrees/auth-fix/
    port_base: int             # 3101 (allocated automatically)
    compose_project: str       # "treehouse_auth_fix"
    status: AgentStatus
    task_prompt: str
    process: Process | None
    log_buffer: deque[str]
```

## Runtime Isolation

Each agent gets its own Docker Compose project with fully isolated containers. Port mapping exposes containers to the host without collisions:

```yaml
# .treehouse/worktrees/auth-fix/docker-compose.treehouse.yml
services:
  app:
    ports: ["3101:3000"]    # host:container
  postgres:
    ports: ["5501:5432"]
  redis:
    ports: ["6401:6379"]
```

Inside containers, everything uses default ports. Isolation comes from separate Compose project names (`treehouse_auth_fix`), giving each agent its own containers, networks, and volumes.

Port allocation: base 3100, each agent gets `3100 + n`. Multi-port projects get offset blocks:

```
agent-1: app=3101, db=5501, redis=6401
agent-2: app=3102, db=5502, redis=6402
```

## Agent Lifecycle

1. **Spawn** — `git worktree add`, generate Compose file, rewrite `.env`, `docker compose up -d`, launch Claude Code subprocess with task prompt
2. **Run** — Capture stdout/stderr into rolling log buffer, parse for status signals
3. **Monitor** — Dashboard polls subprocess + git log + docker status
4. **Complete** — Claude Code exits, status flips to `done`, Docker services stay running for inspection
5. **Merge** — User triggers merge from dashboard or CLI

## CLI Interface

```
treehouse init                              # Initialize in current repo
treehouse spawn <name> "<task>"             # Create workspace + launch agent
treehouse list                              # List all agents and status
treehouse logs <name>                       # Tail an agent's output
treehouse stop <name>                       # Stop an agent
treehouse merge <name>                      # Merge agent's branch back
treehouse destroy <name>                    # Tear down workspace + containers
treehouse dashboard                         # Launch the TUI
treehouse server                            # Start the WebSocket API on :8080
treehouse web                               # Start Next.js dashboard on :3000
```

`treehouse init` detects the project's `docker-compose.yml` and stores config in `.treehouse/config.yml`:

```yaml
base_port: 3100
compose_file: docker-compose.yml
env_file: .env
```

## WebSocket API

FastAPI server on port 8080. Bridges the Python core to external clients (the Next.js dashboard).

**WebSocket endpoint:** `ws://localhost:8080/ws`

**Server → Client messages:**
```json
{"type": "state", "agents": [{"name": "auth-fix", "branch": "treehouse/auth-fix", "port_base": 3101, "status": "running", "last_log": "editing src/auth.py"}]}
{"type": "log", "agent": "auth-fix", "line": "[Edit] src/auth.py:42"}
{"type": "status_change", "agent": "auth-fix", "status": "done"}
```

**Client → Server messages:**
```json
{"type": "spawn", "name": "auth-fix", "task": "fix the login bug"}
{"type": "stop", "name": "auth-fix"}
{"type": "merge", "name": "auth-fix"}
{"type": "destroy", "name": "auth-fix"}
```

The server broadcasts state updates at 1Hz and pushes log lines as they arrive. The TUI reads the same in-memory state directly (no WebSocket needed).

## TUI Dashboard

Built with Textual. Three panels:

- **Top:** Agent table — name, branch, ports, status, last activity. Arrow keys to select.
- **Middle:** Live streaming logs for the selected agent.
- **Bottom:** Keyboard shortcuts — [s]pawn, [m]erge, [k]ill, [d]estroy, [q]uit.

## Web Dashboard

Built with Next.js and v0. Connects to the FastAPI WebSocket server. Same information as the TUI but in a browser:

- Agent table with status badges and port info
- Live log viewer with auto-scroll
- Spawn dialog with name + task inputs
- Merge button with diff preview
- Responsive layout for large screens

## Merge Flow

1. **Pre-check** — `git diff main...treehouse/auth-fix --stat`
2. **Attempt merge** — `git merge --no-commit treehouse/auth-fix`
3. **If clean** — auto-commit, mark merged, tear down workspace
4. **If conflicts** — spawn a merge Claude Code session with context about the original task and both sides of the conflict
5. **Sequential** — merges happen one at a time against updated main to avoid compound conflicts

The merge agent appears as a special row in the dashboard with status `merging`.

## Scope (24-hour hackathon)

- Layered architecture: Python core + FastAPI WebSocket + TUI + Next.js web dashboard
- Claude Code only (no Cursor/Codex support)
- Core happy path: spawn, monitor, merge
- No persistence across CLI restarts
- Web dashboard built with v0 for polished UI
