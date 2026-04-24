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
