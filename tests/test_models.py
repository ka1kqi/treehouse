from treehouse.core.models import AgentStatus, AgentWorkspace
from pathlib import Path


def test_agent_status_values():
    assert AgentStatus.PENDING.value == "pending"
    assert AgentStatus.RUNNING.value == "running"
    assert AgentStatus.DONE.value == "done"
    assert AgentStatus.FAILED.value == "failed"
    assert AgentStatus.MERGING.value == "merging"
    assert AgentStatus.MERGED.value == "merged"


def test_agent_workspace_creation():
    ws = AgentWorkspace(
        name="auth-fix",
        task_prompt="fix the login bug",
        worktree_path=Path("/tmp/treehouse/auth-fix"),
        port_base=3101,
    )
    assert ws.name == "auth-fix"
    assert ws.branch == "treehouse/auth-fix"
    assert ws.compose_project == "treehouse_auth_fix"
    assert ws.status == AgentStatus.PENDING
    assert ws.process is None
    assert len(ws.log_buffer) == 0
