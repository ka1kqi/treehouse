from __future__ import annotations


class PortAllocator:
    def __init__(self, base_port: int = 3100):
        self.base_port = base_port
        self._next = 1
        self._released: list[int] = []

    def allocate(self) -> int:
        if self._released:
            return self._released.pop(0)
        port = self.base_port + self._next
        self._next += 1
        return port

    def release(self, port: int) -> None:
        if port not in self._released:
            self._released.append(port)
            self._released.sort()

    def get_port_mapping(
        self, port_base: int, services: dict[str, int]
    ) -> dict[str, dict[str, int]]:
        offset = port_base - self.base_port
        range_bases = {
            range(3000, 4000): 3100,
            range(5000, 6000): 5500,
            range(6000, 7000): 6400,
            range(8000, 9000): 8100,
        }
        mapping = {}
        for name, container_port in services.items():
            host_base = self.base_port
            for port_range, base in range_bases.items():
                if container_port in port_range:
                    host_base = base
                    break
            mapping[name] = {
                "host": host_base + offset,
                "container": container_port,
            }
        return mapping
