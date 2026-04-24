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
