# treehouse/core/env.py
from __future__ import annotations

import re
from pathlib import Path


def rewrite_env(
    source: Path | None, output: Path,
    port_mapping: dict[str, dict[str, int]],
) -> None:
    port_map: dict[int, int] = {}
    for service in port_mapping.values():
        port_map[service["container"]] = service["host"]

    lines: list[str] = []
    if source and source.exists():
        for line in source.read_text().splitlines():
            rewritten = line
            for container_port, host_port in port_map.items():
                rewritten = re.sub(
                    rf"(?<!\d){container_port}(?!\d)",
                    str(host_port), rewritten,
                )
            lines.append(rewritten)
    else:
        if "app" in port_mapping:
            lines.append(f"PORT={port_mapping['app']['host']}")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n")
