from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Static

from treehouse.config import TreehouseConfig
from treehouse.core.agent import AgentRunner
from treehouse.core.docker import ComposeGenerator, DockerManager
from treehouse.core.env import rewrite_env
from treehouse.core.models import AgentStatus, AgentWorkspace
from treehouse.core.ports import PortAllocator
from treehouse.core.worktree import WorktreeManager
from treehouse.tui.agent_output import AgentOutput
from treehouse.tui.agent_table import AgentTable
from treehouse.tui.log_viewer import LogViewer


class TreehouseHeader(Static):
    """Custom branded header."""

    def render(self) -> str:
        return "[bold #a8e6cf]TREEHOUSE[/] [dim #888]//[/] [#666]multi-agent runtime[/]"


class StatusBar(Static):
    """Bottom status info bar above footer."""

    def __init__(self):
        super().__init__()
        self._counts: dict[str, int] = {}

    def update_counts(self, workspaces: dict[str, AgentWorkspace]) -> None:
        counts: dict[str, int] = {}
        for ws in workspaces.values():
            s = ws.status.value
            counts[s] = counts.get(s, 0) + 1
        if counts != self._counts:
            self._counts = counts
            self.refresh()

    def render(self) -> str:
        if not self._counts:
            return "[dim #555]no agents[/]"
        parts = []
        style_map = {
            "running": "#a8e6cf",
            "spawning": "#ffd93d",
            "pending": "#c4c4c4",
            "done": "#6ec6ff",
            "failed": "#ff6b6b",
            "merging": "#c5a3ff",
            "merged": "#b39ddb",
        }
        for status, count in self._counts.items():
            color = style_map.get(status, "#888")
            parts.append(f"[{color}]{count} {status}[/]")
        return " [dim #444]\u2502[/] ".join(parts) + f" [dim #444]\u2502[/] [dim #666]{sum(self._counts.values())} total[/]"


