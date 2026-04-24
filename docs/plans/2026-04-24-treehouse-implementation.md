# Treehouse Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a CLI + TUI tool that spawns isolated worktree+Docker environments per AI agent, monitors Claude Code sessions in a live dashboard, and merges results with AI-assisted conflict resolution.

**Architecture:** Monolith Python package. Single Textual TUI process manages agent subprocesses. Each agent gets a git worktree, Docker Compose project, and rewritten .env. Claude Code runs in `--print --output-format stream-json` mode for parseable output streaming.

**Tech Stack:** Python 3.12+, Typer (CLI), Textual (TUI), PyYAML (config), asyncio (subprocess management)

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `treehouse/__init__.py`
- Create: `treehouse/core/__init__.py`
- Create: `treehouse/tui/__init__.py`

**Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "treehouse"
version = "0.1.0"
description = "Parallel runtime isolation for multi-agent coding"
requires-python = ">=3.12"
dependencies = [
    "typer>=0.9",
    "textual>=0.50",
    "pyyaml>=6.0",
]

[project.scripts]
treehouse = "treehouse.cli:app"
```

**Step 2: Create package init files**

```python
# treehouse/__init__.py
__version__ = "0.1.0"
```

```python
# treehouse/core/__init__.py
```

```python
# treehouse/tui/__init__.py
```

**Step 3: Install in dev mode and verify**

Run: `pip install -e .`
Expected: Successfully installed treehouse

**Step 4: Commit**

```bash
git add pyproject.toml treehouse/__init__.py treehouse/core/__init__.py treehouse/tui/__init__.py
git commit -m "feat: project scaffolding"
```

---

### Task 2: Data Model

**Files:**
- Create: `treehouse/core/models.py`
- Create: `tests/test_models.py`

**Step 1: Write the failing test**

```python
# tests/test_models.py
from treehouse.core.models import AgentStatus, AgentWorkspace
from pathlib import Path


def test_agent_status_values():
    assert AgentStatus.PENDING.value == "pending"
    assert AgentStatus.RUNNING.value == "running"
    assert AgentStatus.DONE.value == "done"
    assert AgentStatus.FAILED.value == "failed"
    assert AgentStatus.MERGING.value == "merging"
    assert AgentStatus.MERGED.value == "merged"


def test_agent_workspace_creation():
    ws = AgentWorkspace(
        name="auth-fix",
        task_prompt="fix the login bug",
        worktree_path=Path("/tmp/treehouse/auth-fix"),
        port_base=3101,
    )
    assert ws.name == "auth-fix"
    assert ws.branch == "treehouse/auth-fix"
    assert ws.compose_project == "treehouse_auth_fix"
    assert ws.status == AgentStatus.PENDING
    assert ws.process is None
    assert len(ws.log_buffer) == 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL — ModuleNotFoundError

**Step 3: Write the implementation**

```python
# treehouse/core/models.py
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: 2 passed

**Step 5: Commit**

```bash
git add treehouse/core/models.py tests/test_models.py
git commit -m "feat: add AgentWorkspace data model"
```

---

### Task 3: Port Allocation

**Files:**
- Create: `treehouse/core/ports.py`
- Create: `tests/test_ports.py`

**Step 1: Write the failing test**

```python
# tests/test_ports.py
from treehouse.core.ports import PortAllocator


def test_allocate_sequential():
    alloc = PortAllocator(base_port=3100)
    assert alloc.allocate() == 3101
    assert alloc.allocate() == 3102
    assert alloc.allocate() == 3103


def test_release_and_reuse():
    alloc = PortAllocator(base_port=3100)
    p1 = alloc.allocate()
    p2 = alloc.allocate()
    alloc.release(p1)
    p3 = alloc.allocate()
    assert p3 == p1


def test_port_mapping():
    alloc = PortAllocator(base_port=3100)
    port_base = alloc.allocate()
    mapping = alloc.get_port_mapping(port_base, {"app": 3000, "db": 5432, "redis": 6379})
    assert mapping == {
        "app": {"host": 3101, "container": 3000},
        "db": {"host": 5501, "container": 5432},
        "redis": {"host": 6401, "container": 6379},
    }
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_ports.py -v`
Expected: FAIL

**Step 3: Write the implementation**

```python
# treehouse/core/ports.py
from __future__ import annotations


