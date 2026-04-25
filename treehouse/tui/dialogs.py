# treehouse/tui/dialogs.py
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, Static

_DIALOG_BASE_CSS = """
    align: center middle;
"""

_BOX_CSS = """
    border: tall #30363d;
    background: #161b22;
    padding: 1 2;
"""


class SpawnDialog(ModalScreen[tuple[str, str] | None]):
    BINDINGS = [("escape", "cancel", "Cancel")]
    CSS = f"""
    SpawnDialog {{
        {_DIALOG_BASE_CSS}
        background: #0d1117 80%;
    }}
    #dialog-box {{
        width: 64;
        height: 14;
        {_BOX_CSS}
    }}
    .dialog-title {{
        color: #a8e6cf;
        text-style: bold;
        padding: 0 0 1 0;
    }}
    .dialog-label {{
        color: #8b949e;
        padding: 0;
    }}
    Input {{
        background: #0d1117;
        border: tall #30363d;
        color: #e6edf3;
        padding: 0 1;
    }}
    Input:focus {{
        border: tall #a8e6cf 50%;
    }}
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog-box"):
            yield Static("\u25b8 Spawn Agent", classes="dialog-title")
            yield Label("Name", classes="dialog-label")
            yield Input(id="agent-name", placeholder="auth-fix")
            yield Label("Task [dim](enter to spawn)[/]", classes="dialog-label")
            yield Input(id="agent-task", placeholder="fix the login bug")

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "agent-name":
            self.query_one("#agent-task", Input).focus()
        elif event.input.id == "agent-task":
            name = self.query_one("#agent-name", Input).value
            task = self.query_one("#agent-task", Input).value
            if name and task:
                self.dismiss((name, task))


class TaskDialog(ModalScreen[str | None]):
    BINDINGS = [("escape", "cancel", "Cancel")]
    CSS = f"""
    TaskDialog {{
        {_DIALOG_BASE_CSS}
        background: #0d1117 80%;
    }}
    #task-box {{
        width: 64;
        height: 8;
        {_BOX_CSS}
    }}
    .dialog-title {{
        color: #6ec6ff;
        text-style: bold;
        padding: 0 0 1 0;
    }}
    .dialog-label {{
        color: #8b949e;
        padding: 0;
    }}
    Input {{
        background: #0d1117;
        border: tall #30363d;
        color: #e6edf3;
        padding: 0 1;
    }}
    Input:focus {{
        border: tall #6ec6ff 50%;
    }}
    """

    def __init__(self, agent_name: str):
        super().__init__()
        self.agent_name = agent_name

    def compose(self) -> ComposeResult:
        with Vertical(id="task-box"):
            yield Static(f"\u25b8 New Task \u2014 [bold #e6edf3]{self.agent_name}[/]", classes="dialog-title")
            yield Label("Task [dim](enter to run)[/]", classes="dialog-label")
            yield Input(id="new-task", placeholder="add unit tests for the auth module")

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        task = self.query_one("#new-task", Input).value
        if task:
            self.dismiss(task)


class OrchestrateDialog(ModalScreen[str | None]):
    BINDINGS = [("escape", "cancel", "Cancel")]
    CSS = f"""
    OrchestrateDialog {{
        {_DIALOG_BASE_CSS}
        background: #0d1117 80%;
    }}
    #orch-box {{
        width: 72;
        height: 8;
        {_BOX_CSS}
    }}
    .dialog-title {{
        color: #c5a3ff;
        text-style: bold;
        padding: 0 0 1 0;
    }}
    .dialog-label {{
        color: #8b949e;
        padding: 0;
    }}
    Input {{
        background: #0d1117;
        border: tall #30363d;
        color: #e6edf3;
        padding: 0 1;
    }}
    Input:focus {{
        border: tall #c5a3ff 50%;
    }}
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="orch-box"):
            yield Static("\u25b8 Orchestrate \u2014 [dim #8b949e]decompose & spawn[/]", classes="dialog-title")
            yield Label("High-level task [dim](enter to orchestrate)[/]", classes="dialog-label")
            yield Input(id="orch-task", placeholder="build a full auth system with REST API")

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        task = self.query_one("#orch-task", Input).value
        if task:
            self.dismiss(task)
