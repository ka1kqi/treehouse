# treehouse/core/worktree.py
from __future__ import annotations

import subprocess
from pathlib import Path

TREEHOUSE_DIR = ".treehouse"
WORKTREES_DIR = f"{TREEHOUSE_DIR}/worktrees"
TIMEOUT = 30


class WorktreeManager:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.worktrees_dir = repo_root / WORKTREES_DIR

    def create(self, name: str) -> Path:
        wt_path = self.worktrees_dir / name
        wt_path.parent.mkdir(parents=True, exist_ok=True)
        branch = f"treehouse/{name}"

        # Clean up stale worktree/branch from previous failed spawns
        if wt_path.exists():
            subprocess.run(
                ["git", "-C", str(self.repo_root), "worktree", "remove", str(wt_path), "--force"],
                capture_output=True, timeout=TIMEOUT,
            )
        subprocess.run(
            ["git", "-C", str(self.repo_root), "branch", "-D", branch],
            capture_output=True, timeout=TIMEOUT,
        )

        subprocess.run(
            ["git", "-C", str(self.repo_root), "worktree", "add", str(wt_path), "-b", branch],
            check=True, capture_output=True, timeout=TIMEOUT,
        )
        return wt_path

    def destroy(self, name: str) -> None:
        wt_path = self.worktrees_dir / name
        subprocess.run(
            ["git", "-C", str(self.repo_root), "worktree", "remove", str(wt_path), "--force"],
            check=True, capture_output=True, timeout=TIMEOUT,
        )
        branch = f"treehouse/{name}"
        subprocess.run(
            ["git", "-C", str(self.repo_root), "branch", "-D", branch],
            capture_output=True, timeout=TIMEOUT,
        )

    def list(self) -> list[str]:
        if not self.worktrees_dir.exists():
            return []
        return [d.name for d in self.worktrees_dir.iterdir() if d.is_dir()]
