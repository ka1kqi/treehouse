# tests/test_agent.py
from pathlib import Path
from treehouse.core.agent import AgentRunner
from treehouse.core.models import AgentWorkspace


def test_build_command():
    ws = AgentWorkspace(
        name="test", task_prompt="fix the bug",
        worktree_path=Path("/tmp/ws"), port_base=3101,
    )
    runner = AgentRunner()
    cmd = runner.build_command(ws)
    assert "claude" in cmd[0]
    assert "-p" in cmd
    assert "--output-format" in cmd
    assert "stream-json" in cmd
    assert "--verbose" in cmd
    assert "--permission-mode" in cmd
    assert "bypassPermissions" in cmd
    assert "fix the bug" in cmd


def test_parse_stream_json_tool_use():
    runner = AgentRunner()
    line = '{"type":"assistant","subtype":"tool_use","tool":"Edit","content":"editing file"}'
    parsed = runner.parse_output_line(line)
    assert parsed is not None
    assert "Edit" in parsed
