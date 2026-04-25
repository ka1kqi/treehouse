# tests/test_commit_workspace.py
import subprocess
from pathlib import Path

import pytest

from treehouse.core.agent import commit_workspace_if_dirty
from treehouse.core.models import AgentStatus, AgentWorkspace


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, check=True,
    )


@pytest.fixture
def fresh_worktree(tmp_path):
    """A bare git repo at tmp_path/repo plus a worktree at tmp_path/wt
    with no committer identity, simulating a freshly-spawned agent worktree.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "main.txt").write_text("seed")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "init")

    wt = tmp_path / "wt"
    _git(repo, "worktree", "add", "-q", "-b", "treehouse/agent", str(wt))
    return wt


def _ws(name: str, status: AgentStatus, wt_path: Path) -> AgentWorkspace:
    return AgentWorkspace(
        name=name,
        task_prompt="trivial",
        worktree_path=wt_path,
        port_base=4100,
        status=status,
    )


def test_commits_dirty_done_workspace(fresh_worktree):
    (fresh_worktree / "OUT.txt").write_text("agent wrote this")
    ws = _ws("agent", AgentStatus.DONE, fresh_worktree)
    assert commit_workspace_if_dirty(ws) is True
    log = _git(fresh_worktree, "log", "--oneline").stdout.splitlines()
    assert len(log) == 2  # init + agent commit
    assert "agent(agent)" in log[0]


def test_skips_failed_workspace(fresh_worktree):
    (fresh_worktree / "PARTIAL.txt").write_text("incomplete")
    ws = _ws("agent", AgentStatus.FAILED, fresh_worktree)
    assert commit_workspace_if_dirty(ws) is False
    # Files remain unstaged for human inspection
    assert (fresh_worktree / "PARTIAL.txt").exists()
    log = _git(fresh_worktree, "log", "--oneline").stdout.splitlines()
    assert len(log) == 1


def test_noop_when_clean(fresh_worktree):
    ws = _ws("agent", AgentStatus.DONE, fresh_worktree)
    assert commit_workspace_if_dirty(ws) is False
    log = _git(fresh_worktree, "log", "--oneline").stdout.splitlines()
    assert len(log) == 1


def test_includes_untracked_files(fresh_worktree):
    """The agent often creates new files. -A must include them, not just
    modifications to tracked files."""
    (fresh_worktree / "NEW.txt").write_text("brand new")
    ws = _ws("agent", AgentStatus.DONE, fresh_worktree)
    assert commit_workspace_if_dirty(ws) is True
    show = _git(fresh_worktree, "show", "HEAD", "--name-only").stdout
    assert "NEW.txt" in show


def test_excludes_treehouse_generated_artifacts(fresh_worktree):
    """docker-compose.treehouse.yml and .env are written by treehouse itself,
    not the agent. They must not ride along on the merge."""
    (fresh_worktree / "docker-compose.treehouse.yml").write_text("services: {}")
    (fresh_worktree / ".env").write_text("PORT=3101")
    (fresh_worktree / "REAL_WORK.txt").write_text("agent's actual output")
    ws = _ws("agent", AgentStatus.DONE, fresh_worktree)
    assert commit_workspace_if_dirty(ws) is True
    show = _git(fresh_worktree, "show", "HEAD", "--name-only").stdout
    assert "REAL_WORK.txt" in show
    assert "docker-compose.treehouse.yml" not in show
    assert ".env" not in show


def test_no_commit_when_only_excluded_files_dirty(fresh_worktree):
    """If the agent didn't change anything except treehouse-generated files,
    don't create an empty commit."""
    (fresh_worktree / "docker-compose.treehouse.yml").write_text("services: {}")
    (fresh_worktree / ".env").write_text("PORT=3101")
    ws = _ws("agent", AgentStatus.DONE, fresh_worktree)
    assert commit_workspace_if_dirty(ws) is False
    log = _git(fresh_worktree, "log", "--oneline").stdout.splitlines()
    assert len(log) == 1


def test_truncates_long_prompts_in_message(fresh_worktree):
    (fresh_worktree / "x.txt").write_text("y")
    ws = _ws("agent", AgentStatus.DONE, fresh_worktree)
    ws.task_prompt = "A" * 500
    assert commit_workspace_if_dirty(ws) is True
    msg = _git(fresh_worktree, "log", "-1", "--format=%s").stdout.strip()
    # 72-char body cap + "agent(agent): " prefix
    assert msg.startswith("agent(agent): ")
    assert len(msg) <= len("agent(agent): ") + 72