class PortAllocator:
    def __init__(self, base_port: int = 3100):
        self.base_port = base_port
        self._next = 1
        self._released: list[int] = []

    def allocate(self) -> int:
        if self._released:
            return self._released.pop(0)
        port = self.base_port + self._next
        self._next += 1
        return port

    def release(self, port: int) -> None:
        if port not in self._released:
            self._released.append(port)
            self._released.sort()

    def get_port_mapping(
        self, port_base: int, services: dict[str, int]
    ) -> dict[str, dict[str, int]]:
        offset = port_base - self.base_port
        range_bases = {
            range(3000, 4000): 3100,
            range(5000, 6000): 5500,
            range(6000, 7000): 6400,
            range(8000, 9000): 8100,
        }
        mapping = {}
        for name, container_port in services.items():
            host_base = self.base_port
            for port_range, base in range_bases.items():
                if container_port in port_range:
                    host_base = base
                    break
            mapping[name] = {
                "host": host_base + offset,
                "container": container_port,
            }
        return mapping
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_ports.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add treehouse/core/ports.py tests/test_ports.py
git commit -m "feat: add port allocator"
```

---

### Task 4: Git Worktree Management

**Files:**
- Create: `treehouse/core/worktree.py`
- Create: `tests/test_worktree.py`

**Step 1: Write the failing test**

```python
# tests/test_worktree.py
import subprocess
from pathlib import Path

import pytest

from treehouse.core.worktree import WorktreeManager


@pytest.fixture
def git_repo(tmp_path):
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    readme = tmp_path / "README.md"
    readme.write_text("# Test")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-m", "init"],
        check=True, capture_output=True,
    )
    return tmp_path


def test_create_worktree(git_repo):
    mgr = WorktreeManager(git_repo)
    wt_path = mgr.create("auth-fix")
    assert wt_path.exists()
    assert (wt_path / "README.md").exists()
    result = subprocess.run(
        ["git", "-C", str(git_repo), "branch", "--list", "treehouse/auth-fix"],
        capture_output=True, text=True,
    )
    assert "treehouse/auth-fix" in result.stdout


def test_destroy_worktree(git_repo):
    mgr = WorktreeManager(git_repo)
    mgr.create("to-delete")
    mgr.destroy("to-delete")


def test_list_worktrees(git_repo):
    mgr = WorktreeManager(git_repo)
    mgr.create("one")
    mgr.create("two")
    names = mgr.list()
    assert "one" in names
    assert "two" in names
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_worktree.py -v`
Expected: FAIL

**Step 3: Write the implementation**

```python
# treehouse/core/worktree.py
from __future__ import annotations

import subprocess
from pathlib import Path

TREEHOUSE_DIR = ".treehouse"
WORKTREES_DIR = f"{TREEHOUSE_DIR}/worktrees"


class WorktreeManager:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.worktrees_dir = repo_root / WORKTREES_DIR

    def create(self, name: str) -> Path:
        wt_path = self.worktrees_dir / name
        wt_path.parent.mkdir(parents=True, exist_ok=True)
        branch = f"treehouse/{name}"
        subprocess.run(
            ["git", "-C", str(self.repo_root), "worktree", "add", str(wt_path), "-b", branch],
            check=True, capture_output=True,
        )
        return wt_path

    def destroy(self, name: str) -> None:
        wt_path = self.worktrees_dir / name
        subprocess.run(
            ["git", "-C", str(self.repo_root), "worktree", "remove", str(wt_path), "--force"],
            check=True, capture_output=True,
        )
        branch = f"treehouse/{name}"
        subprocess.run(
            ["git", "-C", str(self.repo_root), "branch", "-D", branch],
            capture_output=True,
        )

    def list(self) -> list[str]:
        if not self.worktrees_dir.exists():
            return []
        return [d.name for d in self.worktrees_dir.iterdir() if d.is_dir()]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_worktree.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add treehouse/core/worktree.py tests/test_worktree.py
git commit -m "feat: add git worktree manager"
```

---

### Task 5: Docker Compose Generation

**Files:**
- Create: `treehouse/core/docker.py`
- Create: `tests/test_docker.py`

**Step 1: Write the failing test**

```python
# tests/test_docker.py
from pathlib import Path
import yaml
from treehouse.core.docker import DockerManager


def test_generate_compose_file(tmp_path):
    source = tmp_path / "docker-compose.yml"
    source.write_text(yaml.dump({
        "services": {
            "app": {"build": ".", "ports": ["3000:3000"]},
            "db": {"image": "postgres:16", "ports": ["5432:5432"]},
        }
    }))
    mgr = DockerManager(source)
    port_mapping = {
        "app": {"host": 3101, "container": 3000},
        "db": {"host": 5501, "container": 5432},
    }
    output = tmp_path / "worktree" / "docker-compose.treehouse.yml"
    output.parent.mkdir()
    mgr.generate(output, "treehouse_auth_fix", port_mapping)

    result = yaml.safe_load(output.read_text())
    assert result["services"]["app"]["ports"] == ["3101:3000"]
    assert result["services"]["db"]["ports"] == ["5501:5432"]


