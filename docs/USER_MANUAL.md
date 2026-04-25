# Treehouse — User Manual

A practical guide to running parallel AI coding agents on one repository.
See `docs/Overview.md` for architecture and design rationale.

---

## What it does

Treehouse is a CLI for **parallel runtime isolation** of Claude Code agents.
You describe a task, it decomposes the task into parallel subtasks via Claude,
and spawns one agent per subtask. Each agent gets its own:

- **Git worktree** on a dedicated `treehouse/<name>` branch
- **Docker container** for the agent process itself (default) so agents can't
  step on the host, each other, or share state
- **Docker Compose project** for the *app stack* the agent is testing
  (Next.js, Postgres, Redis, etc.) on remapped ports so 5 agents can each run
  their own dev server simultaneously without port collisions
- **Rewritten `.env`** with the new port mappings

When all agents finish, Treehouse sequentially merges their branches back into
your current branch. Conflicts route to a dedicated Claude session that has the
original task context. Clean merges land automatically.

---

## Prerequisites

| Requirement | Why |
|---|---|
| **Python ≥ 3.12** | Treehouse runtime |
| **Git** | Worktrees and merges |
| **Docker daemon** | For containerized agents and per-agent app stacks |
| **`claude` CLI** (Claude Code) | Used by the orchestrator to decompose tasks on the host, and by the agents inside their containers |
| **An Anthropic API key OR `claude login` session** | See *Authentication* below |

### macOS — Docker without admin

Docker Desktop's installer needs `sudo`. If you'd rather not give it that, use
Colima (no admin needed):

```bash
brew install colima docker docker-compose
mkdir -p ~/.docker/cli-plugins
ln -sf /opt/homebrew/bin/docker-compose ~/.docker/cli-plugins/docker-compose
colima start
docker info        # confirms daemon is up
```

Restart Colima after reboots: `colima start`.

---

## Installation

```bash
git clone https://github.com/ka1kqi/treehouse
cd treehouse
pip install -e .
treehouse --help
```

---

## Authentication

Treehouse runs `claude` in two places: on your host (the orchestrator's
decompose call) and inside each agent's container.

The host inherits whatever auth your local `claude` CLI already uses. The
container needs its own credential surface.

| Path | Host | Container (Linux) | Container (macOS) |
|---|---|---|---|
| `ANTHROPIC_API_KEY` env | ✅ | ✅ | ✅ **(required)** |
| `claude login` (OAuth) | ✅ | ✅ via mounted `~/.claude.json` | ❌ token is in macOS Keychain, can't bind-mount |

**On macOS, container mode (the default) requires `ANTHROPIC_API_KEY`** because
Claude Code stores OAuth tokens in the system Keychain (`Claude
Code-credentials`), which Treehouse can't transfer into a container. To use
OAuth without an API key on macOS, run with `--host`.

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

On Linux, the OAuth fallback works in either mode — `~/.claude.json` and
`~/.claude/` are bind-mounted into each container automatically when present.

---

## Initialize a project

`treehouse` operates on the current git repository. Run `init` once per repo:

```bash
cd /path/to/your/project
treehouse init
```

That writes `.treehouse/config.yml` (base port, env file, compose file
detection). State for spawned agents lives in `.treehouse/workspaces.yml`.
Worktrees go to `.treehouse/worktrees/<name>/`.

Add `.treehouse/` to your `.gitignore`. Treehouse will also auto-write per-
worktree compose files (`docker-compose.treehouse.yml`) and rewritten `.env`s;
the auto-merge step explicitly excludes those from anything that ends up on
your branches.

---

## The two main workflows

### A. Single agent — `spawn`

Use when you have one well-scoped task and want a single agent on it.

```bash
treehouse spawn fix-auth "Replace session cookies with JWT in /api/login"
```

Treehouse will:
1. Build the agent image if needed (one-time, ~30s)
2. Create worktree at `.treehouse/worktrees/fix-auth/` on branch `treehouse/fix-auth`
3. Allocate a port range (default starting at `:3101`) and rewrite `.env`
4. Bring up `docker-compose.treehouse.yml` (your app + the agent service)
5. Stream the agent's output until it finishes
6. Auto-commit any uncommitted edits (excluding Treehouse-generated files)

When the agent's done, merge it back manually:

```bash
treehouse merge fix-auth
```

Clean merges → marked `merged`. Conflicts → AI conflict resolver runs with the
original task as context; if it succeeds, the merge commit is created and
status is `merged`. If the AI fails, the merge is aborted and the repo stays
clean for you to resolve manually.

### B. Orchestrator — `orchestrate`

Use for high-level work that fans out into independent subtasks.

```bash
treehouse orchestrate "Add OAuth login + integration tests + update README"
```

Treehouse will:
1. Call Claude on your host to decompose the task into 2–5 subtasks
2. Spawn one agent per subtask, all in parallel containers
3. Wait for all of them to finish
4. Sequentially merge each `treehouse/<name>` branch into your current branch
   (with AI conflict resolution as above)

Default flags:
- `--merge` (auto-merge after agents finish; opt out with `--no-merge`)
- `--containerized` (agents run in containers; opt out with `--host`)

```bash
# Spawn parallel agents but stop short of merging
treehouse orchestrate "..." --no-merge

# Run agents on the host (no container; OAuth works without API key)
treehouse orchestrate "..." --host
```

---

## Commands

