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

    def _style_line(self, line: str) -> str:
        """Apply contextual styling to log lines."""
        stripped = line.strip()
        # Tool use lines
        if stripped.startswith("[") and "]" in stripped:
            bracket_end = stripped.index("]")
            tool = stripped[1:bracket_end]
            rest = stripped[bracket_end + 1:]
            return f"[bold #a8e6cf]\u250a [#ffd93d]{tool}[/][/] [#c9d1d9]{rest}[/]"
        # Tool result lines
        if stripped.startswith("->"):
            return f"[#30363d]  \u2514[/] [dim #8b949e]{stripped[2:].strip()}[/]"
        # Error lines
        if "ERROR" in stripped or "error" in stripped.lower()[:20]:
            return f"[#ff6b6b]\u2022 {stripped}[/]"
        # Status/lifecycle lines
        if stripped.startswith("---") or "Creating" in stripped or "Launching" in stripped or "Docker" in stripped:
            return f"[dim #6e7681]\u2500 {stripped}[/]"
        # Agent finished
        if "finished" in stripped.lower():
            return f"[#6ec6ff]\u2713 {stripped}[/]"
        # STDERR
        if stripped.startswith("STDERR:"):
            return f"[#ff6b6b dim]{stripped}[/]"
        # Default
        return f"[#c9d1d9]{stripped}[/]"

    def clear_logs(self) -> None:
        self.query_one(RichLog).clear()
        self._current_agent = None
        self._last_count = 0

    def update_logs(self, agent_name: str, log_buffer: deque[str]) -> None:
        log = self.query_one(RichLog)

        if agent_name != self._current_agent:
            log.clear()
            self._current_agent = agent_name
            self._last_count = 0
            log.write(f"[bold #6ec6ff]\u2500\u2500 {agent_name} [dim #30363d]{'─' * 40}[/][/]")

        new_lines = list(log_buffer)[self._last_count:]
        for line in new_lines:
            styled = self._style_line(line)
            log.write(styled)
        self._last_count = len(log_buffer)
