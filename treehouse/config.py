from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import yaml

CONFIG_DIR = ".treehouse"
CONFIG_FILE = "config.yml"


@dataclass
class TreehouseConfig:
    root: Path
    base_port: int = 3100
    compose_file: str = ""
    env_file: str = ".env"

    @classmethod
    def init(cls, root: Path) -> TreehouseConfig:
        cfg_dir = root / CONFIG_DIR
        cfg_dir.mkdir(parents=True, exist_ok=True)

        compose_file = ""
        for name in ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]:
            if (root / name).exists():
                compose_file = name
                break

        config = cls(root=root, compose_file=compose_file)
        config.save()
        return config

    @classmethod
    def load(cls, root: Path) -> TreehouseConfig:
        cfg_path = root / CONFIG_DIR / CONFIG_FILE
        if not cfg_path.exists():
            raise FileNotFoundError(f"No treehouse config at {cfg_path}. Run 'treehouse init' first.")
        with open(cfg_path) as f:
            data = yaml.safe_load(f) or {}
        return cls(
            root=root,
            base_port=data.get("base_port", 3100),
            compose_file=data.get("compose_file", ""),
            env_file=data.get("env_file", ".env"),
        )

    def save(self) -> None:
        cfg_path = self.root / CONFIG_DIR / CONFIG_FILE
        with open(cfg_path, "w") as f:
            yaml.dump({
                "base_port": self.base_port,
                "compose_file": self.compose_file,
                "env_file": self.env_file,
            }, f)