def test_command_formation(tmp_path):
    source = tmp_path / "docker-compose.yml"
    source.write_text(yaml.dump({"services": {"app": {"image": "nginx"}}}))
    mgr = DockerManager(source)
    cmd = mgr._up_command(tmp_path / "compose.yml", "test_project")
    assert "docker" in cmd[0]
    assert "-p" in cmd
    assert "test_project" in cmd
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_docker.py -v`
Expected: FAIL

**Step 3: Write the implementation**

```python
# treehouse/core/docker.py
from __future__ import annotations

import subprocess
from pathlib import Path
import yaml


class DockerManager:
    def __init__(self, source_compose: Path):
        self.source_compose = source_compose

    def generate(
        self, output_path: Path, project_name: str,
        port_mapping: dict[str, dict[str, int]],
    ) -> None:
        with open(self.source_compose) as f:
            compose = yaml.safe_load(f)

        for service_name, ports in port_mapping.items():
            if service_name in compose.get("services", {}):
                compose["services"][service_name]["ports"] = [
                    f"{ports['host']}:{ports['container']}"
                ]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            yaml.dump(compose, f, default_flow_style=False)

    def _up_command(self, compose_file: Path, project_name: str) -> list[str]:
        return ["docker", "compose", "-f", str(compose_file), "-p", project_name, "up", "-d"]

    def _down_command(self, compose_file: Path, project_name: str) -> list[str]:
        return ["docker", "compose", "-f", str(compose_file), "-p", project_name, "down", "-v"]

    def start(self, compose_file: Path, project_name: str) -> None:
        subprocess.run(self._up_command(compose_file, project_name), check=True, capture_output=True)

    def stop(self, compose_file: Path, project_name: str) -> None:
        subprocess.run(self._down_command(compose_file, project_name), check=True, capture_output=True)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_docker.py -v`
Expected: 2 passed

**Step 5: Commit**

```bash
git add treehouse/core/docker.py tests/test_docker.py
git commit -m "feat: add Docker Compose manager"
```

---

### Task 6: Env File Rewriting

**Files:**
- Create: `treehouse/core/env.py`
- Create: `tests/test_env.py`

**Step 1: Write the failing test**

```python
# tests/test_env.py
from pathlib import Path
from treehouse.core.env import rewrite_env


def test_rewrite_env(tmp_path):
    source = tmp_path / ".env"
    source.write_text(
        "PORT=3000\n"
        "DATABASE_URL=postgres://localhost:5432/app\n"
        "REDIS_URL=redis://localhost:6379\n"
        "SECRET_KEY=abc123\n"
    )
    port_mapping = {
        "app": {"host": 3101, "container": 3000},
        "db": {"host": 5501, "container": 5432},
        "redis": {"host": 6401, "container": 6379},
    }
    output = tmp_path / "worktree" / ".env"
    output.parent.mkdir()
    rewrite_env(source, output, port_mapping)

    result = output.read_text()
    assert "PORT=3101" in result
    assert "5501" in result
    assert "6401" in result
    assert "SECRET_KEY=abc123" in result


def test_rewrite_env_no_source(tmp_path):
    output = tmp_path / ".env"
    port_mapping = {"app": {"host": 3101, "container": 3000}}
    rewrite_env(None, output, port_mapping)
    result = output.read_text()
    assert "PORT=3101" in result
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_env.py -v`
Expected: FAIL

**Step 3: Write the implementation**

```python
# treehouse/core/env.py
from __future__ import annotations

import re
from pathlib import Path


def rewrite_env(
    source: Path | None, output: Path,
    port_mapping: dict[str, dict[str, int]],
) -> None:
    port_map: dict[int, int] = {}
    for service in port_mapping.values():
        port_map[service["container"]] = service["host"]

    lines: list[str] = []
    if source and source.exists():
        for line in source.read_text().splitlines():
            rewritten = line
            for container_port, host_port in port_map.items():
                rewritten = re.sub(
                    rf"(?<!\d){container_port}(?!\d)",
                    str(host_port), rewritten,
                )
            lines.append(rewritten)
    else:
        if "app" in port_mapping:
            lines.append(f"PORT={port_mapping['app']['host']}")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_env.py -v`
Expected: 2 passed

**Step 5: Commit**

```bash
git add treehouse/core/env.py tests/test_env.py
git commit -m "feat: add env file rewriter"
```

---

### Task 7: Claude Code Agent Manager

**Files:**
- Create: `treehouse/core/agent.py`
- Create: `tests/test_agent.py`

**Step 1: Write the failing test**

```python
# tests/test_agent.py
from pathlib import Path
from treehouse.core.agent import AgentRunner
from treehouse.core.models import AgentWorkspace


def test_build_command():
    ws = AgentWorkspace(
        name="test", task_prompt="fix the bug",
        worktree_path=Path("/tmp/ws"), port_base=3101,
    )
    runner = AgentRunner()
    cmd = runner.build_command(ws)
    assert "claude" in cmd[0]
    assert "--print" in cmd
    assert "--output-format" in cmd
    assert "stream-json" in cmd
    assert "fix the bug" in cmd


