# treehouse/core/docker.py
from __future__ import annotations

import subprocess
from pathlib import Path
import yaml


class DockerManager:
    def __init__(self, source_compose: Path):
        self.source_compose = source_compose

    def generate(
        self, output_path: Path, project_name: str,
        port_mapping: dict[str, dict[str, int]],
    ) -> None:
        with open(self.source_compose) as f:
            compose = yaml.safe_load(f)

        for service_name, ports in port_mapping.items():
            if service_name in compose.get("services", {}):
                compose["services"][service_name]["ports"] = [
                    f"{ports['host']}:{ports['container']}"
                ]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            yaml.dump(compose, f, default_flow_style=False)

    def _up_command(self, compose_file: Path, project_name: str) -> list[str]:
        return ["docker", "compose", "-f", str(compose_file), "-p", project_name, "up", "-d"]

    def _down_command(self, compose_file: Path, project_name: str) -> list[str]:
        return ["docker", "compose", "-f", str(compose_file), "-p", project_name, "down", "-v"]

    def start(self, compose_file: Path, project_name: str) -> None:
        subprocess.run(self._up_command(compose_file, project_name), check=True, capture_output=True)

    def stop(self, compose_file: Path, project_name: str) -> None:
        subprocess.run(self._down_command(compose_file, project_name), check=True, capture_output=True)
