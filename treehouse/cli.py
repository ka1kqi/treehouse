from __future__ import annotations

import asyncio
from pathlib import Path

import typer

from treehouse.config import TreehouseConfig
from treehouse.core.agent import AgentRunner
from treehouse.core.docker import ComposeGenerator, DockerManager
from treehouse.core.env import rewrite_env
from treehouse.core.merger import MergeManager, MergeResult
from treehouse.core.models import AgentStatus, AgentWorkspace
from treehouse.core.ports import PortAllocator
from treehouse.core.worktree import WorktreeManager

app = typer.Typer(name="treehouse", help="Parallel runtime isolation for multi-agent coding")


def _get_root() -> Path:
    return Path.cwd()


def _get_config() -> TreehouseConfig:
    return TreehouseConfig.load(_get_root())


def _load_workspaces(config: TreehouseConfig) -> dict[str, AgentWorkspace]:
    return config.load_workspaces()


def _save_workspaces(config: TreehouseConfig, workspaces: dict[str, AgentWorkspace]) -> None:
    config.save_workspaces(workspaces)


def _get_allocator(config: TreehouseConfig, workspaces: dict[str, AgentWorkspace]) -> PortAllocator:
    allocator = PortAllocator(config.base_port)
    # Fast-forward allocator past already-used ports
    if workspaces:
        max_port = max(ws.port_base for ws in workspaces.values())
        allocator._next = max_port - config.base_port + 1
    return allocator


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
    workspaces = _load_workspaces(config)
    allocator = _get_allocator(config, workspaces)

    wt_mgr = WorktreeManager(root)
    wt_path = wt_mgr.create(name)
    port_base = allocator.allocate()

    workspace = AgentWorkspace(
        name=name, task_prompt=task,
        worktree_path=wt_path, port_base=port_base,
    )
    workspaces[name] = workspace

    # Auto-generate or use existing compose
    compose_out = wt_path / "docker-compose.treehouse.yml"
    if config.compose_file and (root / config.compose_file).exists():
        generator = ComposeGenerator()
        _, port_defaults = generator.detect(root)
        port_mapping = allocator.get_port_mapping(port_base, port_defaults or {"app": 3000})
        docker_mgr = DockerManager(root / config.compose_file)
        docker_mgr.generate(compose_out, workspace.compose_project, port_mapping)
    else:
        generator = ComposeGenerator()
        port_defaults = generator.generate(root, compose_out)
        port_mapping = allocator.get_port_mapping(port_base, port_defaults or {"app": 3000})
        docker_mgr = DockerManager(compose_out)
        docker_mgr.generate(compose_out, workspace.compose_project, port_mapping)

    try:
        docker_mgr.start(compose_out, workspace.compose_project)
    except Exception as e:
        typer.echo(f"Docker containers failed to start (non-fatal): {e}")

    source_env = root / config.env_file if (root / config.env_file).exists() else None
    rewrite_env(source_env, wt_path / ".env", port_mapping)

    # Save state to disk
    _save_workspaces(config, workspaces)

    typer.echo(f"Spawned agent '{name}' on branch treehouse/{name}")
    typer.echo(f"  Worktree: {wt_path}")
    typer.echo(f"  Port base: {port_base}")

    # Launch Claude agent
    typer.echo(f"  Launching Claude agent...")
    runner = AgentRunner()
    asyncio.run(_run_cli_agent(runner, workspace, config, workspaces))


async def _run_cli_agent(runner: AgentRunner, workspace: AgentWorkspace, config: TreehouseConfig, workspaces: dict) -> None:
    try:
        await runner.start(workspace)
        _save_workspaces(config, workspaces)
        await asyncio.gather(
            runner.stream_output(workspace),
            runner.wait(workspace),
        )
    except Exception as e:
        workspace.status = AgentStatus.FAILED
        typer.echo(f"  Agent failed: {e}")
    _save_workspaces(config, workspaces)
    typer.echo(f"  Agent '{workspace.name}' finished with status: {workspace.status.value}")


