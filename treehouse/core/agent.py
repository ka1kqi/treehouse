# treehouse/core/agent.py
from __future__ import annotations

import asyncio
import json
import subprocess

from treehouse.core.models import AgentStatus, AgentWorkspace


def commit_workspace_if_dirty(workspace: AgentWorkspace) -> bool:
    """Stage and commit any changes the agent left uncommitted in its worktree.

    Without this, agents that edit files but skip `git commit` produce empty
    branches — `treehouse merge` is then a silent no-op and the work is lost.

    Only commits on AgentStatus.DONE so partial state from FAILED runs stays
    visible for inspection. Configures a local agent identity if neither the
    worktree nor the user's global git config has user.email set, so the
    commit doesn't fail with "Author identity unknown".

    Returns True if a commit was made.
    """
    if workspace.status != AgentStatus.DONE:
        return False

    wt = str(workspace.worktree_path)
    status = subprocess.run(
        ["git", "-C", wt, "status", "--porcelain"],
        capture_output=True, text=True,
    )
    if not status.stdout.strip():
        return False  # nothing to commit

    # Ensure committer identity exists (worktree-local, doesn't touch global config).
    email = subprocess.run(
        ["git", "-C", wt, "config", "user.email"],
        capture_output=True, text=True,
    )
    if email.returncode != 0 or not email.stdout.strip():
        subprocess.run(
            ["git", "-C", wt, "config", "user.email", "agent@treehouse"],
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", wt, "config", "user.name", f"treehouse/{workspace.name}"],
            capture_output=True,
        )

    # Treehouse-generated artifacts in the worktree must not ride into the
    # merged branch: docker-compose.treehouse.yml is per-workspace boilerplate
    # and .env was rewritten with this agent's port mappings (not the user's
    # canonical .env content).
    subprocess.run(
        ["git", "-C", wt, "add", "-A", "--",
         ".",
         ":(exclude)docker-compose.treehouse.yml",
         ":(exclude).env"],
        capture_output=True,
    )
    # If only excluded files were dirty, the staging area is now empty —
    # nothing meaningful to commit.
    diff_cached = subprocess.run(
        ["git", "-C", wt, "diff", "--cached", "--quiet"],
        capture_output=True,
    )
    if diff_cached.returncode == 0:
        return False

    summary = workspace.task_prompt.strip().replace("\n", " ")[:72]
    msg = f"agent({workspace.name}): {summary}"
    commit = subprocess.run(
        ["git", "-C", wt, "commit", "-m", msg],
        capture_output=True, text=True,
    )
    return commit.returncode == 0


DECOMPOSE_PROMPT = """\
You are a task decomposer. Given a high-level task, split it into 2-5 independent subtasks \
that can be worked on in parallel by separate coding agents. Each subtask should be \
self-contained and not depend on the others. Keep subtask names short (lowercase, hyphens). \
Include enough detail in each task description for an agent to work autonomously.

Project file tree:
{file_tree}

High-level task: {task}
"""

DECOMPOSE_SCHEMA = json.dumps({
    "type": "object",
    "properties": {
        "subtasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "task": {"type": "string"},
                },
                "required": ["name", "task"],
            },
        },
    },
    "required": ["subtasks"],
})


