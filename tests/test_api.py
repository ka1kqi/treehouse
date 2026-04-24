# tests/test_api.py
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from treehouse.server.api import create_app
from treehouse.server.state import StateManager
from treehouse.core.models import AgentWorkspace


@pytest.fixture
def state():
    s = StateManager()
    ws = AgentWorkspace(
        name="auth-fix", task_prompt="fix login",
        worktree_path=Path("/tmp/ws"), port_base=3101,
    )
    s.add(ws)
    return s


@pytest.fixture
def client(state):
    app = create_app(state)
    return TestClient(app)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_get_agents(client):
    resp = client.get("/agents")
    assert resp.status_code == 200
    agents = resp.json()["agents"]
    assert len(agents) == 1
    assert agents[0]["name"] == "auth-fix"


def test_websocket_receives_state(client):
    with client.websocket_connect("/ws") as ws:
        data = ws.receive_json()
        assert data["type"] == "state"
        assert len(data["agents"]) == 1