@app.command()
def orchestrate(
    task: str,
    auto_merge: bool = typer.Option(
        True,
        "--merge/--no-merge",
        help="Sequentially merge each agent's branch back to the current branch when all agents finish.",
    ),
):
    """Decompose a high-level task and spawn parallel agents."""
    config = _get_config()
    root = _get_root()
    workspaces = _load_workspaces(config)

    typer.echo(f"Decomposing task: {task}")
    runner = AgentRunner()
    subtasks = asyncio.run(runner.decompose_task(task, str(root)))

    typer.echo(f"Plan ({len(subtasks)} subtasks):")
    for name, sub in subtasks:
        typer.echo(f"  - {name}: {sub[:80]}")

    allocator = _get_allocator(config, workspaces)
    wt_mgr = WorktreeManager(root)

    agent_runs = []
    spawned: list[AgentWorkspace] = []
    for name, sub in subtasks:
        # Avoid name collisions
        final_name = name
        counter = 2
        while final_name in workspaces:
            final_name = f"{name}-{counter}"
            counter += 1

        wt_path = wt_mgr.create(final_name)
        port_base = allocator.allocate()

        ws = AgentWorkspace(
            name=final_name, task_prompt=sub,
            worktree_path=wt_path, port_base=port_base,
        )
        workspaces[final_name] = ws
        spawned.append(ws)

        # Docker setup
        compose_out = wt_path / "docker-compose.treehouse.yml"
        if config.compose_file and (root / config.compose_file).exists():
            generator = ComposeGenerator()
            _, port_defaults = generator.detect(root)
            port_mapping = allocator.get_port_mapping(port_base, port_defaults or {"app": 3000})
            docker_mgr = DockerManager(root / config.compose_file)
            docker_mgr.generate(compose_out, ws.compose_project, port_mapping)
        else:
            generator = ComposeGenerator()
            port_defaults = generator.generate(root, compose_out)
            port_mapping = allocator.get_port_mapping(port_base, port_defaults or {"app": 3000})
            docker_mgr = DockerManager(compose_out)
            docker_mgr.generate(compose_out, ws.compose_project, port_mapping)

        try:
            docker_mgr.start(compose_out, ws.compose_project)
        except Exception as e:
            typer.echo(f"  Docker failed for {final_name} (non-fatal): {e}")

        source_env = root / config.env_file if (root / config.env_file).exists() else None
        rewrite_env(source_env, wt_path / ".env", port_mapping)

        typer.echo(f"Spawned '{final_name}' on port {port_base}")
        agent_runs.append(_run_cli_agent(runner, ws, config, workspaces))

    _save_workspaces(config, workspaces)

    typer.echo(f"Launching {len(agent_runs)} agents in parallel...")
    mgr = MergeManager(root) if auto_merge else None
    save = lambda: _save_workspaces(config, workspaces)
    asyncio.run(_orchestrate_agents(agent_runs, mgr, spawned, save))

    if auto_merge:
        merged = sum(1 for ws in spawned if ws.status == AgentStatus.MERGED)
        typer.echo(f"\nDone. {merged}/{len(spawned)} agents merged.")
    else:
        typer.echo(
            "All orchestrated agents finished. "
            "Run `treehouse merge <name>` to integrate each."
        )


async def _run_all(coros: list) -> None:
    await asyncio.gather(*coros)


async def _orchestrate_agents(
    coros: list,
    mgr: MergeManager | None,
    spawned: list[AgentWorkspace],
    save,
) -> None:
    await asyncio.gather(*coros)
    if mgr is not None:
        await _merge_spawned(mgr, spawned, save)


async def _merge_spawned(
    mgr: MergeManager,
    spawned: list[AgentWorkspace],
    save,
) -> int:
    """Sequentially merge each DONE agent's branch. Returns count merged.

    On clean merge: marks workspace MERGED.
    On conflict: invokes the AI conflict resolver. On AI failure, aborts the
    merge and stops (the repo is left clean; remaining agents are skipped so
    the user can intervene).
    """
    merged = 0
    for ws in spawned:
        if ws.status != AgentStatus.DONE:
            typer.echo(f"  skip merge of '{ws.name}' (status: {ws.status.value})")
            continue
        typer.echo(f"\nMerging {ws.branch}...")
        stat = mgr.diff_stat(ws.branch).rstrip()
        if stat:
            typer.echo(stat)
        result = mgr.merge(ws.branch)
        if result == MergeResult.CLEAN:
            ws.status = AgentStatus.MERGED
            save()
            merged += 1
            typer.echo("  ✓ merged cleanly")
        elif result == MergeResult.CONFLICT:
            typer.echo("  ⚠ conflicts — invoking AI merger")
            resolved = await mgr.ai_resolve(ws.name, ws.task_prompt)
            if resolved:
                ws.status = AgentStatus.MERGED
                save()
                merged += 1
                typer.echo("  ✓ resolved by AI merger")
            else:
                typer.echo(
                    f"  ✗ AI merge failed; aborting. "
                    f"Resolve '{ws.name}' manually with `treehouse merge {ws.name}`."
                )
                mgr.abort_merge()
                break
        else:
            typer.echo(f"  ✗ merge of {ws.branch} failed; stopping")
            break
    return merged


