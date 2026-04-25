from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import asyncio


class AgentStatus(Enum):
    SPAWNING = "spawning"
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    MERGING = "merging"
    MERGED = "merged"


@dataclass
class AgentWorkspace:
    name: str
    task_prompt: str
    worktree_path: Path
    port_base: int
    branch: str = ""
    compose_project: str = ""
    status: AgentStatus = AgentStatus.PENDING
    process: asyncio.subprocess.Process | None = None
    log_buffer: deque[str] = field(default_factory=lambda: deque(maxlen=500))
    output_buffer: deque[str] = field(default_factory=lambda: deque(maxlen=500))

    def __post_init__(self):
        if not self.branch:
            self.branch = f"treehouse/{self.name}"
        if not self.compose_project:
            self.compose_project = f"treehouse_{self.name.replace('-', '_')}"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "task_prompt": self.task_prompt,
            "worktree_path": str(self.worktree_path),
            "port_base": self.port_base,
            "branch": self.branch,
            "compose_project": self.compose_project,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AgentWorkspace:
        ws = cls(
            name=data["name"],
            task_prompt=data["task_prompt"],
            worktree_path=Path(data["worktree_path"]),
            port_base=data["port_base"],
            branch=data.get("branch", ""),
            compose_project=data.get("compose_project", ""),
            status=AgentStatus(data.get("status", "pending")),
        )
        return ws