def test_parse_stream_json_tool_use():
    runner = AgentRunner()
    line = '{"type":"assistant","subtype":"tool_use","tool":"Edit","content":"editing file"}'
    parsed = runner.parse_output_line(line)
    assert parsed is not None
    assert "Edit" in parsed
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_agent.py -v`
Expected: FAIL

**Step 3: Write the implementation**

```python
# treehouse/core/agent.py
from __future__ import annotations

import asyncio
import json

from treehouse.core.models import AgentStatus, AgentWorkspace


class AgentRunner:
    def build_command(self, workspace: AgentWorkspace) -> list[str]:
        return [
            "claude",
            "--print",
            "--output-format", "stream-json",
            "--dangerously-skip-permissions",
            "--add-dir", str(workspace.worktree_path),
            workspace.task_prompt,
        ]

    def parse_output_line(self, line: str) -> str | None:
        try:
            data = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            return line.strip() if line.strip() else None

        subtype = data.get("subtype", "")
        tool = data.get("tool", "")
        content = data.get("content", "")

        if subtype == "tool_use" and tool:
            return f"[{tool}] {content[:120]}"
        if subtype == "tool_result":
            return f"  -> {str(content)[:120]}"
        if content:
            return content[:120]
        return None

    async def start(self, workspace: AgentWorkspace) -> None:
        cmd = self.build_command(workspace)
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(workspace.worktree_path),
        )
        workspace.process = process
        workspace.status = AgentStatus.RUNNING

    async def stream_output(self, workspace: AgentWorkspace) -> None:
        if not workspace.process or not workspace.process.stdout:
            return
        async for raw_line in workspace.process.stdout:
            line = raw_line.decode("utf-8", errors="replace").strip()
            parsed = self.parse_output_line(line)
            if parsed:
                workspace.log_buffer.append(parsed)

    async def wait(self, workspace: AgentWorkspace) -> None:
        if not workspace.process:
            return
        returncode = await workspace.process.wait()
        workspace.status = AgentStatus.DONE if returncode == 0 else AgentStatus.FAILED
        workspace.process = None

    async def stop(self, workspace: AgentWorkspace) -> None:
        if workspace.process:
            workspace.process.terminate()
            await workspace.process.wait()
            workspace.status = AgentStatus.FAILED
            workspace.process = None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_agent.py -v`
Expected: 2 passed

**Step 5: Commit**

```bash
git add treehouse/core/agent.py tests/test_agent.py
git commit -m "feat: add Claude Code agent runner"
```

---

### Task 8: Merge Manager

**Files:**
- Create: `treehouse/core/merger.py`
- Create: `tests/test_merger.py`

**Step 1: Write the failing test**

```python
# tests/test_merger.py
import subprocess
from pathlib import Path
import pytest
from treehouse.core.merger import MergeManager, MergeResult


@pytest.fixture
def git_repo_with_branches(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "checkout", "-b", "main"], check=True, capture_output=True)
    (repo / "file.txt").write_text("original")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "init"], check=True, capture_output=True)

    subprocess.run(["git", "-C", str(repo), "checkout", "-b", "treehouse/feature"], check=True, capture_output=True)
    (repo / "file.txt").write_text("modified by agent")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "agent change"], check=True, capture_output=True)

    subprocess.run(["git", "-C", str(repo), "checkout", "main"], check=True, capture_output=True)
    return repo


def test_clean_merge(git_repo_with_branches):
    mgr = MergeManager(git_repo_with_branches)
    result = mgr.merge("treehouse/feature")
    assert result == MergeResult.CLEAN
    content = (git_repo_with_branches / "file.txt").read_text()
    assert content == "modified by agent"


def test_diff_stat(git_repo_with_branches):
    mgr = MergeManager(git_repo_with_branches)
    stat = mgr.diff_stat("treehouse/feature")
    assert "file.txt" in stat
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_merger.py -v`
Expected: FAIL

**Step 3: Write the implementation**

```python
# treehouse/core/merger.py
from __future__ import annotations

import asyncio
import subprocess
from enum import Enum
from pathlib import Path


class MergeResult(Enum):
    CLEAN = "clean"
    CONFLICT = "conflict"
    FAILED = "failed"


