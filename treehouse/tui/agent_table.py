# treehouse/tui/agent_table.py
from __future__ import annotations

from textual.widgets import DataTable
from textual.widget import Widget

from treehouse.core.models import AgentWorkspace


class AgentTable(Widget):
    def __init__(self, workspaces: dict[str, AgentWorkspace]):
        super().__init__()
        self.workspaces = workspaces
        self._row_keys: list[str] = []

    @property
    def selected_agent(self) -> str | None:
        table = self.query_one(DataTable)
        if not self._row_keys or table.row_count == 0:
            return None
        idx = table.cursor_row
        if 0 <= idx < len(self._row_keys):
            return self._row_keys[idx]
        return None

    def compose(self):
        table = DataTable(id="agent-table", cursor_type="row")
        table.add_columns("Agent", "Branch", "Port", "Status", "Last Activity")
        yield table

    def on_mount(self) -> None:
        self.update_data(self.workspaces)

    def update_data(self, workspaces: dict[str, AgentWorkspace]) -> None:
        self.workspaces = workspaces
        table = self.query_one(DataTable)
        prev_cursor = table.cursor_row
        table.clear()
        self._row_keys = []
        for ws in workspaces.values():
            last = ws.log_buffer[-1] if ws.log_buffer else ""
            table.add_row(
                ws.name, ws.branch, str(ws.port_base),
                ws.status.value, last[:80], key=ws.name,
            )
            self._row_keys.append(ws.name)
        if table.row_count > 0:
            table.move_cursor(row=min(prev_cursor, table.row_count - 1))
