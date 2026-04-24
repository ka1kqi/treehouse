from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import asyncio


class AgentStatus(Enum):
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

    def __post_init__(self):
        if not self.branch:
            self.branch = f"treehouse/{self.name}"
        if not self.compose_project:
            self.compose_project = f"treehouse_{self.name.replace('-', '_')}"
