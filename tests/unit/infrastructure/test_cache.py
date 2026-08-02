"""Cache backend tests."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from profile_intelligence.bootstrap import build_container
from profile_intelligence.core.config import AppConfig, CacheSection
from profile_intelligence.core.exceptions import CacheError, ConfigurationError
from profile_intelligence.domain.interfaces.cache import ICache
from profile_intelligence.infrastructure.cache import (
    FileCache,
    MemoryCache,
    RedisCache,
    SQLiteCache,
    create_cache,
)


def test_memory_cache_roundtrip() -> None:
    cache = MemoryCache(default_ttl_seconds=None)
    assert cache.backend == "memory"
    assert cache.get("missing") is None
    assert not cache.has("k")

    cache.set("k", {"v": 1})
    assert cache.has("k")
    assert cache.get("k") == {"v": 1}

    cache.delete("k")
    assert cache.get("k") is None


def test_memory_cache_ttl_expiry() -> None:
    cache = MemoryCache(default_ttl_seconds=1)
    cache.set("k", "v", ttl_seconds=1)
    assert cache.get("k") == "v"
    time.sleep(1.1)
    assert cache.get("k") is None
    assert not cache.has("k")


def test_memory_cache_clear() -> None:
    cache = MemoryCache()
    cache.set("a", 1)
    cache.set("b", 2)
    cache.clear()
    assert cache.get("a") is None
    assert cache.get("b") is None


def test_file_cache_roundtrip(tmp_path: Path) -> None:
    cache = FileCache(tmp_path / "cache", default_ttl_seconds=None)
    assert cache.backend == "file"
    cache.set("profile:1", {"name": "Ada"})
    assert cache.get("profile:1") == {"name": "Ada"}
    assert cache.has("profile:1")
    cache.delete("profile:1")
    assert cache.get("profile:1") is None


def test_file_cache_ttl_and_clear(tmp_path: Path) -> None:
    cache = FileCache(tmp_path / "cache", default_ttl_seconds=1)
    cache.set("a", 1, ttl_seconds=1)
    cache.set("b", 2, ttl_seconds=0)
    time.sleep(1.1)
    assert cache.get("a") is None
    assert cache.get("b") == 2
    cache.clear()
    assert cache.get("b") is None


def test_sqlite_cache_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "cache.sqlite3"
    cache = SQLiteCache(path, default_ttl_seconds=None)
    assert cache.backend == "sqlite"
    cache.set("k", [1, 2, 3])
    assert cache.get("k") == [1, 2, 3]
    assert cache.has("k")
    cache.delete("k")
    assert not cache.has("k")


def test_sqlite_cache_ttl_and_clear(tmp_path: Path) -> None:
    cache = SQLiteCache(tmp_path / "c.db", default_ttl_seconds=1)
    cache.set("a", "x", ttl_seconds=1)
    cache.set("b", "y", ttl_seconds=0)
    time.sleep(1.1)
    assert cache.get("a") is None
    assert cache.get("b") == "y"
    cache.clear()
    assert cache.get("b") is None


def test_redis_cache_raises() -> None:
    with pytest.raises(CacheError, match="not implemented"):
        RedisCache()


def test_create_cache_selects_backends(tmp_path: Path) -> None:
    mem = create_cache(AppConfig(cache=CacheSection(backend="memory")))
    assert isinstance(mem, MemoryCache)

    file_cfg = AppConfig(
        root_dir=tmp_path,
        cache=CacheSection(backend="file", file_dir="cache-files"),
    )
    assert isinstance(create_cache(file_cfg), FileCache)

    sqlite_cfg = AppConfig(
        root_dir=tmp_path,
        cache=CacheSection(backend="sqlite", sqlite_file="c.db"),
    )
    assert isinstance(create_cache(sqlite_cfg), SQLiteCache)

    with pytest.raises(CacheError, match="not implemented"):
        create_cache(AppConfig(cache=CacheSection(backend="redis")))

    with pytest.raises(ConfigurationError, match="Unsupported"):
        create_cache(AppConfig(cache=CacheSection(backend="nope")))


def test_bootstrap_registers_cache(temp_root: Path) -> None:
    container = build_container(root_dir=temp_root)
    cache = container.resolve(ICache)
    assert cache.backend == "memory"
    cache.set("boot", True)
    assert cache.get("boot") is True
