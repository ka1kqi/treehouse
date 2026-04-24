from treehouse.core.ports import PortAllocator


def test_allocate_sequential():
    alloc = PortAllocator(base_port=3100)
    assert alloc.allocate() == 3101
    assert alloc.allocate() == 3102
    assert alloc.allocate() == 3103


def test_release_and_reuse():
    alloc = PortAllocator(base_port=3100)
    p1 = alloc.allocate()
    p2 = alloc.allocate()
    alloc.release(p1)
    p3 = alloc.allocate()
    assert p3 == p1


def test_port_mapping():
    alloc = PortAllocator(base_port=3100)
    port_base = alloc.allocate()
    mapping = alloc.get_port_mapping(port_base, {"app": 3000, "db": 5432, "redis": 6379})
    assert mapping == {
        "app": {"host": 3101, "container": 3000},
        "db": {"host": 5501, "container": 5432},
        "redis": {"host": 6401, "container": 6379},
    }
