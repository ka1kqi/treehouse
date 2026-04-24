# tests/test_docker.py
from pathlib import Path
import yaml
from treehouse.core.docker import DockerManager


def test_generate_compose_file(tmp_path):
    source = tmp_path / "docker-compose.yml"
    source.write_text(yaml.dump({
        "services": {
            "app": {"build": ".", "ports": ["3000:3000"]},
            "db": {"image": "postgres:16", "ports": ["5432:5432"]},
        }
    }))
    mgr = DockerManager(source)
    port_mapping = {
        "app": {"host": 3101, "container": 3000},
        "db": {"host": 5501, "container": 5432},
    }
    output = tmp_path / "worktree" / "docker-compose.treehouse.yml"
    output.parent.mkdir()
    mgr.generate(output, "treehouse_auth_fix", port_mapping)

    result = yaml.safe_load(output.read_text())
    assert result["services"]["app"]["ports"] == ["3101:3000"]
    assert result["services"]["db"]["ports"] == ["5501:5432"]


def test_command_formation(tmp_path):
    source = tmp_path / "docker-compose.yml"
    source.write_text(yaml.dump({"services": {"app": {"image": "nginx"}}}))
    mgr = DockerManager(source)
    cmd = mgr._up_command(tmp_path / "compose.yml", "test_project")
    assert "docker" in cmd[0]
    assert "-p" in cmd
    assert "test_project" in cmd
