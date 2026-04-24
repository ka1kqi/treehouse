# tests/test_env.py
from pathlib import Path
from treehouse.core.env import rewrite_env


def test_rewrite_env(tmp_path):
    source = tmp_path / ".env"
    source.write_text(
        "PORT=3000\n"
        "DATABASE_URL=postgres://localhost:5432/app\n"
        "REDIS_URL=redis://localhost:6379\n"
        "SECRET_KEY=abc123\n"
    )
    port_mapping = {
        "app": {"host": 3101, "container": 3000},
        "db": {"host": 5501, "container": 5432},
        "redis": {"host": 6401, "container": 6379},
    }
    output = tmp_path / "worktree" / ".env"
    output.parent.mkdir()
    rewrite_env(source, output, port_mapping)

    result = output.read_text()
    assert "PORT=3101" in result
    assert "5501" in result
    assert "6401" in result
    assert "SECRET_KEY=abc123" in result


def test_rewrite_env_no_source(tmp_path):
    output = tmp_path / ".env"
    port_mapping = {"app": {"host": 3101, "container": 3000}}
    rewrite_env(None, output, port_mapping)
    result = output.read_text()
    assert "PORT=3101" in result