class TreehouseApp(App):
    CSS = """
    Screen {
        background: #0d1117;
    }

    TreehouseHeader {
        dock: top;
        height: 1;
        padding: 0 1;
        background: #161b22;
        color: #c9d1d9;
    }

    StatusBar {
        dock: bottom;
        height: 1;
        padding: 0 1;
        background: #161b22;
        color: #8b949e;
    }

    #main-container {
        height: 1fr;
        padding: 0;
    }

    AgentTable {
        height: 38%;
        margin: 0 1;
        border: tall #30363d;
        border-title-color: #a8e6cf;
        border-title-style: bold;
        background: #0d1117;
    }

    AgentTable:focus-within {
        border: tall #a8e6cf 40%;
    }

    #bottom-split {
        height: 1fr;
    }

    LogViewer {
        width: 1fr;
        margin: 0 0 0 1;
        border: tall #30363d;
        border-title-color: #6ec6ff;
        border-title-style: bold;
        background: #0d1117;
    }

    LogViewer:focus-within {
        border: tall #6ec6ff 40%;
    }

    AgentOutput {
        width: 1fr;
        margin: 0 1 0 0;
        border: tall #30363d;
        border-title-color: #a8e6cf;
        border-title-style: bold;
        background: #0d1117;
    }

    AgentOutput:focus-within {
        border: tall #a8e6cf 40%;
    }

    #agent-table {
        background: #0d1117;
    }

    #agent-table > .datatable--header {
        background: #161b22;
        color: #8b949e;
        text-style: bold;
    }

    #agent-table > .datatable--cursor {
        background: #1f2937;
        color: #e6edf3;
    }

    #agent-table > .datatable--hover {
        background: #161b22;
    }

    #log-output, #agent-output {
        background: #0d1117;
        scrollbar-color: #30363d;
        scrollbar-color-hover: #484f58;
        scrollbar-color-active: #6e7681;
    }

    Footer {
        background: #161b22;
        color: #8b949e;
    }

    Footer > .footer--key {
        background: #21262d;
        color: #a8e6cf;
    }

    Footer > .footer--description {
        color: #8b949e;
    }
    """

    BINDINGS = [
        ("s", "spawn", "Spawn"),
        ("t", "new_task", "Task"),
        ("o", "orchestrate", "Orchestrate"),
        ("e", "enter_sandbox", "Enter"),
        ("c", "copy_logs", "Copy"),
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
            if self.workspaces:
                max_port = max(ws.port_base for ws in self.workspaces.values())
                self._allocator._next = max_port - config.base_port + 1
        return self._allocator

    def _save(self) -> None:
        config = self._get_config()
        config.save_workspaces(self.workspaces)

    def compose(self) -> ComposeResult:
        yield TreehouseHeader()
        with Vertical(id="main-container"):
            yield AgentTable(self.workspaces)
            with Horizontal(id="bottom-split"):
                yield LogViewer()
                yield AgentOutput()
        yield StatusBar()
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(1.0, self.refresh_data)
        # Set border titles
        self.query_one(AgentTable).border_title = "\u25b8 AGENTS"
        self.query_one(LogViewer).border_title = "\u25b8 ACTIVITY"
        self.query_one(AgentOutput).border_title = "\u25b8 OUTPUT"

    def refresh_data(self) -> None:
        table = self.query_one(AgentTable)
        table.update_data(self.workspaces)
        # Update status bar
        self.query_one(StatusBar).update_counts(self.workspaces)
        selected = table.selected_agent
        if selected and selected in self.workspaces:
            ws = self.workspaces[selected]
            viewer = self.query_one(LogViewer)
            viewer.update_logs(selected, ws.log_buffer)
            viewer.border_title = f"\u25b8 ACTIVITY \u2014 {selected}"
            output = self.query_one(AgentOutput)
            output.update_output(selected, ws)
            output.border_title = f"\u25b8 OUTPUT \u2014 {selected}"

    def action_spawn(self) -> None:
        from treehouse.tui.dialogs import SpawnDialog
        self.push_screen(SpawnDialog(), self._on_spawn_result)

    def action_new_task(self) -> None:
        table = self.query_one(AgentTable)
        name = table.selected_agent
        if not name or name not in self.workspaces:
            self.notify("No agent selected", severity="warning")
            return
        from treehouse.tui.dialogs import TaskDialog
        self.push_screen(TaskDialog(name), self._on_task_result)

    def action_orchestrate(self) -> None:
        from treehouse.tui.dialogs import OrchestrateDialog
        self.push_screen(OrchestrateDialog(), self._on_orchestrate_result)

    def _on_orchestrate_result(self, result: str | None) -> None:
        if result is None:
            return
        self.notify("Decomposing task...")
        self.run_worker(self._orchestrate(result))

    async def _orchestrate(self, task: str) -> None:
        try:
            config = self._get_config()
            runner = AgentRunner()

            subtasks = await runner.decompose_task(task, str(config.root))
            self.notify(f"Decomposed into {len(subtasks)} subtasks")

            for name, subtask in subtasks:
                final_name = name
                counter = 2
                while final_name in self.workspaces:
                    final_name = f"{name}-{counter}"
                    counter += 1
                self._on_spawn_result((final_name, subtask))
        except Exception as e:
            self.notify(f"Orchestration failed: {e}", severity="error")

    def _on_task_result(self, result: str | None) -> None:
        if result is None:
            return
        table = self.query_one(AgentTable)
        name = table.selected_agent
        if not name or name not in self.workspaces:
            return
        ws = self.workspaces[name]
        if ws.process:
            ws.process.terminate()
        ws.task_prompt = result
        ws.status = AgentStatus.PENDING
        ws.log_buffer.append(f"--- New task: {result} ---")
        self._save()
        runner = AgentRunner()
        self.run_worker(self._run_agent(runner, ws))

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

            port_base = allocator.allocate()
            ws = AgentWorkspace(
                name=name, task_prompt=task,
                worktree_path=Path("."),
                port_base=port_base,
                status=AgentStatus.SPAWNING,
            )
            self.workspaces[name] = ws
            self._save()

            ws.log_buffer.append("Creating git worktree...")
            wt_mgr = WorktreeManager(config.root)
            wt_path = wt_mgr.create(name)
            ws.worktree_path = wt_path

            ws.log_buffer.append("Generating Docker Compose...")
            compose_out = wt_path / "docker-compose.treehouse.yml"
            ws_project = f"treehouse_{name.replace('-', '_')}"

            if config.compose_file and (config.root / config.compose_file).exists():
                generator = ComposeGenerator()
                _, port_defaults = generator.detect(config.root)
                port_mapping = allocator.get_port_mapping(port_base, port_defaults or {"app": 3000})
                docker_mgr = DockerManager(config.root / config.compose_file)
                docker_mgr.generate(compose_out, ws_project, port_mapping)
            else:
                generator = ComposeGenerator()
                port_defaults = generator.generate(config.root, compose_out)
                port_mapping = allocator.get_port_mapping(port_base, port_defaults or {"app": 3000})
                docker_mgr = DockerManager(compose_out)
                docker_mgr.generate(compose_out, ws_project, port_mapping)

            ws.log_buffer.append("Starting Docker containers...")
            try:
                docker_mgr.start(compose_out, ws_project)
                ws.log_buffer.append("Docker containers started.")
            except Exception as e:
                ws.log_buffer.append(f"Docker failed (non-fatal): {e}")
                self.notify("Docker containers failed to start", severity="warning")

            ws.log_buffer.append("Rewriting .env with isolated ports...")
            source_env = config.root / config.env_file if (config.root / config.env_file).exists() else None
            rewrite_env(source_env, wt_path / ".env", port_mapping)

            ws.status = AgentStatus.PENDING
            self._save()

            self.notify(f"Spawned '{name}' on port {port_base}")

            runner = AgentRunner()
            self.run_worker(self._run_agent(runner, ws))
        except Exception as e:
            self.notify(f"Spawn failed: {e}", severity="error")

    async def _run_agent(self, runner: AgentRunner, workspace: AgentWorkspace) -> None:
        try:
            workspace.log_buffer.append("Launching Claude agent...")
            await runner.start(workspace)
            workspace.log_buffer.append(f"Claude running (pid {workspace.process.pid})")
            self._save()
            await asyncio.gather(
                runner.stream_output(workspace),
                runner.wait(workspace),
            )
            workspace.log_buffer.append(f"Agent finished: {workspace.status.value}")
        except Exception as e:
            workspace.status = AgentStatus.FAILED
            workspace.log_buffer.append(f"ERROR: {e}")
            self.notify(f"Agent failed: {e}", severity="error")
        self._save()

    def action_copy_logs(self) -> None:
        table = self.query_one(AgentTable)
        name = table.selected_agent
        if not name or name not in self.workspaces:
            self.notify("No agent selected", severity="warning")
            return
        ws = self.workspaces[name]
        if not ws.log_buffer:
            self.notify("No logs to copy", severity="warning")
            return
        text = "\n".join(ws.log_buffer)
        try:
            subprocess.run(["pbcopy"], input=text.encode(), check=True)
        except Exception:
            self.copy_to_clipboard(text)
        self.notify(f"Copied {len(ws.log_buffer)} log lines")

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
            try:
                compose_file = ws.worktree_path / "docker-compose.treehouse.yml"
                if compose_file.exists():
                    docker_mgr = DockerManager(config.root / config.compose_file)
                    docker_mgr.stop(compose_file, ws.compose_project)
            except Exception:
                pass
            try:
                wt_mgr = WorktreeManager(config.root)
                wt_mgr.destroy(name)
            except Exception:
                pass
            self._save()
            # Clear bottom panels if they were showing this agent
            self.query_one(LogViewer).clear_logs()
            self.query_one(AgentOutput).clear_output()
            self.query_one(LogViewer).border_title = "\u25b8 ACTIVITY"
            self.query_one(AgentOutput).border_title = "\u25b8 OUTPUT"
            self.notify(f"Destroyed '{name}'")
        except Exception as e:
            self.notify(f"Destroy failed: {e}", severity="error")
