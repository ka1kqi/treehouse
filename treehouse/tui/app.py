from __future__ import annotations

import asyncio
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Footer, Header

from treehouse.config import TreehouseConfig
from treehouse.core.agent import AgentRunner
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

            # Env rewriting
            source_env = config.root / config.env_file if (config.root / config.env_file).exists() else None
            port_mapping = allocator.get_port_mapping(port_base, {"app": 3000})
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
        except Exception:
            workspace.status = AgentStatus.FAILED
        self._save()

    def action_merge(self) -> None:
        table = self.query_one(AgentTable)
        if table.selected_agent:
            self.notify(f"Merging {table.selected_agent}...")

    def action_kill(self) -> None:
        table = self.query_one(AgentTable)
        name = table.selected_agent
        if not name or name not in self.workspaces:
            return
        ws = self.workspaces[name]
        if ws.process:
            ws.process.terminate()
        ws.status = AgentStatus.FAILED
        self._save()
        self.notify(f"Killed '{name}'")

    def action_destroy_agent(self) -> None:
        table = self.query_one(AgentTable)
        name = table.selected_agent
        if not name or name not in self.workspaces:
            return
        try:
            config = self._get_config()
            ws = self.workspaces.pop(name)
            if ws.process:
                ws.process.terminate()
            wt_mgr = WorktreeManager(config.root)
            wt_mgr.destroy(name)
            self._save()
            self.notify(f"Destroyed '{name}'")
        except Exception as e:
            self.notify(f"Destroy failed: {e}", severity="error")
