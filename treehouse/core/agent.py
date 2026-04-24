# treehouse/core/agent.py
from __future__ import annotations

import asyncio
import json

from treehouse.core.models import AgentStatus, AgentWorkspace


class AgentRunner:
    def build_command(self, workspace: AgentWorkspace) -> list[str]:
        return [
            "claude",
            "-p",
            "--output-format", "stream-json",
            "--verbose",
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
                    parsed = self.parse_output_line(line)
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
