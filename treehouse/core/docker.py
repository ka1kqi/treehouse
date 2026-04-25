# treehouse/core/docker.py
from __future__ import annotations

import subprocess
from pathlib import Path
import yaml

from treehouse.core.agent_image import agent_service


class ComposeGenerator:
    """Auto-detect project stack and generate a docker-compose.yml."""

    def _app_service(self, project_root: Path, image: str, port: int, cmd: str, extra_volumes: list[str] | None = None) -> dict:
        """Build an app service dict, using build if Dockerfile exists, else image."""
        svc = {}
        if (project_root / "Dockerfile").exists():
            svc["build"] = "."
        else:
            svc["image"] = image
        svc["ports"] = [f"{port}:{port}"]
        vols = [".:/app"]
        if extra_volumes:
            vols.extend(extra_volumes)
        svc["volumes"] = vols
        svc["working_dir"] = "/app"
        svc["command"] = cmd
        return svc

    def detect(self, project_root: Path) -> dict:
        services = {}
        port_defaults = {}

        # Node / Next.js / React
        pkg_json = project_root / "package.json"
        if pkg_json.exists():
            import json
            pkg = json.loads(pkg_json.read_text())
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

            if "next" in deps or any(k in deps for k in ("react-scripts", "vite", "vue")):
                services["app"] = self._app_service(project_root, "node:20-alpine", 3000, "npm run dev", ["/app/node_modules"])
            elif any(k in deps for k in ("express", "fastify", "koa", "hono")):
                services["app"] = self._app_service(project_root, "node:20-alpine", 3000, "npm start", ["/app/node_modules"])
            else:
                services["app"] = self._app_service(project_root, "node:20-alpine", 3000, "npm start", ["/app/node_modules"])
            port_defaults["app"] = 3000

            if any(k in deps for k in ("pg", "postgres", "prisma", "@prisma/client", "typeorm", "knex", "sequelize", "drizzle-orm")):
                services["db"] = {
                    "image": "postgres:16-alpine",
                    "ports": ["5432:5432"],
                    "environment": {"POSTGRES_USER": "treehouse", "POSTGRES_PASSWORD": "treehouse", "POSTGRES_DB": "app"},
                    "volumes": ["pgdata:/var/lib/postgresql/data"],
                }
                port_defaults["db"] = 5432

            if any(k in deps for k in ("redis", "ioredis", "bullmq", "@bull-board/api")):
                services["redis"] = {"image": "redis:7-alpine", "ports": ["6379:6379"]}
                port_defaults["redis"] = 6379

            if any(k in deps for k in ("mongodb", "mongoose", "mongosh")):
                services["mongo"] = {"image": "mongo:7", "ports": ["27017:27017"], "volumes": ["mongodata:/data/db"]}
                port_defaults["mongo"] = 27017

        # Python projects
        has_requirements = (project_root / "requirements.txt").exists()
        has_pyproject = (project_root / "pyproject.toml").exists()
        if (has_requirements or has_pyproject) and "app" not in services:
            deps_text = ""
            if has_requirements:
                deps_text = (project_root / "requirements.txt").read_text().lower()
            elif has_pyproject:
                deps_text = (project_root / "pyproject.toml").read_text().lower()

            port = 8000
            cmd = "python -m uvicorn main:app --host 0.0.0.0 --reload"
            if "django" in deps_text:
                cmd = "python manage.py runserver 0.0.0.0:8000"
            elif "flask" in deps_text:
                port = 5000
                cmd = "flask run --host=0.0.0.0"

            services["app"] = self._app_service(project_root, "python:3.12-slim", port, cmd)
            port_defaults["app"] = port

            if "psycopg" in deps_text or "sqlalchemy" in deps_text or "django" in deps_text:
                services["db"] = {
                    "image": "postgres:16-alpine",
                    "ports": ["5432:5432"],
                    "environment": {"POSTGRES_USER": "treehouse", "POSTGRES_PASSWORD": "treehouse", "POSTGRES_DB": "app"},
                    "volumes": ["pgdata:/var/lib/postgresql/data"],
                }
                port_defaults["db"] = 5432

            if "redis" in deps_text or "celery" in deps_text:
                services["redis"] = {"image": "redis:7-alpine", "ports": ["6379:6379"]}
                port_defaults["redis"] = 6379

        # Go projects
        if (project_root / "go.mod").exists() and "app" not in services:
            services["app"] = self._app_service(project_root, "golang:1.22-alpine", 8080, "go run .")
            port_defaults["app"] = 8080

        # Rust projects
        if (project_root / "Cargo.toml").exists() and "app" not in services:
            services["app"] = self._app_service(project_root, "rust:1.77-slim", 8080, "cargo run")
            port_defaults["app"] = 8080

        # Fallback: generic dev container
        if not services:
            services["app"] = {
                "image": "ubuntu:22.04",
                "volumes": [".:/workspace"],
                "working_dir": "/workspace",
                "command": "sleep infinity",
                "tty": True,
            }

        compose = {"services": services}
        volumes = {}
        for svc in services.values():
            for v in svc.get("volumes", []):
                if ":" in v and not v.startswith(".") and not v.startswith("/"):
                    volumes[v.split(":")[0]] = None
        if volumes:
            compose["volumes"] = volumes

        return compose, port_defaults

    def generate(
        self,
        project_root: Path,
        output_path: Path,
        agent_task: str | None = None,
    ) -> dict[str, int]:
        compose, port_defaults = self.detect(project_root)
        if agent_task is not None:
            compose.setdefault("services", {})["agent"] = agent_service(agent_task)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            yaml.dump(compose, f, default_flow_style=False)
        return port_defaults


class DockerManager:
    def __init__(self, source_compose: Path):
        self.source_compose = source_compose

    def generate(
        self, output_path: Path, project_name: str,
        port_mapping: dict[str, dict[str, int]],
        agent_task: str | None = None,
    ) -> None:
        with open(self.source_compose) as f:
            compose = yaml.safe_load(f)

        for service_name, ports in port_mapping.items():
            if service_name in compose.get("services", {}):
                compose["services"][service_name]["ports"] = [
                    f"{ports['host']}:{ports['container']}"
                ]

        if agent_task is not None:
            compose.setdefault("services", {})["agent"] = agent_service(agent_task)

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
