# treehouse/tui/log_viewer.py
from __future__ import annotations

from collections import deque

from textual.widgets import RichLog
from textual.widget import Widget


class LogViewer(Widget):
    def compose(self):
        yield RichLog(id="log-output", wrap=True, highlight=True, markup=True)

    def update_logs(self, log_buffer: deque[str]) -> None:
        log = self.query_one(RichLog)
        current_count = getattr(self, "_last_count", 0)
        new_lines = list(log_buffer)[current_count:]
        for line in new_lines:
            log.write(line)
        self._last_count = len(log_buffer)
