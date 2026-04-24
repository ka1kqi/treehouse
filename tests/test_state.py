# tests/test_state.py
import json
from pathlib import Path
from treehouse.server.state import StateManager
from treehouse.core.models import AgentWorkspace, AgentStatus


def test_add_workspace():
    state = StateManager()
    ws = AgentWorkspace(
        name="auth-fix", task_prompt="fix login",
        worktree_path=Path("/tmp/ws"), port_base=3101,
    )
    state.add(ws)
    assert "auth-fix" in state.workspaces
    assert state.get("auth-fix") is ws


def test_snapshot_json():
    state = StateManager()
    ws = AgentWorkspace(
        name="auth-fix", task_prompt="fix login",
        worktree_path=Path("/tmp/ws"), port_base=3101,
    )
    state.add(ws)
    snapshot = state.snapshot()
    data = json.loads(snapshot)
    assert data["type"] == "state"
    assert len(data["agents"]) == 1
    assert data["agents"][0]["name"] == "auth-fix"
    assert data["agents"][0]["status"] == "pending"


def test_on_log_callback():
    state = StateManager()
    ws = AgentWorkspace(
        name="test", task_prompt="task",
        worktree_path=Path("/tmp/ws"), port_base=3101,
    )
    state.add(ws)
    received = []
    state.on_log = lambda msg: received.append(msg)
    state.push_log("test", "hello world")
    assert len(received) == 1
    assert "hello world" in received[0]
    assert ws.log_buffer[-1] == "hello world"
