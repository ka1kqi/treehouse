from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Footer, Header

from treehouse.config import TreehouseConfig
from treehouse.core.agent import AgentRunner
from treehouse.core.docker import ComposeGenerator, DockerManager
from treehouse.core.env import rewrite_env
from treehouse.core.models import AgentStatus, AgentWorkspace
from treehouse.core.ports import PortAllocator
from treehouse.core.worktree import WorktreeManager
from treehouse.tui.agent_table import AgentTable
from treehouse.tui.log_viewer import LogViewer


class TreehouseApp(App):
    CSS = """
    AgentTable {
        height: 40%;
        border: solid green;
    }
    LogViewer {
        height: 55%;
        border: solid cyan;
    }
    """

    BINDINGS = [
        ("s", "spawn", "Spawn"),
        ("e", "enter_sandbox", "Enter"),
        ("m", "merge", "Merge"),
        ("k", "kill", "Kill"),
        ("d", "destroy_agent", "Destroy"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, workspaces: dict[str, AgentWorkspace] | None = None):
        super().__init__()
        self.workspaces = workspaces or {}
        self._config: TreehouseConfig | None = None
        self._allocator: PortAllocator | None = None

    def _get_config(self) -> TreehouseConfig:
        if self._config is None:
            self._config = TreehouseConfig.load(Path.cwd())
        return self._config

    def _get_allocator(self) -> PortAllocator:
        if self._allocator is None:
            config = self._get_config()
            self._allocator = PortAllocator(config.base_port)
            # Fast-forward past existing ports
            if self.workspaces:
                max_port = max(ws.port_base for ws in self.workspaces.values())
                self._allocator._next = max_port - config.base_port + 1
        return self._allocator

    def _save(self) -> None:
        config = self._get_config()
        config.save_workspaces(self.workspaces)

    def compose(self) -> ComposeResult:
        yield Header(name="Treehouse")
        with Vertical():
            yield AgentTable(self.workspaces)
            yield LogViewer()
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(1.0, self.refresh_data)

    def refresh_data(self) -> None:
        table = self.query_one(AgentTable)
        table.update_data(self.workspaces)
        selected = table.selected_agent
        if selected and selected in self.workspaces:
            viewer = self.query_one(LogViewer)
            viewer.update_logs(self.workspaces[selected].log_buffer)

    def action_spawn(self) -> None:
        from treehouse.tui.dialogs import SpawnDialog
        self.push_screen(SpawnDialog(), self._on_spawn_result)

    def _on_spawn_result(self, result: tuple[str, str] | None) -> None:
        if result is None:
            return
        name, task = result

        if name in self.workspaces:
            self.notify(f"Agent '{name}' already exists", severity="error")
            return

        try:
            config = self._get_config()
            allocator = self._get_allocator()

            wt_mgr = WorktreeManager(config.root)
            wt_path = wt_mgr.create(name)
            port_base = allocator.allocate()

            # Auto-generate or use existing compose
            compose_out = wt_path / "docker-compose.treehouse.yml"
            ws_project = f"treehouse_{name.replace('-', '_')}"

            if config.compose_file and (config.root / config.compose_file).exists():
                # Use existing compose file as base
                generator = ComposeGenerator()
                _, port_defaults = generator.detect(config.root)
                port_mapping = allocator.get_port_mapping(port_base, port_defaults or {"app": 3000})
                docker_mgr = DockerManager(config.root / config.compose_file)
                docker_mgr.generate(compose_out, ws_project, port_mapping)
            else:
                # Auto-generate from project detection
                generator = ComposeGenerator()
                port_defaults = generator.generate(config.root, compose_out)
                port_mapping = allocator.get_port_mapping(port_base, port_defaults or {"app": 3000})
                # Rewrite ports in the generated file
                docker_mgr = DockerManager(compose_out)
                docker_mgr.generate(compose_out, ws_project, port_mapping)

            # Start containers
            docker_mgr.start(compose_out, ws_project)

            # Env rewriting
            source_env = config.root / config.env_file if (config.root / config.env_file).exists() else None
            rewrite_env(source_env, wt_path / ".env", port_mapping)

            ws = AgentWorkspace(
                name=name, task_prompt=task,
                worktree_path=wt_path, port_base=port_base,
            )
            self.workspaces[name] = ws
            self._save()

            self.notify(f"Spawned '{name}' on port {port_base}")

            runner = AgentRunner()
            self.run_worker(self._run_agent(runner, ws))
        except Exception as e:
            self.notify(f"Spawn failed: {e}", severity="error")

    async def _run_agent(self, runner: AgentRunner, workspace: AgentWorkspace) -> None:
        try:
            await runner.start(workspace)
            self._save()
            await asyncio.gather(
                runner.stream_output(workspace),
                runner.wait(workspace),
            )
        except Exception as e:
            workspace.status = AgentStatus.FAILED
            workspace.log_buffer.append(f"ERROR: {e}")
            self.call_from_thread(self.notify, f"Agent failed: {e}", severity="error")
        self._save()

    def action_enter_sandbox(self) -> None:
        table = self.query_one(AgentTable)
        name = table.selected_agent
        if not name or name not in self.workspaces:
            self.notify("No agent selected", severity="warning")
            return
        ws = self.workspaces[name]
        wt_path = str(ws.worktree_path)
        with self.suspend():
            subprocess.run(
                ["zsh", "-i"],
                cwd=wt_path,
                env={**__import__("os").environ, "TREEHOUSE_AGENT": name},
            )

    def action_merge(self) -> None:
        table = self.query_one(AgentTable)
        if table.selected_agent:
            self.notify(f"Merging {table.selected_agent}...")

    def action_kill(self) -> None:
        table = self.query_one(AgentTable)
        name = table.selected_agent
        if not name or name not in self.workspaces:
            self.notify("No agent selected", severity="warning")
            return
        ws = self.workspaces[name]
        if ws.process:
            ws.process.terminate()
        # Stop Docker services
        try:
            compose_file = ws.worktree_path / "docker-compose.treehouse.yml"
            if compose_file.exists():
                config = self._get_config()
                docker_mgr = DockerManager(config.root / config.compose_file)
                docker_mgr.stop(compose_file, ws.compose_project)
        except Exception:
            pass
        ws.status = AgentStatus.FAILED
        self._save()
        self.notify(f"Killed '{name}'")

    def action_destroy_agent(self) -> None:
        table = self.query_one(AgentTable)
        name = table.selected_agent
        if not name or name not in self.workspaces:
            self.notify("No agent selected", severity="warning")
            return
        try:
            config = self._get_config()
            ws = self.workspaces.pop(name)
            if ws.process:
                ws.process.terminate()
            # Stop Docker services
            try:
                compose_file = ws.worktree_path / "docker-compose.treehouse.yml"
                if compose_file.exists():
                    docker_mgr = DockerManager(config.root / config.compose_file)
                    docker_mgr.stop(compose_file, ws.compose_project)
            except Exception:
                pass
            # Remove worktree
            try:
                wt_mgr = WorktreeManager(config.root)
                wt_mgr.destroy(name)
            except Exception:
                pass  # worktree may not exist
            self._save()
            self.notify(f"Destroyed '{name}'")
        except Exception as e:
            self.notify(f"Destroy failed: {e}", severity="error")