@app.command(name="list")
def list_agents():
    """List all agent workspaces."""
    config = _get_config()
    workspaces = _load_workspaces(config)
    if not workspaces:
        typer.echo("No agents. Use 'treehouse spawn' to create one.")
        return
    for ws in workspaces.values():
        typer.echo(f"  {ws.name:<15} {ws.branch:<25} port:{ws.port_base} [{ws.status.value}]")


@app.command()
def merge(name: str):
    """Merge an agent's branch back to main."""
    config = _get_config()
    root = _get_root()
    workspaces = _load_workspaces(config)
    mgr = MergeManager(root)
    branch = f"treehouse/{name}"
    typer.echo(mgr.diff_stat(branch))

    result = mgr.merge(branch)
    if result == MergeResult.CLEAN:
        typer.echo(f"Merged {branch} cleanly.")
        ws = workspaces.get(name)
        if ws:
            from treehouse.core.models import AgentStatus
            ws.status = AgentStatus.MERGED
            _save_workspaces(config, workspaces)
    elif result == MergeResult.CONFLICT:
        typer.echo("Conflicts detected. Launching AI merge agent...")
        ws = workspaces.get(name)
        task = ws.task_prompt if ws else "unknown task"
        resolved = asyncio.run(mgr.ai_resolve(name, task))
        if resolved:
            typer.echo("Conflicts resolved by AI merge agent.")
            if ws:
                from treehouse.core.models import AgentStatus
                ws.status = AgentStatus.MERGED
                _save_workspaces(config, workspaces)
        else:
            typer.echo("AI merge failed. Resolve manually.")
            mgr.abort_merge()
    else:
        typer.echo("Merge failed.")


@app.command()
def stop(name: str):
    """Stop a running agent."""
    config = _get_config()
    workspaces = _load_workspaces(config)
    ws = workspaces.get(name)
    if not ws:
        typer.echo(f"No agent named '{name}'")
        raise typer.Exit(1)
    from treehouse.core.models import AgentStatus
    ws.status = AgentStatus.FAILED
    _save_workspaces(config, workspaces)
    typer.echo(f"Stopped agent '{name}'")


@app.command()
def destroy(name: str):
    """Tear down an agent workspace and its Docker services."""
    config = _get_config()
    root = _get_root()
    workspaces = _load_workspaces(config)

    workspaces.pop(name, None)

    # Stop Docker containers
    compose_file = root / ".treehouse" / "worktrees" / name / "docker-compose.treehouse.yml"
    if compose_file.exists():
        try:
            docker_mgr = DockerManager(compose_file)
            docker_mgr.stop(compose_file, f"treehouse_{name.replace('-', '_')}")
        except Exception:
            pass

    wt_mgr = WorktreeManager(root)
    try:
        wt_mgr.destroy(name)
    except Exception:
        pass
    _save_workspaces(config, workspaces)
    typer.echo(f"Destroyed workspace '{name}'")


@app.command()
def dashboard():
    """Launch the TUI dashboard."""
    config = _get_config()
    workspaces = _load_workspaces(config)
    from treehouse.tui.app import TreehouseApp
    tui_app = TreehouseApp(workspaces=workspaces)
    tui_app.run()


@app.command()
def server(port: int = 8080):
    """Start the WebSocket API server."""
    import uvicorn
    from treehouse.server.api import create_app
    from treehouse.server.state import StateManager

    config = _get_config()
    workspaces = _load_workspaces(config)
    state = StateManager()
    state.workspaces = workspaces
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
