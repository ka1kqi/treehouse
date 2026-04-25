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
    npm install -g @anthropic-ai/claude-code && \\
    mkdir -p /home/agent && chmod 777 /home/agent
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

    The container runs as the host user's UID/GID so files written to the
    bind-mounted worktree end up owned by the host user (not root). claude
    refuses bypassPermissions when running as root, which is also why we
    must avoid the default UID 0.

    Auth: passes through ANTHROPIC_API_KEY/CLAUDE_API_KEY from the host's env
    (the API key never enters the compose file as a literal — only the
    variable name). When the host has OAuth credentials in mountable files
    (~/.claude.json + ~/.claude/), they're bind-mounted into the container's
    HOME so the CLI finds them. Mounted RW so token refreshes can write back.

    macOS caveat: Claude Code on macOS stores OAuth tokens in the system
    Keychain (`Claude Code-credentials`), not in ~/.claude.json. The keychain
    can't be bind-mounted, so OAuth-only macOS users must set
    ANTHROPIC_API_KEY explicitly to use container mode. On Linux, where the
    CLI stores tokens in ~/.claude.json, the bind mount is sufficient on
    its own.
    """
    volumes = [".:/workspace"]
    home = os.path.expanduser("~")
    claude_json = os.path.join(home, ".claude.json")
    claude_dir = os.path.join(home, ".claude")
    if os.path.isfile(claude_json):
        volumes.append(f"{claude_json}:/home/agent/.claude.json")
    if os.path.isdir(claude_dir):
        volumes.append(f"{claude_dir}:/home/agent/.claude")

    return {
        "image": image,
        # Bake host UID/GID into the compose file so files are owned correctly
        # under the bind mount. The compose file is per-workspace and not
        # committed, so machine-specific values are fine.
        "user": f"{os.getuid()}:{os.getgid()}",
        "working_dir": "/workspace",
        "volumes": volumes,
        # List entries with `KEY=value` set explicit values; bare `KEY` passes
        # through from the host's shell at compose-up time.
        "environment": [
            "HOME=/home/agent",
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
