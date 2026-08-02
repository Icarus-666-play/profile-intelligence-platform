"""Tests for Image → Download → Hash → Duplicate → Thumbnail → Storage."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from profile_intelligence.application.use_cases.application import ApplicationService
from profile_intelligence.application.use_cases.media_pipeline import (
    DEFAULT_IMAGE_PIPELINE_STAGES,
    ImagePipeline,
    ImageSource,
)
from profile_intelligence.bootstrap import build_container
from profile_intelligence.core.exceptions import MediaError
from profile_intelligence.domain.entities.profile import ProfileDraft
from profile_intelligence.domain.interfaces.repositories import (
    IPhotoRepository,
    IProfileRepository,
)
from profile_intelligence.domain.value_objects.profile_children import Photo
from profile_intelligence.infrastructure.media import ImageDownloader, ImageRepository


def _write_png(path: Path, color: tuple[int, int, int] = (255, 0, 0)) -> None:
    image = Image.new("RGB", (48, 32), color=color)
    image.save(path, format="PNG")


def test_default_image_pipeline_stages() -> None:
    assert DEFAULT_IMAGE_PIPELINE_STAGES == (
        "download",
        "hash",
        "duplicate_detection",
        "thumbnail",
        "storage",
    )


def test_image_downloader_stages_local_file(temp_root: Path) -> None:
    source = temp_root / "src.png"
    _write_png(source, (1, 2, 3))
    downloader = ImageDownloader(temp_root / "downloads", allow_remote=False)
    result = downloader.download(source)
    assert result.path.is_file()
    assert result.path.parent == temp_root / "downloads"
    assert result.path.read_bytes() == source.read_bytes()


def test_image_downloader_rejects_remote_when_disabled(temp_root: Path) -> None:
    downloader = ImageDownloader(temp_root / "downloads", allow_remote=False)
    try:
        downloader.download("https://example.com/a.png")
        raise AssertionError("expected MediaError")
    except MediaError as exc:
        assert "disabled" in str(exc).lower()


def test_image_pipeline_end_to_end_and_dedupe(temp_root: Path) -> None:
    container = build_container(root_dir=temp_root)
    app = container.resolve(ApplicationService)
    app.start()

    source = temp_root / "face.png"
    _write_png(source, (40, 50, 60))
    pipeline = container.resolve(ImagePipeline)

    first = pipeline.process(ImageSource(uri=str(source), profile_id=1))
    assert first.success
    assert first.stages_run == DEFAULT_IMAGE_PIPELINE_STAGES
    assert first.content_hash is not None
    assert first.asset_id is not None
    assert first.thumbnail_path is not None
    assert Path(first.thumbnail_path).is_file()
    assert first.storage_path is not None
    assert Path(first.storage_path).is_file()
    assert first.is_duplicate is False

    second = pipeline.process(ImageSource(uri=str(source), profile_id=1))
    assert second.success
    assert second.is_duplicate is True
    assert second.asset_id == first.asset_id
    assert second.content_hash == first.content_hash

    batch = pipeline.process_many([source, source])
    assert batch.processed == 2
    assert batch.duplicates == 2
    assert batch.failed == 0

    app.shutdown()


def test_image_pipeline_process_profiles_updates_photo_hash(
    temp_root: Path,
) -> None:
    container = build_container(root_dir=temp_root)
    app = container.resolve(ApplicationService)
    app.start()

    profiles = container.resolve(IProfileRepository)
    photos = container.resolve(IPhotoRepository)
    pipeline = container.resolve(ImagePipeline)

    entity, _created = profiles.upsert_draft(
        ProfileDraft(
            display_name="Ada",
            email="ada@example.com",
            source="test",
        )
    )
    assert entity.id is not None

    image_path = temp_root / "ada.png"
    _write_png(image_path, (10, 20, 30))
    photos.replace_for_profile(
        entity.id,
        [Photo(original_url=str(image_path), role="main")],
    )

    result = pipeline.process_profiles([entity.id])
    assert result.processed == 1
    assert result.failed == 0

    stored = list(photos.list_for_profile(entity.id))
    assert len(stored) == 1
    assert stored[0].sha256 is not None
    assert stored[0].sha256 == result.items[0].content_hash

    assets = container.resolve(ImageRepository).list_for_profile(entity.id)
    assert len(assets) == 1

    app.shutdown()
