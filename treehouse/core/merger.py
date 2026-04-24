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
    """Manages git merge operations with AI-assisted conflict resolution."""

    def __init__(self, repo_root: Path) -> None:
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
