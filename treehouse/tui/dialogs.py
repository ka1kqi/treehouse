# treehouse/tui/dialogs.py
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label


class SpawnDialog(ModalScreen[tuple[str, str] | None]):
    BINDINGS = [("escape", "cancel", "Cancel")]
    CSS = """
    SpawnDialog {
        align: center middle;
    }
    #dialog-box {
        width: 60;
        height: 14;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog-box"):
            yield Label("Spawn New Agent")
            yield Label("Name:")
            yield Input(id="agent-name", placeholder="auth-fix")
            yield Label("Task:")
            yield Input(id="agent-task", placeholder="fix the login bug")
            yield Button("Spawn", variant="primary", id="spawn-btn")
            yield Button("Cancel", id="cancel-btn")

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "spawn-btn":
            name = self.query_one("#agent-name", Input).value
            task = self.query_one("#agent-task", Input).value
            if name and task:
                self.dismiss((name, task))
        else:
            self.dismiss(None)
