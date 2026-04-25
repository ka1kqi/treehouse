# treehouse/core/agent.py
from __future__ import annotations

import asyncio
import json

from treehouse.core.models import AgentStatus, AgentWorkspace


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
        workspace.status = AgentStatus.DONE if returncode == 0 else AgentStatus.FAILED
        workspace.process = None

    async def stop(self, workspace: AgentWorkspace) -> None:
        if workspace.process:
            workspace.process.terminate()
            await workspace.process.wait()
            workspace.status = AgentStatus.FAILED
            workspace.process = None
