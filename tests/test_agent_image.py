# tests/test_agent_image.py
import os
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml

from treehouse.core.agent_image import (
    AGENT_IMAGE_TAG,
    agent_service,
    ensure_agent_image,
)


def _completed(returncode: int, stdout: bytes = b"", stderr: bytes = b""):
    proc = MagicMock(spec=subprocess.CompletedProcess)
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


def test_ensure_agent_image_skips_build_when_image_exists():
    with patch("treehouse.core.agent_image.subprocess.run") as run:
        run.return_value = _completed(0)  # inspect found image
        tag = ensure_agent_image("custom:tag")
    assert tag == "custom:tag"
    # Only the inspect call, no build
    assert run.call_count == 1
    cmd = run.call_args_list[0].args[0]
    assert cmd[:3] == ["docker", "image", "inspect"]


def test_ensure_agent_image_builds_when_missing():
    with patch("treehouse.core.agent_image.subprocess.run") as run:
        run.side_effect = [
            _completed(1),  # inspect: not found
            _completed(0),  # build: success
        ]
        tag = ensure_agent_image()
    assert tag == AGENT_IMAGE_TAG
    assert run.call_count == 2
    build_cmd = run.call_args_list[1].args[0]
    assert build_cmd[:2] == ["docker", "build"]
    assert "-t" in build_cmd
    # Dockerfile fed via stdin
    assert "input" in run.call_args_list[1].kwargs


def test_ensure_agent_image_raises_on_build_failure():
    with patch("treehouse.core.agent_image.subprocess.run") as run:
        run.side_effect = [
            _completed(1),  # inspect: not found
            _completed(1, stderr=b"boom"),  # build: fail
        ]
        with pytest.raises(RuntimeError, match="Failed to build agent image"):
            ensure_agent_image()


def test_agent_service_has_required_fields():
    svc = agent_service("write hello to README")
    assert svc["working_dir"] == "/workspace"
    assert ".:/workspace" in svc["volumes"]
    assert svc["command"][0] == "claude"
    assert svc["command"][-1] == "write hello to README"
    # Auth pass-through is by reference, not value: the key never enters
    # the compose file as a literal, only as a name to inherit from host.
    assert "ANTHROPIC_API_KEY" in svc["environment"]
    assert svc["restart"] == "no"


def test_agent_service_yaml_round_trips_with_unusual_prompt():
    """Prompts with quotes, newlines, and shell metacharacters must survive
    serialization without becoming a quoting hazard or running through a
    shell."""
    prompt = 'fix the "main" function;\nrm -rf / # bad'
    svc = agent_service(prompt)
    rendered = yaml.safe_dump(svc)
    parsed = yaml.safe_load(rendered)
    # command is a list, so the args go directly to docker exec without
    # passing through a shell — the prompt round-trips intact.
    assert parsed["command"][-1] == prompt


def test_agent_service_mounts_claude_dir_when_present(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    (fake_home / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(fake_home))
    svc = agent_service("noop")
    mounts = [v for v in svc["volumes"] if "/root/.claude" in v]
    assert mounts and mounts[0].endswith(":/root/.claude:ro")


def test_agent_service_skips_claude_mount_when_absent(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "no-claude-here"))
    svc = agent_service("noop")
    assert not any("/root/.claude" in v for v in svc["volumes"])
