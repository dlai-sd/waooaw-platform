"""WC-109 cache namespace, locking, integrity, eviction and authority boundaries."""

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

from validation_control.cache_controller import CacheController, MANIFEST, cache_namespace


def test_cache_namespace_changes_with_each_identity_input() -> None:
    identity = {"runner": "sha256:runner", "lockfile": "sha256:lock", "architecture": "amd64"}

    namespaces = {cache_namespace({**identity, field: f"changed-{value}"}) for field, value in identity.items()}

    assert len(namespaces) == len(identity)
    assert cache_namespace(identity) not in namespaces


def test_concurrent_writers_are_serialized_and_retained_integrity_is_verified(tmp_path: Path) -> None:
    controller = CacheController(tmp_path, max_bytes=1024)
    namespace = cache_namespace({"runner": "python", "dependencies": "locked"})

    def increment() -> str:
        with controller.acquire(namespace) as lease:
            counter = lease.path / "counter"
            value = int(counter.read_text() if counter.is_file() else "0") + 1
            counter.write_text(str(value), encoding="utf-8")
            controller.seal(lease)
            return lease.state

    with ThreadPoolExecutor(max_workers=2) as executor:
        states = list(executor.map(lambda _: increment(), range(2)))

    with controller.acquire(namespace) as lease:
        assert (lease.path / "counter").read_text(encoding="utf-8") == "2"
        assert lease.state == "warm"
    assert set(states) == {"cold", "warm"}


def test_corruption_is_evicted_and_clean_execution_remains_available(tmp_path: Path) -> None:
    controller = CacheController(tmp_path, max_bytes=1024)
    namespace = cache_namespace({"runner": "dotnet", "dependencies": "locked"})
    with controller.acquire(namespace) as lease:
        (lease.path / "package").write_text("trusted", encoding="utf-8")
        controller.seal(lease)
    (tmp_path / namespace / "package").write_text("corrupt", encoding="utf-8")

    with controller.acquire(namespace) as lease:
        assert lease.state == "corrupt-evicted"
        assert list(lease.path.iterdir()) == []
        (lease.path / "package").write_text("clean", encoding="utf-8")
        controller.seal(lease)

    with controller.acquire(namespace) as lease:
        assert lease.state == "warm"


def test_cache_manifest_is_explicitly_non_authoritative_and_size_is_bounded(tmp_path: Path) -> None:
    controller = CacheController(tmp_path, max_bytes=4)
    namespace = cache_namespace({"runner": "typescript", "dependencies": "locked"})
    with controller.acquire(namespace) as lease:
        assert lease.authoritative is False
        (lease.path / "entry").write_text("pass", encoding="utf-8")
        controller.seal(lease)
        manifest = json.loads((lease.path / MANIFEST).read_text(encoding="utf-8"))
        assert manifest["authoritative"] is False

    with controller.acquire(namespace) as lease:
        (lease.path / "entry").write_text("oversized", encoding="utf-8")
        try:
            controller.seal(lease)
        except ValueError as error:
            assert str(error) == "cache exceeds declared size bound"
        else:
            raise AssertionError("oversized cache was accepted")
        assert list(lease.path.iterdir()) == []
