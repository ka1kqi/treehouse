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
