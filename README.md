# Treehouse

Parallel runtime isolation for multi-agent coding.

Treehouse spawns fully isolated workspaces for AI coding agents -- each gets its own git worktree, Docker Compose project, database, ports, and environment. A live TUI dashboard monitors all agents and merges results back with AI-assisted conflict resolution.

## Quick Start

```
pip install -e .
export ANTHROPIC_API_KEY=...                # required for container mode on macOS
cd your-project
treehouse init
treehouse orchestrate "add OAuth + tests + update README"   # parallel agents, auto-merge
# or, single agent:
treehouse spawn auth-fix "fix the login bug"
treehouse dashboard
```

Full guide: [docs/USER_MANUAL.md](docs/USER_MANUAL.md). Architecture: [docs/Overview.md](docs/Overview.md).

## Commands

| Command | Description |
|---------|-------------|
| `treehouse init` | Initialize in current repo |
| `treehouse orchestrate "<task>"` | Decompose into subtasks, spawn parallel agents, auto-merge |
| `treehouse spawn <name> "<task>"` | Create workspace + launch a single agent |
| `treehouse list` | List all agents and status |
| `treehouse stop <name>` | Stop a running agent |
| `treehouse merge <name>` | Merge agent's branch back (AI conflict resolution) |
| `treehouse destroy <name>` | Tear down workspace + containers |
| `treehouse dashboard` | Launch the TUI dashboard |

## Architecture

Treehouse is a layered Python package:

- **Core** (`treehouse/core/`) -- git worktree management, Docker Compose orchestration, port allocation, env rewriting, agent process runner, and merge conflict resolution.
- **Config** (`treehouse/config.py`) -- YAML-based project configuration stored in `.treehouse/config.yml`.
- **Server** (`treehouse/server/`) -- FastAPI WebSocket API that exposes real-time agent state to external clients (web dashboard).
- **TUI** (`treehouse/tui/`) -- Textual-based terminal dashboard for monitoring agents, viewing logs, and spawning new tasks.
- **Web** (`web/`) -- Next.js + React browser dashboard that connects to the WebSocket server.

Each spawned agent gets:
- A dedicated git worktree on its own branch (`treehouse/<name>`)
- An isolated Docker Compose project with remapped ports
- A rewritten `.env` file so services bind to unique host ports
- A monitored Claude Code subprocess with streaming log capture
