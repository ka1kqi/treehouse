# treehouse/tui/log_viewer.py
from __future__ import annotations

from collections import deque

from textual.widgets import RichLog
from textual.widget import Widget


class LogViewer(Widget):
    def compose(self):
        yield RichLog(id="log-output", wrap=True, highlight=True, markup=True)
        self._current_agent: str | None = None
        self._last_count: int = 0

    def update_logs(self, agent_name: str, log_buffer: deque[str]) -> None:
        log = self.query_one(RichLog)

        # Reset when switching agents
        if agent_name != self._current_agent:
            log.clear()
            self._current_agent = agent_name
            self._last_count = 0
            log.write(f"[bold cyan]── Logs: {agent_name} ──[/bold cyan]")

        new_lines = list(log_buffer)[self._last_count:]
        for line in new_lines:
            log.write(f"[dim]\\[{agent_name}][/dim] {line}")
        self._last_count = len(log_buffer)