class AgentRunner:
    def __init__(self, containerized: bool = True) -> None:
        # Containerized: agent runs inside the per-workspace `agent` compose
        # service; output streamed via `docker logs -f`. Host: agent runs as
        # a direct subprocess on the host with cwd=worktree_path. Default
        # containerized for blast-radius isolation.
        self.containerized = containerized

    def build_command(self, workspace: AgentWorkspace) -> list[str]:
        return [
            "claude",
            "-p",
            "--output-format", "stream-json",
            "--verbose",
            "--permission-mode", "bypassPermissions",
            workspace.task_prompt,
        ]

    def parse_output_line(self, line: str, workspace: AgentWorkspace | None = None) -> str | None:
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
            # Assistant text content goes to the output buffer
            if workspace and subtype != "tool_use" and subtype != "tool_result":
                workspace.output_buffer.append(content)
            return content[:120]
        return None

    async def decompose_task(self, task: str, project_root: str = ".") -> list[tuple[str, str]]:
        import os
        import subprocess as _sp
        # Get a compact file tree for context
        try:
            tree_result = _sp.run(
                ["find", ".", "-maxdepth", "3", "-not", "-path", "./.git/*", "-not", "-path", "./node_modules/*"],
                capture_output=True, text=True, cwd=project_root, timeout=10,
            )
            file_tree = tree_result.stdout[:3000]
        except Exception:
            file_tree = "(unavailable)"

        prompt = DECOMPOSE_PROMPT.format(file_tree=file_tree, task=task)
        cmd = [
            "claude", "-p",
            "--output-format", "json",
            "--json-schema", DECOMPOSE_SCHEMA,
            prompt,
        ]
        env = os.environ.copy()
        env.pop("CLAUDECODE", None)
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=project_root,
            env=env,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"Decomposition failed: {stderr.decode()[:500]}")
        data = json.loads(stdout.decode())
        result = data.get("result", data)
        if isinstance(result, str):
            result = json.loads(result)
        subtasks = result.get("subtasks", [])
        return [(f"orch-{i+1}-{st['name']}", st["task"]) for i, st in enumerate(subtasks)]

    async def start(self, workspace: AgentWorkspace) -> None:
        if self.containerized:
            await self._start_container(workspace)
        else:
            await self._start_host(workspace)

    async def _start_host(self, workspace: AgentWorkspace) -> None:
        import os
        cmd = self.build_command(workspace)
        env = os.environ.copy()
        env.pop("CLAUDECODE", None)  # allow nested claude sessions
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(workspace.worktree_path),
            env=env,
            limit=1024 * 1024,  # 1MB line buffer for large stream-json output
        )
        workspace.process = process
        workspace.status = AgentStatus.RUNNING

    async def _start_container(self, workspace: AgentWorkspace) -> None:
        compose_file = workspace.worktree_path / "docker-compose.treehouse.yml"
        if not compose_file.exists():
            raise RuntimeError(
                f"compose file missing for workspace '{workspace.name}': {compose_file}"
            )

        # The agent service was brought up with the rest of compose
        # (`docker compose up -d`). Look up its container id.
        ps = await asyncio.create_subprocess_exec(
            "docker", "compose",
            "-f", str(compose_file),
            "-p", workspace.compose_project,
            "ps", "-q", "agent",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await ps.communicate()
        container_id = stdout.decode().strip().split("\n")[0]
        if not container_id:
            err = stderr.decode("utf-8", errors="replace")[:300]
            raise RuntimeError(
                f"agent container not found for '{workspace.name}': {err}"
            )
        workspace.container_id = container_id

        # `docker logs -f` blocks until the container exits and gives us the
        # stream-json output unmolested (no `agent_1 |` prefix).
        process = await asyncio.create_subprocess_exec(
            "docker", "logs", "-f", container_id,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=1024 * 1024,
        )
        workspace.process = process
        workspace.status = AgentStatus.RUNNING

    async def stream_output(self, workspace: AgentWorkspace) -> None:
        if not workspace.process:
            return

        async def _read_stream(stream, prefix=""):
            async for raw_line in stream:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if prefix:
                    if line:
                        workspace.log_buffer.append(f"{prefix}{line}")
                else:
                    parsed = self.parse_output_line(line, workspace)
                    if parsed:
                        workspace.log_buffer.append(parsed)

        tasks = []
        if workspace.process.stdout:
            tasks.append(_read_stream(workspace.process.stdout))
        if workspace.process.stderr:
            tasks.append(_read_stream(workspace.process.stderr, prefix="STDERR: "))
        if tasks:
            await asyncio.gather(*tasks)

    async def wait(self, workspace: AgentWorkspace) -> None:
        if not workspace.process:
            return
        returncode = await workspace.process.wait()
        if self.containerized and workspace.container_id:
            # `docker logs -f` exits 0 when the container exits, regardless of
            # the agent's actual exit status. Inspect the container for the
            # real code.
            inspect = await asyncio.create_subprocess_exec(
                "docker", "inspect",
                "-f", "{{.State.ExitCode}}",
                workspace.container_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await inspect.communicate()
            try:
                returncode = int(stdout.decode().strip())
            except ValueError:
                pass
        workspace.status = AgentStatus.DONE if returncode == 0 else AgentStatus.FAILED
        workspace.process = None

    async def stop(self, workspace: AgentWorkspace) -> None:
        if self.containerized and workspace.container_id:
            stop_proc = await asyncio.create_subprocess_exec(
                "docker", "stop", workspace.container_id,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await stop_proc.wait()
            if workspace.process:
                # `docker logs -f` will exit on its own once the container
                # stops; give it a moment then make sure it's gone.
                try:
                    await asyncio.wait_for(workspace.process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    workspace.process.terminate()
                    await workspace.process.wait()
        elif workspace.process:
            workspace.process.terminate()
            await workspace.process.wait()
        workspace.status = AgentStatus.FAILED
        workspace.process = None
