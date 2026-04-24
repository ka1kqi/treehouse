from __future__ import annotations

import asyncio
from pathlib import Path

import typer

from treehouse.config import TreehouseConfig
from treehouse.core.agent import AgentRunner
from treehouse.core.docker import DockerManager
from treehouse.core.env import rewrite_env
from treehouse.core.merger import MergeManager, MergeResult
from treehouse.core.models import AgentWorkspace
from treehouse.core.ports import PortAllocator
from treehouse.core.worktree import WorktreeManager

app = typer.Typer(name="treehouse", help="Parallel runtime isolation for multi-agent coding")

_workspaces: dict[str, AgentWorkspace] = {}
_port_allocator: PortAllocator | None = None


def _get_root() -> Path:
    return Path.cwd()


def _get_config() -> TreehouseConfig:
    return TreehouseConfig.load(_get_root())


def _get_allocator(config: TreehouseConfig) -> PortAllocator:
    global _port_allocator
    if _port_allocator is None:
        _port_allocator = PortAllocator(config.base_port)
    return _port_allocator


@app.command()
def init():
    """Initialize treehouse in the current repo."""
    root = _get_root()
    config = TreehouseConfig.init(root)
    typer.echo(f"Treehouse initialized in {root}")
    if config.compose_file:
        typer.echo(f"Detected compose file: {config.compose_file}")
    else:
        typer.echo("No docker-compose file detected.")


@app.command()
def spawn(name: str, task: str):
    """Spawn an isolated agent workspace."""
    config = _get_config()
    root = _get_root()
    allocator = _get_allocator(config)

    wt_mgr = WorktreeManager(root)
    wt_path = wt_mgr.create(name)
    port_base = allocator.allocate()

    workspace = AgentWorkspace(
        name=name, task_prompt=task,
        worktree_path=wt_path, port_base=port_base,
    )
    _workspaces[name] = workspace

    if config.compose_file:
        source_compose = root / config.compose_file
        if source_compose.exists():
            docker_mgr = DockerManager(source_compose)
            port_mapping = allocator.get_port_mapping(port_base, {"app": 3000})
            compose_out = wt_path / "docker-compose.treehouse.yml"
            docker_mgr.generate(compose_out, workspace.compose_project, port_mapping)
            docker_mgr.start(compose_out, workspace.compose_project)

    source_env = root / config.env_file if (root / config.env_file).exists() else None
    port_mapping = allocator.get_port_mapping(port_base, {"app": 3000})
    rewrite_env(source_env, wt_path / ".env", port_mapping)

    runner = AgentRunner()
    asyncio.run(_spawn_agent(runner, workspace))

    typer.echo(f"Spawned agent '{name}' on branch treehouse/{name}")
    typer.echo(f"  Worktree: {wt_path}")
    typer.echo(f"  Port base: {port_base}")


async def _spawn_agent(runner: AgentRunner, workspace: AgentWorkspace):
    await runner.start(workspace)
    await asyncio.gather(
        runner.stream_output(workspace),
        runner.wait(workspace),
    )


@app.command(name="list")
def list_agents():
    """List all agent workspaces."""
    if not _workspaces:
        typer.echo("No agents running. Use 'treehouse spawn' to create one.")
        return
    for ws in _workspaces.values():
        typer.echo(f"  {ws.name:<15} {ws.branch:<25} port:{ws.port_base} [{ws.status.value}]")


@app.command()
def merge(name: str):
    """Merge an agent's branch back to main."""
    root = _get_root()
    mgr = MergeManager(root)
    branch = f"treehouse/{name}"
    typer.echo(mgr.diff_stat(branch))

    result = mgr.merge(branch)
    if result == MergeResult.CLEAN:
        typer.echo(f"Merged {branch} cleanly.")
    elif result == MergeResult.CONFLICT:
        typer.echo("Conflicts detected. Launching AI merge agent...")
        ws = _workspaces.get(name)
        task = ws.task_prompt if ws else "unknown task"
        resolved = asyncio.run(mgr.ai_resolve(name, task))
        if resolved:
            typer.echo("Conflicts resolved by AI merge agent.")
        else:
            typer.echo("AI merge failed. Resolve manually.")
            mgr.abort_merge()
    else:
        typer.echo("Merge failed.")


@app.command()
def stop(name: str):
    """Stop a running agent."""
    ws = _workspaces.get(name)
    if not ws:
        typer.echo(f"No agent named '{name}'")
        raise typer.Exit(1)
    runner = AgentRunner()
    asyncio.run(runner.stop(ws))
    typer.echo(f"Stopped agent '{name}'")


@app.command()
def destroy(name: str):
    """Tear down an agent workspace and its Docker services."""
    config = _get_config()
    root = _get_root()

    ws = _workspaces.pop(name, None)
    if ws and ws.process:
        runner = AgentRunner()
        asyncio.run(runner.stop(ws))

    if config.compose_file:
        compose_file = root / ".treehouse" / "worktrees" / name / "docker-compose.treehouse.yml"
        if compose_file.exists():
            docker_mgr = DockerManager(root / config.compose_file)
            docker_mgr.stop(compose_file, f"treehouse_{name.replace('-', '_')}")

    wt_mgr = WorktreeManager(root)
    wt_mgr.destroy(name)
    typer.echo(f"Destroyed workspace '{name}'")


@app.command()
def dashboard():
    """Launch the TUI dashboard."""
    from treehouse.tui.app import TreehouseApp
    tui_app = TreehouseApp(workspaces=_workspaces)
    tui_app.run()


@app.command()
def server(port: int = 8080):
    """Start the WebSocket API server."""
    import uvicorn
    from treehouse.server.api import create_app
    from treehouse.server.state import StateManager

    state = StateManager()
    state.workspaces = _workspaces
    api = create_app(state)
    typer.echo(f"Treehouse API server on http://localhost:{port}")
    uvicorn.run(api, host="0.0.0.0", port=port)


@app.command()
def web():
    """Start the Next.js web dashboard."""
    import subprocess
    web_dir = Path(__file__).parent.parent / "web"
    if not web_dir.exists():
        typer.echo("Web dashboard not found. Run from the project root.")
        raise typer.Exit(1)
    if not (web_dir / "node_modules").exists():
        typer.echo("Installing web dependencies...")
        subprocess.run(["npm", "install"], cwd=str(web_dir), check=True)
    typer.echo("Starting web dashboard on http://localhost:3000")
    subprocess.run(["npm", "run", "dev"], cwd=str(web_dir))
