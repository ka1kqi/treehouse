# treehouse/tui/agent_table.py
from __future__ import annotations

from textual.widgets import DataTable
from textual.widget import Widget

from treehouse.core.models import AgentWorkspace


class AgentTable(Widget):
    selected_agent: str | None = None

    def __init__(self, workspaces: dict[str, AgentWorkspace]):
        super().__init__()
        self.workspaces = workspaces

    def compose(self):
        table = DataTable(id="agent-table")
        table.add_columns("Agent", "Branch", "Port", "Status", "Last Activity")
        yield table

    def on_mount(self) -> None:
        self.update_data(self.workspaces)

    def update_data(self, workspaces: dict[str, AgentWorkspace]) -> None:
        self.workspaces = workspaces
        table = self.query_one(DataTable)
        table.clear()
        for ws in workspaces.values():
            last = ws.log_buffer[-1] if ws.log_buffer else ""
            table.add_row(
                ws.name, ws.branch, str(ws.port_base),
                ws.status.value, last[:40], key=ws.name,
            )

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key:
            self.selected_agent = str(event.row_key.value)
