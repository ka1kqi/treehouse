from pathlib import Path
from treehouse.config import TreehouseConfig


def test_init_creates_config(tmp_path):
    config = TreehouseConfig.init(tmp_path)
    assert (tmp_path / ".treehouse" / "config.yml").exists()
    assert config.base_port == 3100


def test_load_existing_config(tmp_path):
    cfg_dir = tmp_path / ".treehouse"
    cfg_dir.mkdir()
    (cfg_dir / "config.yml").write_text("base_port: 4000\ncompose_file: docker-compose.dev.yml\n")
    config = TreehouseConfig.load(tmp_path)
    assert config.base_port == 4000
    assert config.compose_file == "docker-compose.dev.yml"


def test_detect_compose_file(tmp_path):
    (tmp_path / "docker-compose.yml").write_text("services: {}")
    config = TreehouseConfig.init(tmp_path)
    assert config.compose_file == "docker-compose.yml"
