# treehouse/core/agent_image.py
from __future__ import annotations

import os
import subprocess
from pathlib import Path

AGENT_IMAGE_TAG = "treehouse-agent:0.1"

# Inline Dockerfile so the package self-contains the build context.
# node:20-alpine is small (~50MB), git lets the agent commit, claude-code is
# the Claude Code CLI the agent invokes.
_DOCKERFILE = b"""\
FROM node:20-alpine
RUN apk add --no-cache git ca-certificates curl bash && \\
    npm install -g @anthropic-ai/claude-code
WORKDIR /workspace
"""


def ensure_agent_image(tag: str = AGENT_IMAGE_TAG) -> str:
    """Build the agent image if it doesn't already exist locally. Idempotent.

    Returns the image tag. Raises RuntimeError on build failure.
    """
    inspect = subprocess.run(
        ["docker", "image", "inspect", tag],
        capture_output=True,
    )
    if inspect.returncode == 0:
        return tag

    build = subprocess.run(
        ["docker", "build", "-t", tag, "-"],
        input=_DOCKERFILE,
        capture_output=True,
    )
    if build.returncode != 0:
        stderr = build.stderr.decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"Failed to build agent image '{tag}':\n{stderr}")
    return tag


def agent_service(task_prompt: str, image: str = AGENT_IMAGE_TAG) -> dict:
    """Compose service definition for a Claude Code agent.

    Mounts the worktree at /workspace, passes through ANTHROPIC_API_KEY +
    CLAUDE_API_KEY from the host, and conditionally bind-mounts the host's
    ~/.claude (read-only) so OAuth-based auth works without a separate API key.
    Either credential path satisfies the CLI; whichever the user has set up
    will succeed at runtime.
    """
    volumes = [".:/workspace"]
    claude_dir = os.path.expanduser("~/.claude")
    if os.path.isdir(claude_dir):
        volumes.append(f"{claude_dir}:/root/.claude:ro")

    return {
        "image": image,
        "working_dir": "/workspace",
        "volumes": volumes,
        # List form: pass values through from the host's environment.
        # Compose treats undefined vars as empty (which the CLI will reject
        # with a clear "no credentials" error — desired behavior).
        "environment": [
            "ANTHROPIC_API_KEY",
            "CLAUDE_API_KEY",
            "ANTHROPIC_BASE_URL",
        ],
        "command": [
            "claude",
            "-p",
            "--output-format",
            "stream-json",
            "--verbose",
            "--permission-mode",
            "bypassPermissions",
            task_prompt,
        ],
        # Run once; don't restart on agent exit.
        "restart": "no",
    }
