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
