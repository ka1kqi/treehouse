# tests/test_orchestrate_merge.py
import asyncio
import subprocess
from pathlib import Path

import pytest

from treehouse.cli import _merge_spawned
from treehouse.core.merger import MergeManager
from treehouse.core.models import AgentStatus, AgentWorkspace


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True
    )


@pytest.fixture
def repo_with_two_branches(tmp_path):
    """Repo on main with two non-conflicting treehouse branches."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    _git(repo, "checkout", "-b", "main")
    (repo / "main.txt").write_text("main")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "init")

    _git(repo, "checkout", "-b", "treehouse/agent-a")
    (repo / "a.txt").write_text("from a")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "agent a")

    _git(repo, "checkout", "main")
    _git(repo, "checkout", "-b", "treehouse/agent-b")
    (repo / "b.txt").write_text("from b")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "agent b")
    _git(repo, "checkout", "main")

    return repo


def _ws(name: str, status: AgentStatus, tmp_path: Path) -> AgentWorkspace:
    return AgentWorkspace(
        name=name,
        task_prompt=f"do {name}",
        worktree_path=tmp_path / f"wt-{name}",
        port_base=4100,
        status=status,
    )


def test_merge_spawned_merges_done_agents(repo_with_two_branches, tmp_path):
    repo = repo_with_two_branches
    ws_a = _ws("agent-a", AgentStatus.DONE, tmp_path)
    ws_b = _ws("agent-b", AgentStatus.DONE, tmp_path)
    mgr = MergeManager(repo)
    save_calls = []

    merged = asyncio.run(
        _merge_spawned(mgr, [ws_a, ws_b], lambda: save_calls.append(1))
    )

    assert merged == 2
    assert ws_a.status == AgentStatus.MERGED
    assert ws_b.status == AgentStatus.MERGED
    # Both branches' files are present on main
    assert (repo / "a.txt").exists()
    assert (repo / "b.txt").exists()
    # Persistence callback fired once per successful merge
    assert len(save_calls) == 2


def test_merge_spawned_skips_failed_agents(repo_with_two_branches, tmp_path):
    repo = repo_with_two_branches
    ws_a = _ws("agent-a", AgentStatus.FAILED, tmp_path)
    ws_b = _ws("agent-b", AgentStatus.DONE, tmp_path)
    mgr = MergeManager(repo)

    merged = asyncio.run(
        _merge_spawned(mgr, [ws_a, ws_b], lambda: None)
    )

    assert merged == 1
    assert ws_a.status == AgentStatus.FAILED  # untouched
    assert ws_b.status == AgentStatus.MERGED
    assert not (repo / "a.txt").exists()
    assert (repo / "b.txt").exists()


def test_merge_spawned_handles_empty_list(repo_with_two_branches):
    repo = repo_with_two_branches
    mgr = MergeManager(repo)
    merged = asyncio.run(_merge_spawned(mgr, [], lambda: None))
    assert merged == 0
