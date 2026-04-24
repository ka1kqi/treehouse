# treehouse/tui/app.py
from __future__ import annotations

import asyncio
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Footer, Header

from treehouse.core.models import AgentWorkspace
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
        self.notify(f"Spawning agent '{name}'...")
        from treehouse.core.worktree import WorktreeManager
        from treehouse.core.ports import PortAllocator
        from treehouse.core.models import AgentWorkspace
        from treehouse.core.agent import AgentRunner
        from treehouse.config import TreehouseConfig

        config = TreehouseConfig.load(Path.cwd())
        wt_mgr = WorktreeManager(config.root)
        allocator = PortAllocator(config.base_port)

        wt_path = wt_mgr.create(name)
        port_base = allocator.allocate()
        ws = AgentWorkspace(
            name=name, task_prompt=task,
            worktree_path=wt_path, port_base=port_base,
        )
        self.workspaces[name] = ws

        runner = AgentRunner()
        self.run_worker(self._run_agent(runner, ws))

    async def _run_agent(self, runner, workspace):
        await runner.start(workspace)
        await asyncio.gather(
            runner.stream_output(workspace),
            runner.wait(workspace),
        )

    def action_merge(self) -> None:
        table = self.query_one(AgentTable)
        if table.selected_agent:
            self.notify(f"Merging {table.selected_agent}...")

    def action_kill(self) -> None:
        table = self.query_one(AgentTable)
        if table.selected_agent:
            self.notify(f"Killing {table.selected_agent}...")

    def action_destroy_agent(self) -> None:
        table = self.query_one(AgentTable)
        if table.selected_agent:
            self.notify(f"Destroying {table.selected_agent}...")
