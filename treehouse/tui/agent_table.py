# treehouse/tui/agent_table.py
from __future__ import annotations

from textual.widgets import DataTable
from textual.widget import Widget

from treehouse.core.models import AgentStatus, AgentWorkspace

# Status display: (icon, color)
STATUS_STYLE: dict[AgentStatus, tuple[str, str]] = {
    AgentStatus.SPAWNING: ("\u25cf", "#ffd93d"),   # yellow dot
    AgentStatus.PENDING:  ("\u25cb", "#8b949e"),    # dim circle
    AgentStatus.RUNNING:  ("\u25b6", "#a8e6cf"),    # green triangle
    AgentStatus.DONE:     ("\u2713", "#6ec6ff"),    # blue check
    AgentStatus.FAILED:   ("\u2717", "#ff6b6b"),    # red x
    AgentStatus.MERGING:  ("\u21c4", "#c5a3ff"),    # purple arrows
    AgentStatus.MERGED:   ("\u2714", "#b39ddb"),    # purple check
}


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
        table.add_columns("", "Agent", "Branch", "Port", "Status", "Activity")
        yield table

    def on_mount(self) -> None:
        self.update_data(self.workspaces)

    def _format_status(self, status: AgentStatus) -> str:
        icon, color = STATUS_STYLE.get(status, ("\u2022", "#888"))
        return f"[{color}]{status.value}[/]"

    def _format_icon(self, status: AgentStatus) -> str:
        icon, color = STATUS_STYLE.get(status, ("\u2022", "#888"))
        return f"[{color}]{icon}[/]"

    def _format_activity(self, ws: AgentWorkspace) -> str:
        if not ws.log_buffer:
            return "[dim #555]\u2014[/]"
        last = ws.log_buffer[-1]
        # Truncate and dim the activity
        if len(last) > 60:
            last = last[:57] + "..."
        return f"[#8b949e]{last}[/]"

    def update_data(self, workspaces: dict[str, AgentWorkspace]) -> None:
        self.workspaces = workspaces
        table = self.query_one(DataTable)
        prev_cursor = table.cursor_row
        table.clear()
        self._row_keys = []
        for ws in workspaces.values():
            table.add_row(
                self._format_icon(ws.status),
                f"[bold #e6edf3]{ws.name}[/]",
                f"[#8b949e]{ws.branch}[/]",
                f"[#8b949e]{ws.port_base}[/]",
                self._format_status(ws.status),
                self._format_activity(ws),
                key=ws.name,
            )
            self._row_keys.append(ws.name)
        if table.row_count > 0:
            table.move_cursor(row=min(prev_cursor, table.row_count - 1))