class MergeManager:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root

    def diff_stat(self, branch: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(self.repo_root), "diff", f"HEAD...{branch}", "--stat"],
            capture_output=True, text=True,
        )
        return result.stdout

    def merge(self, branch: str) -> MergeResult:
        result = subprocess.run(
            ["git", "-C", str(self.repo_root), "merge", branch, "--no-edit"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            return MergeResult.CLEAN

        status = subprocess.run(
            ["git", "-C", str(self.repo_root), "status", "--porcelain"],
            capture_output=True, text=True,
        )
        if "UU " in status.stdout or "AA " in status.stdout:
            return MergeResult.CONFLICT
        return MergeResult.FAILED

    def get_conflicts(self) -> list[str]:
        result = subprocess.run(
            ["git", "-C", str(self.repo_root), "diff", "--name-only", "--diff-filter=U"],
            capture_output=True, text=True,
        )
        return [f for f in result.stdout.strip().split("\n") if f]

    def abort_merge(self) -> None:
        subprocess.run(
            ["git", "-C", str(self.repo_root), "merge", "--abort"],
            capture_output=True,
        )

    def complete_merge(self, message: str) -> None:
        subprocess.run(
            ["git", "-C", str(self.repo_root), "add", "."],
            check=True, capture_output=True, cwd=str(self.repo_root),
        )
        subprocess.run(
            ["git", "-C", str(self.repo_root), "commit", "-m", message],
            check=True, capture_output=True,
        )

    async def ai_resolve(self, workspace_name: str, task_prompt: str) -> bool:
        conflicts = self.get_conflicts()
        if not conflicts:
            return True

        conflict_prompt = (
            f"You are resolving merge conflicts for branch 'treehouse/{workspace_name}'.\n"
            f"The original task was: {task_prompt}\n\n"
            f"Conflicted files: {', '.join(conflicts)}\n\n"
            "Resolve all conflicts keeping the intent of both sides. "
            "After resolving, stage the files with git add."
        )

        process = await asyncio.create_subprocess_exec(
            "claude", "--print", "--dangerously-skip-permissions",
            conflict_prompt,
            cwd=str(self.repo_root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.wait()

        if process.returncode == 0:
            self.complete_merge(f"merge: resolve conflicts for treehouse/{workspace_name}")
            return True
        return False
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_merger.py -v`
Expected: 2 passed

**Step 5: Commit**

```bash
git add treehouse/core/merger.py tests/test_merger.py
git commit -m "feat: add merge manager with AI conflict resolution"
```

---

### Task 9: Config Management

**Files:**
- Create: `treehouse/config.py`
- Create: `tests/test_config.py`

**Step 1: Write the failing test**

```python
# tests/test_config.py
from pathlib import Path
from treehouse.config import TreehouseConfig


def test_init_creates_config(tmp_path):
    config = TreehouseConfig.init(tmp_path)
    assert (tmp_path / ".treehouse" / "config.yml").exists()
    assert config.base_port == 3100


def test_load_existing_config(tmp_path):
    cfg_dir = tmp_path / ".treehouse"
    cfg_dir.mkdir()
    (cfg_dir / "config.yml").write_text("base_port: 4000\ncompose_file: docker-compose.dev.yml\n")
    config = TreehouseConfig.load(tmp_path)
    assert config.base_port == 4000
    assert config.compose_file == "docker-compose.dev.yml"


def test_detect_compose_file(tmp_path):
    (tmp_path / "docker-compose.yml").write_text("services: {}")
    config = TreehouseConfig.init(tmp_path)
    assert config.compose_file == "docker-compose.yml"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL

**Step 3: Write the implementation**

```python
# treehouse/config.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import yaml

CONFIG_DIR = ".treehouse"
CONFIG_FILE = "config.yml"


@dataclass
class TreehouseConfig:
    root: Path
    base_port: int = 3100
    compose_file: str = ""
    env_file: str = ".env"

    @classmethod
    def init(cls, root: Path) -> TreehouseConfig:
        cfg_dir = root / CONFIG_DIR
        cfg_dir.mkdir(parents=True, exist_ok=True)

        compose_file = ""
        for name in ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]:
            if (root / name).exists():
                compose_file = name
                break

        config = cls(root=root, compose_file=compose_file)
        config.save()
        return config

    @classmethod
    def load(cls, root: Path) -> TreehouseConfig:
        cfg_path = root / CONFIG_DIR / CONFIG_FILE
        if not cfg_path.exists():
            raise FileNotFoundError(f"No treehouse config at {cfg_path}. Run 'treehouse init' first.")
        with open(cfg_path) as f:
            data = yaml.safe_load(f) or {}
        return cls(
            root=root,
            base_port=data.get("base_port", 3100),
            compose_file=data.get("compose_file", ""),
            env_file=data.get("env_file", ".env"),
        )

    def save(self) -> None:
        cfg_path = self.root / CONFIG_DIR / CONFIG_FILE
        with open(cfg_path, "w") as f:
            yaml.dump({
                "base_port": self.base_port,
                "compose_file": self.compose_file,
                "env_file": self.env_file,
            }, f)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add treehouse/config.py tests/test_config.py
git commit -m "feat: add config management"
```

---

### Task 10: CLI Entry Point

**Files:**
- Create: `treehouse/cli.py`

**Step 1: Write the CLI**

```python
# treehouse/cli.py
from __future__ import annotations

import asyncio
from pathlib import Path

import typer

from treehouse.config import TreehouseConfig
from treehouse.core.agent import AgentRunner
from treehouse.core.docker import DockerManager
from treehouse.core.env import rewrite_env
from treehouse.core.merger import MergeManager, MergeResult
from treehouse.core.models import AgentWorkspace
from treehouse.core.ports import PortAllocator
from treehouse.core.worktree import WorktreeManager

app = typer.Typer(name="treehouse", help="Parallel runtime isolation for multi-agent coding")

_workspaces: dict[str, AgentWorkspace] = {}
_port_allocator: PortAllocator | None = None


def _get_root() -> Path:
    return Path.cwd()


def _get_config() -> TreehouseConfig:
    return TreehouseConfig.load(_get_root())


def _get_allocator(config: TreehouseConfig) -> PortAllocator:
    global _port_allocator
    if _port_allocator is None:
        _port_allocator = PortAllocator(config.base_port)
    return _port_allocator


@app.command()
def init():
    """Initialize treehouse in the current repo."""
    root = _get_root()
    config = TreehouseConfig.init(root)
    typer.echo(f"Treehouse initialized in {root}")
    if config.compose_file:
        typer.echo(f"Detected compose file: {config.compose_file}")
    else:
        typer.echo("No docker-compose file detected.")


@app.command()
def spawn(name: str, task: str):
    """Spawn an isolated agent workspace."""
    config = _get_config()
    root = _get_root()
    allocator = _get_allocator(config)

    wt_mgr = WorktreeManager(root)
    wt_path = wt_mgr.create(name)
    port_base = allocator.allocate()

    workspace = AgentWorkspace(
        name=name, task_prompt=task,
        worktree_path=wt_path, port_base=port_base,
    )
    _workspaces[name] = workspace

    if config.compose_file:
        source_compose = root / config.compose_file
        if source_compose.exists():
            docker_mgr = DockerManager(source_compose)
            port_mapping = allocator.get_port_mapping(port_base, {"app": 3000})
            compose_out = wt_path / "docker-compose.treehouse.yml"
            docker_mgr.generate(compose_out, workspace.compose_project, port_mapping)
            docker_mgr.start(compose_out, workspace.compose_project)

    source_env = root / config.env_file if (root / config.env_file).exists() else None
    port_mapping = allocator.get_port_mapping(port_base, {"app": 3000})
    rewrite_env(source_env, wt_path / ".env", port_mapping)

    runner = AgentRunner()
    asyncio.run(_spawn_agent(runner, workspace))

    typer.echo(f"Spawned agent '{name}' on branch treehouse/{name}")
    typer.echo(f"  Worktree: {wt_path}")
    typer.echo(f"  Port base: {port_base}")


async def _spawn_agent(runner: AgentRunner, workspace: AgentWorkspace):
    await runner.start(workspace)
    await asyncio.gather(
        runner.stream_output(workspace),
        runner.wait(workspace),
    )


@app.command(name="list")
def list_agents():
    """List all agent workspaces."""
    if not _workspaces:
        typer.echo("No agents running. Use 'treehouse spawn' to create one.")
        return
    for ws in _workspaces.values():
        typer.echo(f"  {ws.name:<15} {ws.branch:<25} port:{ws.port_base} [{ws.status.value}]")


@app.command()
def merge(name: str):
    """Merge an agent's branch back to main."""
    root = _get_root()
    mgr = MergeManager(root)
    branch = f"treehouse/{name}"
    typer.echo(mgr.diff_stat(branch))

    result = mgr.merge(branch)
    if result == MergeResult.CLEAN:
        typer.echo(f"Merged {branch} cleanly.")
    elif result == MergeResult.CONFLICT:
        typer.echo("Conflicts detected. Launching AI merge agent...")
        ws = _workspaces.get(name)
        task = ws.task_prompt if ws else "unknown task"
        resolved = asyncio.run(mgr.ai_resolve(name, task))
        if resolved:
            typer.echo("Conflicts resolved by AI merge agent.")
        else:
            typer.echo("AI merge failed. Resolve manually.")
            mgr.abort_merge()
    else:
        typer.echo("Merge failed.")


@app.command()
def stop(name: str):
    """Stop a running agent."""
    ws = _workspaces.get(name)
    if not ws:
        typer.echo(f"No agent named '{name}'")
        raise typer.Exit(1)
    runner = AgentRunner()
    asyncio.run(runner.stop(ws))
    typer.echo(f"Stopped agent '{name}'")


@app.command()
def destroy(name: str):
    """Tear down an agent workspace and its Docker services."""
    config = _get_config()
    root = _get_root()

    ws = _workspaces.pop(name, None)
    if ws and ws.process:
        runner = AgentRunner()
        asyncio.run(runner.stop(ws))

    if config.compose_file:
        compose_file = root / ".treehouse" / "worktrees" / name / "docker-compose.treehouse.yml"
        if compose_file.exists():
            docker_mgr = DockerManager(root / config.compose_file)
            docker_mgr.stop(compose_file, f"treehouse_{name.replace('-', '_')}")

    wt_mgr = WorktreeManager(root)
    wt_mgr.destroy(name)
    typer.echo(f"Destroyed workspace '{name}'")


@app.command()
def dashboard():
    """Launch the TUI dashboard."""
    from treehouse.tui.app import TreehouseApp
    tui_app = TreehouseApp(workspaces=_workspaces)
    tui_app.run()
```

**Step 2: Verify CLI loads**

Run: `treehouse --help`
Expected: Shows help text with all commands

**Step 3: Commit**

```bash
git add treehouse/cli.py
git commit -m "feat: add CLI entry point"
```

---

### Task 11: TUI Dashboard

**Files:**
- Create: `treehouse/tui/app.py`
- Create: `treehouse/tui/agent_table.py`
- Create: `treehouse/tui/log_viewer.py`

**Step 1: Build the Textual app**

```python
# treehouse/tui/app.py
from __future__ import annotations

import asyncio
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Footer, Header

from treehouse.core.models import AgentWorkspace
from treehouse.tui.agent_table import AgentTable
from treehouse.tui.log_viewer import LogViewer


class TreehouseApp(App):
    CSS = """
    AgentTable {
        height: 40%;
        border: solid green;
    }
    LogViewer {
        height: 55%;
        border: solid cyan;
    }
    """

    BINDINGS = [
        ("s", "spawn", "Spawn"),
        ("m", "merge", "Merge"),
        ("k", "kill", "Kill"),
        ("d", "destroy_agent", "Destroy"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, workspaces: dict[str, AgentWorkspace] | None = None):
        super().__init__()
        self.workspaces = workspaces or {}

    def compose(self) -> ComposeResult:
        yield Header(name="Treehouse")
        with Vertical():
            yield AgentTable(self.workspaces)
            yield LogViewer()
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(1.0, self.refresh_data)

    def refresh_data(self) -> None:
        table = self.query_one(AgentTable)
        table.update_data(self.workspaces)
        selected = table.selected_agent
        if selected and selected in self.workspaces:
            viewer = self.query_one(LogViewer)
            viewer.update_logs(self.workspaces[selected].log_buffer)

    def action_spawn(self) -> None:
        from treehouse.tui.dialogs import SpawnDialog
        self.push_screen(SpawnDialog(), self._on_spawn_result)

    def _on_spawn_result(self, result: tuple[str, str] | None) -> None:
        if result is None:
            return
        name, task = result
        self.notify(f"Spawning agent '{name}'...")
        from treehouse.core.worktree import WorktreeManager
        from treehouse.core.ports import PortAllocator
        from treehouse.core.models import AgentWorkspace
        from treehouse.core.agent import AgentRunner
        from treehouse.config import TreehouseConfig

        config = TreehouseConfig.load(Path.cwd())
        wt_mgr = WorktreeManager(config.root)
        allocator = PortAllocator(config.base_port)

        wt_path = wt_mgr.create(name)
        port_base = allocator.allocate()
        ws = AgentWorkspace(
            name=name, task_prompt=task,
            worktree_path=wt_path, port_base=port_base,
        )
        self.workspaces[name] = ws

        runner = AgentRunner()
        self.run_worker(self._run_agent(runner, ws))

    async def _run_agent(self, runner, workspace):
        await runner.start(workspace)
        await asyncio.gather(
            runner.stream_output(workspace),
            runner.wait(workspace),
        )

    def action_merge(self) -> None:
        table = self.query_one(AgentTable)
        if table.selected_agent:
            self.notify(f"Merging {table.selected_agent}...")

    def action_kill(self) -> None:
        table = self.query_one(AgentTable)
        if table.selected_agent:
            self.notify(f"Killing {table.selected_agent}...")

    def action_destroy_agent(self) -> None:
        table = self.query_one(AgentTable)
        if table.selected_agent:
            self.notify(f"Destroying {table.selected_agent}...")
```

```python
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
```

```python
# treehouse/tui/log_viewer.py
from __future__ import annotations

from collections import deque

from textual.widgets import RichLog
from textual.widget import Widget


class LogViewer(Widget):
    def compose(self):
        yield RichLog(id="log-output", wrap=True, highlight=True, markup=True)

    def update_logs(self, log_buffer: deque[str]) -> None:
        log = self.query_one(RichLog)
        current_count = getattr(self, "_last_count", 0)
        new_lines = list(log_buffer)[current_count:]
        for line in new_lines:
            log.write(line)
        self._last_count = len(log_buffer)
```

**Step 2: Verify dashboard launches**

Run: `treehouse dashboard`
Expected: TUI opens with empty agent table

**Step 3: Commit**

```bash
git add treehouse/tui/app.py treehouse/tui/agent_table.py treehouse/tui/log_viewer.py
git commit -m "feat: add TUI dashboard"
```

---

### Task 12: TUI Spawn Dialog

**Files:**
- Create: `treehouse/tui/dialogs.py`

**Step 1: Create the spawn dialog**

```python
# treehouse/tui/dialogs.py
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label


class SpawnDialog(ModalScreen[tuple[str, str] | None]):
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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "spawn-btn":
            name = self.query_one("#agent-name", Input).value
            task = self.query_one("#agent-task", Input).value
            if name and task:
                self.dismiss((name, task))
        else:
            self.dismiss(None)
```

**Step 2: Verify dialog works**

Run: `treehouse dashboard`, press `s`
Expected: Modal dialog appears

**Step 3: Commit**

```bash
git add treehouse/tui/dialogs.py
git commit -m "feat: add spawn dialog to TUI"
```

---

### Task 13: Integration Test

**Files:**
- Create: `tests/test_integration.py`

**Step 1: Write the integration test**

```python
# tests/test_integration.py
import subprocess
from pathlib import Path
import pytest
from treehouse.config import TreehouseConfig
from treehouse.core.worktree import WorktreeManager
from treehouse.core.ports import PortAllocator
from treehouse.core.env import rewrite_env
from treehouse.core.models import AgentWorkspace, AgentStatus


@pytest.fixture
def initialized_repo(tmp_path):
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    (tmp_path / "README.md").write_text("# Test Project")
    (tmp_path / ".env").write_text("PORT=3000\nDATABASE_URL=postgres://localhost:5432/app\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "init"], check=True, capture_output=True)
    TreehouseConfig.init(tmp_path)
    return tmp_path


def test_full_spawn_cycle(initialized_repo):
    root = initialized_repo
    config = TreehouseConfig.load(root)
    wt_mgr = WorktreeManager(root)
    allocator = PortAllocator(config.base_port)

    wt_path = wt_mgr.create("agent-1")
    port_base = allocator.allocate()

    ws = AgentWorkspace(
        name="agent-1", task_prompt="test task",
        worktree_path=wt_path, port_base=port_base,
    )

    assert wt_path.exists()
    assert (wt_path / "README.md").exists()
    assert ws.branch == "treehouse/agent-1"
    assert ws.status == AgentStatus.PENDING
    assert port_base == 3101

    port_mapping = allocator.get_port_mapping(port_base, {"app": 3000, "db": 5432})
    rewrite_env(root / ".env", wt_path / ".env", port_mapping)
    env_content = (wt_path / ".env").read_text()
    assert "3101" in env_content
    assert "5501" in env_content

    wt_mgr.destroy("agent-1")
    assert not wt_path.exists()


def test_multi_agent_no_port_collision(initialized_repo):
    root = initialized_repo
    allocator = PortAllocator(3100)
    wt_mgr = WorktreeManager(root)

    ports = []
    for i in range(5):
        wt_mgr.create(f"agent-{i}")
        ports.append(allocator.allocate())

    assert len(set(ports)) == 5

    for i in range(5):
        wt_mgr.destroy(f"agent-{i}")
```

**Step 2: Run integration tests**

Run: `pytest tests/test_integration.py -v`
Expected: 2 passed

**Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration tests for full spawn cycle"
```

---

### Task 14: README and .gitignore

**Files:**
- Create: `README.md`
- Create: `.gitignore`

**Step 1: Create .gitignore**

```
__pycache__/
*.egg-info/
dist/
.treehouse/
.venv/
*.pyc
```

**Step 2: Create README**

```markdown
# Treehouse

Parallel runtime isolation for multi-agent coding.

Treehouse spawns fully isolated workspaces for AI coding agents — each gets its own git worktree, Docker Compose project, database, ports, and environment. A live TUI dashboard monitors all agents and merges results back with AI-assisted conflict resolution.

## Quick Start

pip install -e .
cd your-project
treehouse init
treehouse spawn auth-fix "fix the login bug"
treehouse spawn ui-hero "redesign the hero section"
treehouse dashboard

## Commands

| Command | Description |
|---------|-------------|
| `treehouse init` | Initialize in current repo |
| `treehouse spawn <name> "<task>"` | Create workspace + launch agent |
| `treehouse list` | List all agents and status |
| `treehouse stop <name>` | Stop a running agent |
| `treehouse merge <name>` | Merge agent's branch back |
| `treehouse destroy <name>` | Tear down workspace + containers |
| `treehouse dashboard` | Launch the TUI dashboard |
```

**Step 3: Commit**

```bash
git add README.md .gitignore
git commit -m "docs: add README and gitignore"
```