| Command | What |
|---|---|
| `treehouse init` | One-time setup in the current repo |
| `treehouse spawn <name> "<task>"` | Create an isolated workspace, launch one agent |
| `treehouse orchestrate "<task>"` | Decompose into subtasks, spawn agents in parallel, auto-merge |
| `treehouse list` | Status of all known agents (`pending` / `running` / `done` / `failed` / `merged`) |
| `treehouse merge <name>` | Merge `treehouse/<name>` into the current branch (AI resolves conflicts) |
| `treehouse stop <name>` | Kill a running agent (mark FAILED) |
| `treehouse destroy <name>` | Tear down worktree, branch, containers, state |
| `treehouse dashboard` | Textual TUI with live agent logs |
| `treehouse server [--port 8080]` | FastAPI WebSocket server (used by the web dashboard) |
| `treehouse web` | Next.js web dashboard at http://localhost:3000 |

Per-command help: `treehouse <cmd> --help`.

---

## What ends up where

Spawning `treehouse spawn fix-auth "..."` from `/myproject`:

```
/myproject/
├── .treehouse/
│   ├── config.yml                              # treehouse settings
│   ├── workspaces.yml                          # state for all agents
│   └── worktrees/
│       └── fix-auth/                           # the agent's worktree
│           ├── (full project tree, mounted into container)
│           ├── .env                            # rewritten with new ports
│           └── docker-compose.treehouse.yml    # app + agent services
└── (your project, untouched until you merge)
```

The branch `treehouse/fix-auth` is what carries the agent's commit. After
`treehouse merge fix-auth`, that commit lands on your current branch.

The `.env` and `docker-compose.treehouse.yml` files are Treehouse-generated
boilerplate per worktree and are explicitly excluded from auto-commit, so they
don't ride into your branch on merge.

---

## Behaviors worth knowing

### Auto-commit on agent finish
After an agent exits with status `done`, Treehouse stages and commits any
uncommitted edits in the worktree with a message of `agent(<name>):
<prompt[:72]>`. Without this, the agent's work would never reach the branch
and `merge` would silently no-op.

If the agent didn't change anything except Treehouse-generated files (`.env`,
`docker-compose.treehouse.yml`), no commit is created. If the agent failed,
edits are left uncommitted so you can inspect them.

### Auto-merge after orchestrate
`orchestrate --merge` (default) walks the agents in spawn order and merges
each. Failures stop the loop — if any agent's merge needs manual resolution,
the loop aborts cleanly and prints the command to resolve the rest.

### AI conflict resolution
When `git merge` reports conflicts, Treehouse spawns a dedicated `claude`
session with:
- The original task prompt
- The list of conflicted files
- Instructions to keep the intent of both sides

If Claude exits 0, Treehouse runs `git add . && git commit` to complete the
merge. If it fails, `git merge --abort` runs and the repo stays clean.

### Port allocation
Each agent gets a range of `base_port + offset` per service. Default
`base_port` is 3100 and each agent grabs the next 10 ports
(`3101`, `3111`, …). Configurable in `.treehouse/config.yml`.

---

## Observability

```bash
treehouse list                  # quick status
treehouse dashboard             # live TUI; press 'o' to orchestrate from there
treehouse server                # WebSocket API on :8080
treehouse web                   # Next.js dashboard on :3000 (mock data)
```

Per-agent logs:
```bash
docker compose -f .treehouse/worktrees/<name>/docker-compose.treehouse.yml \
  -p treehouse_<name> logs -f agent
```

The TUI's bottom panel shows the same content live, split between Activity
(tool calls, events) and Output (assistant text).

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Agent failed` immediately, logs say `Not logged in · Please run /login` | macOS OAuth tokens are in Keychain, can't reach the container | `export ANTHROPIC_API_KEY=...` or use `--host` |
| `Agent failed`, logs say `Invalid API key` | API key set but rejected by API | Rotate the key in Anthropic Console; export the new one |
| `--dangerously-skip-permissions cannot be used with root/sudo privileges` | Container running as root | If you see this, the agent service in your compose file is missing `user:` — re-spawn so a fresh compose is generated |
| `treehouse merge` says `Merged cleanly` but nothing landed | Spawn used an older Treehouse without the auto-commit fix | Update; current versions auto-commit on `done`. Verify with `git log --oneline` on the worktree branch |
| `Docker containers failed to start (non-fatal)` then agent runs anyway | Docker daemon isn't running | `colima start` or launch Docker Desktop |
| Port collision with existing service | Another process bound the allocated port | Bump `base_port` in `.treehouse/config.yml` |
| Build error: `failed to build agent image` | First-run image build needed network and didn't have it | Check internet connectivity; `docker build` needs `npm install` to reach the npm registry |

---

## Limits / known scope

- Mobile-first dashboard layout is out of scope for `web/`.
- Agents inside containers can't run `docker build` themselves (no Docker-in-
  Docker by default).
- The orchestrator's decompose step still runs on the host — it's a one-shot
  call to your local `claude` CLI to keep startup latency low and inherit your
  existing auth.
- The TUI's orchestrate handler doesn't auto-merge; that's CLI-only for now.

---

## Quick reference

```bash
# Setup (once)
pip install -e .                                  # from the repo
export ANTHROPIC_API_KEY=...                      # required for container mode on macOS
colima start                                       # if not already running
cd /path/to/your/project
treehouse init

# Daily use
treehouse orchestrate "high-level task"           # parallel + auto-merge
treehouse spawn name "focused task"               # single agent, manual merge
treehouse list                                    # what's running
treehouse dashboard                               # live TUI
treehouse merge name                              # integrate
treehouse destroy name                            # clean up

# Useful flags
--no-merge          # spawn agents in orchestrate but don't auto-merge
--host              # run agents on the host instead of in containers
```
