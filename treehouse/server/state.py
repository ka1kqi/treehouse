from __future__ import annotations

import json
from typing import Callable

from treehouse.core.models import AgentWorkspace


class StateManager:
    def __init__(self):
        self.workspaces: dict[str, AgentWorkspace] = {}
        self.on_log: Callable[[str], None] | None = None
        self.on_status_change: Callable[[str], None] | None = None

    def add(self, workspace: AgentWorkspace) -> None:
        self.workspaces[workspace.name] = workspace

    def get(self, name: str) -> AgentWorkspace | None:
        return self.workspaces.get(name)

    def remove(self, name: str) -> AgentWorkspace | None:
        return self.workspaces.pop(name, None)

    def push_log(self, agent_name: str, line: str) -> None:
        ws = self.workspaces.get(agent_name)
        if ws:
            ws.log_buffer.append(line)
        msg = json.dumps({"type": "log", "agent": agent_name, "line": line})
        if self.on_log:
            self.on_log(msg)

    def set_status(self, agent_name: str, status) -> None:
        ws = self.workspaces.get(agent_name)
        if ws:
            ws.status = status
        msg = json.dumps({"type": "status_change", "agent": agent_name, "status": status.value})
        if self.on_status_change:
            self.on_status_change(msg)

    def snapshot(self) -> str:
        agents = []
        for ws in self.workspaces.values():
            agents.append({
                "name": ws.name,
                "branch": ws.branch,
                "port_base": ws.port_base,
                "status": ws.status.value,
                "task_prompt": ws.task_prompt,
                "compose_project": ws.compose_project,
                "last_log": ws.log_buffer[-1] if ws.log_buffer else "",
            })
        return json.dumps({"type": "state", "agents": agents})
