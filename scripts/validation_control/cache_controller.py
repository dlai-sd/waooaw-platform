"""Identity-scoped cache locking, integrity verification, and eviction."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil


MANIFEST = ".waooaw-cache-manifest.json"


def cache_namespace(identity: dict[str, object]) -> str:
    if not identity:
        raise ValueError("cache identity must not be empty")
    canonical = json.dumps(identity, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True)
class CacheLease:
    path: Path
    namespace: str
    state: str
    authoritative: bool = False


class CacheController:
    def __init__(self, root: Path, max_bytes: int) -> None:
        if max_bytes < 1:
            raise ValueError("cache size bound must be positive")
        self.root = root
        self.max_bytes = max_bytes

    def _verify(self, path: Path, namespace: str) -> str:
        manifest_path = path / MANIFEST
        retained = sorted(item for item in path.rglob("*") if item.is_file() and item.name != MANIFEST)
        if not manifest_path.is_file():
            return "cold" if not retained else "corrupt"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return "corrupt"
        expected = manifest.get("files")
        if manifest.get("namespace") != namespace or manifest.get("authoritative") is not False:
            return "corrupt"
        if not isinstance(expected, dict):
            return "corrupt"
        actual_names = {str(item.relative_to(path)) for item in retained}
        if actual_names != set(expected):
            return "corrupt"
        for item in retained:
            if item.is_symlink() or expected[str(item.relative_to(path))] != _digest(item):
                return "corrupt"
        return "warm"

    @contextmanager
    def acquire(self, namespace: str) -> Iterator[CacheLease]:
        if len(namespace) != 64 or any(character not in "0123456789abcdef" for character in namespace):
            raise ValueError("cache namespace must be a SHA-256 digest")
        lock_path = self.root / ".locks" / f"{namespace}.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            path = self.root / namespace
            path.mkdir(parents=True, exist_ok=True)
            state = self._verify(path, namespace)
            if state == "corrupt":
                shutil.rmtree(path)
                path.mkdir()
                state = "corrupt-evicted"
            try:
                yield CacheLease(path=path, namespace=namespace, state=state)
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def seal(self, lease: CacheLease) -> None:
        files = sorted(item for item in lease.path.rglob("*") if item.is_file() and item.name != MANIFEST)
        if any(item.is_symlink() for item in files):
            raise ValueError("cache must not contain symbolic links")
        size = sum(item.stat().st_size for item in files)
        if size > self.max_bytes:
            shutil.rmtree(lease.path)
            lease.path.mkdir()
            raise ValueError("cache exceeds declared size bound")
        manifest = {
            "schema": "waooaw.cache-manifest/v1",
            "namespace": lease.namespace,
            "authoritative": False,
            "files": {str(item.relative_to(lease.path)): _digest(item) for item in files},
        }
        temporary = lease.path / f"{MANIFEST}.tmp-{os.getpid()}"
        temporary.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, lease.path / MANIFEST)
