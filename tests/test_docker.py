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


def test_docker_manager_injects_agent_when_task_provided(tmp_path):
    source = tmp_path / "docker-compose.yml"
    source.write_text(yaml.dump({"services": {"app": {"image": "nginx", "ports": ["3000:3000"]}}}))
    mgr = DockerManager(source)
    output = tmp_path / "out" / "docker-compose.treehouse.yml"
    mgr.generate(
        output,
        "test_project",
        {"app": {"host": 3101, "container": 3000}},
        agent_task="add a healthcheck",
    )
    result = yaml.safe_load(output.read_text())
    assert "agent" in result["services"]
    assert result["services"]["agent"]["command"][-1] == "add a healthcheck"
    # User's app service is untouched
    assert result["services"]["app"]["ports"] == ["3101:3000"]


def test_docker_manager_omits_agent_when_no_task(tmp_path):
    source = tmp_path / "docker-compose.yml"
    source.write_text(yaml.dump({"services": {"app": {"image": "nginx"}}}))
    mgr = DockerManager(source)
    output = tmp_path / "out" / "docker-compose.treehouse.yml"
    mgr.generate(output, "test_project", {})
    result = yaml.safe_load(output.read_text())
    assert "agent" not in result.get("services", {})


def test_compose_generator_injects_agent_when_task_provided(tmp_path):
    from treehouse.core.docker import ComposeGenerator
    # Empty project root → falls into the generic ubuntu fallback
    project_root = tmp_path / "proj"
    project_root.mkdir()
    output = tmp_path / "compose.yml"
    gen = ComposeGenerator()
    gen.generate(project_root, output, agent_task="ship it")
    result = yaml.safe_load(output.read_text())
    assert "agent" in result["services"]
    assert result["services"]["agent"]["command"][-1] == "ship it"
