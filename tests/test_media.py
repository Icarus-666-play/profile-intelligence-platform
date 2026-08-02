"""Tests for media hashing, duplicates, thumbnails, and image repository."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from profile_intelligence.application.use_cases.application import ApplicationService
from profile_intelligence.bootstrap import build_container
from profile_intelligence.core.config_manager import load_config
from profile_intelligence.infrastructure.media import (
    ImageDuplicateFinder,
    ImageRepository,
    ThumbnailService,
    hash_bytes,
    hash_file,
    short_hash,
)


def _write_png(path: Path, color: tuple[int, int, int] = (255, 0, 0)) -> None:
    image = Image.new("RGB", (32, 24), color=color)
    image.save(path, format="PNG")


def test_hash_bytes_and_file(tmp_path: Path) -> None:
    payload = b"pip-media"
    assert hash_bytes(payload) == hash_bytes(payload)
    path = tmp_path / "blob.bin"
    path.write_bytes(payload)
    assert hash_file(path) == hash_bytes(payload)
    assert len(short_hash(hash_file(path))) == 16


def test_image_duplicate_finder(tmp_path: Path) -> None:
    a = tmp_path / "a.png"
    b = tmp_path / "b.png"
    c = tmp_path / "c.png"
    _write_png(a, (1, 2, 3))
    _write_png(b, (1, 2, 3))
    _write_png(c, (9, 9, 9))

    result = ImageDuplicateFinder().find([a, b, c])
    assert result.hashed == 3
    assert len(result.groups) == 1
    assert result.duplicate_count == 1
    assert set(result.groups[0].paths) == {a.resolve(), b.resolve()}


def test_thumbnail_service(temp_root: Path) -> None:
    config = load_config(root_dir=temp_root)
    config.ensure_directories()
    source = temp_root / "photo.png"
    _write_png(source, (10, 20, 30))

    service = ThumbnailService(config)
    thumb = service.make_thumbnail(source)
    assert thumb.is_file()
    assert thumb.parent == config.thumbnails_dir
    with Image.open(thumb) as image:
        assert max(image.size) <= config.media.thumbnail_max_size


def test_image_repository_store_and_dedupe(temp_root: Path) -> None:
    container = build_container(root_dir=temp_root)
    app = container.resolve(ApplicationService)
    app.start()

    source = temp_root / "face.png"
    _write_png(source, (40, 50, 60))
    repo = container.resolve(ImageRepository)

    first = repo.store(source, profile_id=1)
    second = repo.store(source, profile_id=1)
    assert first.id == second.id
    assert first.content_hash == second.content_hash
    assert Path(first.storage_path).is_file()
    assert first.thumbnail_path is not None
    assert Path(first.thumbnail_path).is_file()

    listed = repo.list_for_profile(1)
    assert len(listed) == 1
    assert repo.find_by_hash(first.content_hash) is not None
    assert repo.get_by_id(first.id) is not None

    assert repo.delete(first.id, remove_files=True) is True
    assert repo.get_by_id(first.id) is None
    app.shutdown()
