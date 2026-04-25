# treehouse/tui/agent_output.py
from __future__ import annotations

from collections import deque

from textual.widgets import RichLog
from textual.widget import Widget

from treehouse.core.models import AgentWorkspace


class AgentOutput(Widget):
    """Right-side panel showing the agent's text output."""

    def compose(self):
        yield RichLog(id="agent-output", wrap=True, highlight=True, markup=True)
        self._current_agent: str | None = None
        self._last_count: int = 0

    def clear_output(self) -> None:
        self.query_one(RichLog).clear()
        self._current_agent = None
        self._last_count = 0

    def update_output(self, agent_name: str, workspace: AgentWorkspace) -> None:
        log = self.query_one(RichLog)

        if agent_name != self._current_agent:
            log.clear()
            self._current_agent = agent_name
            self._last_count = 0
            # Show task context header
            log.write(f"[bold #a8e6cf]\u2500\u2500 {agent_name} [dim #30363d]{'─' * 30}[/][/]")
            log.write(f"[dim #6e7681]task:[/] [#c9d1d9]{workspace.task_prompt[:200]}[/]")
            log.write(f"[dim #6e7681]branch:[/] [#8b949e]{workspace.branch}[/]  "
                      f"[dim #6e7681]port:[/] [#8b949e]{workspace.port_base}[/]")
            log.write(f"[dim #30363d]{'─' * 44}[/]")

        output = workspace.output_buffer
        new_lines = list(output)[self._last_count:]
        for line in new_lines:
            log.write(f"[#e6edf3]{line}[/]")
        self._last_count = len(output)
