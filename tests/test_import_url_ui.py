"""URL Import UI: preview, activity panels, recent/queue/errors/completed."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from profile_intelligence.api import ApiContext, create_fastapi_app
from profile_intelligence.application.use_cases.application import ApplicationService
from profile_intelligence.application.use_cases.compare_service import CompareService
from profile_intelligence.application.use_cases.import_flow import ImportFlow
from profile_intelligence.application.use_cases.import_service import ImportService
from profile_intelligence.application.use_cases.profile_service import ProfileService
from profile_intelligence.bootstrap import build_container
from profile_intelligence.core.config import AppConfig
from profile_intelligence.domain.interfaces.plugin_pipeline import DownloadArtifact
from profile_intelligence.domain.interfaces.repositories import IProfileRepository
from profile_intelligence.infrastructure.analysis import AnalysisService
from profile_intelligence.infrastructure.auth import LocalAuthService
from profile_intelligence.infrastructure.dashboard import DashboardService
from profile_intelligence.infrastructure.download import DocumentDownloader
from profile_intelligence.infrastructure.importers.import_activity import (
    ImportActivityStore,
)
from profile_intelligence.infrastructure.importers.import_ledger import ImportFileLedger
from profile_intelligence.infrastructure.importers.registry import ImporterRegistry


class _LocalDownloader:
    def __init__(self, path: Path) -> None:
        self._path = path

    def download(self, source: str | Path) -> DownloadArtifact:
        return DownloadArtifact(path=self._path, source=str(source))


def _ctx(
    tmp_path: Path,
    *,
    csv_path: Path | None = None,
) -> tuple[ApiContext, ApplicationService]:
    container = build_container(root_dir=tmp_path)
    app = container.resolve(ApplicationService)
    app.start()
    downloader: DocumentDownloader | _LocalDownloader | None
    if csv_path is not None:
        downloader = _LocalDownloader(csv_path)
    else:
        downloader = container.resolve(DocumentDownloader)
    ctx = ApiContext(
        config=container.resolve(AppConfig),
        profiles=container.resolve(ProfileService),
        repository=container.resolve(IProfileRepository),
        imports=container.resolve(ImportService),
        import_flow=container.resolve(ImportFlow),
        compare=container.resolve(CompareService),
        dashboard=container.resolve(DashboardService),
        analysis=container.resolve(AnalysisService),
        importers=container.resolve(ImporterRegistry),
        downloader=downloader,  # type: ignore[arg-type]
        auth=container.resolve(LocalAuthService),
        import_activity=container.resolve(ImportActivityStore),
    )
    return ctx, app


def test_import_activity_store_and_queue(temp_root: Path) -> None:
    container = build_container(root_dir=temp_root)
    app = container.resolve(ApplicationService)
    app.start()
    try:
        store = container.resolve(ImportActivityStore)
        store.remember_url("https://example.com/a.csv")
        store.set_progress(
            url="https://example.com/a.csv",
            stage="download",
            message="Downloading…",
            percent=40,
        )
        store.record_error(url="https://example.com/bad.csv", message="boom")
        store.record_completed(
            url="https://example.com/a.csv",
            path=str(temp_root / "a.csv"),
            plugin="csv",
            created=2,
            success=True,
        )
        inbox = temp_root / "data" / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)
        waiting = inbox / "waiting.csv"
        waiting.write_text("name\nAda\n", encoding="utf-8")
        snap = store.snapshot()
        assert snap.recent_urls[0]["url"] == "https://example.com/a.csv"
        assert snap.progress is None  # cleared by completed/error
        assert snap.errors[0]["message"] == "boom"
        assert snap.completed[0]["created"] == 2
        assert any(item["name"] == "waiting.csv" for item in snap.import_queue)
        assert container.resolve(ImportFileLedger).is_new(waiting)
    finally:
        app.shutdown()


def test_import_url_preview_and_import_activity_api(temp_root: Path) -> None:
    csv_path = temp_root / "people.csv"
    csv_path.write_text(
        "name,email\nAda Lovelace,ada@example.com\n",
        encoding="utf-8",
    )
    ctx, app_svc = _ctx(temp_root, csv_path=csv_path)
    try:
        client = TestClient(create_fastapi_app(ctx, serve_spa=False))
        preview = client.post(
            "/api/import/url/preview",
            json={"url": "https://example.com/people.csv", "plugin": "csv"},
        )
        assert preview.status_code == 200
        body = preview.json()
        assert body["ok"] is True
        assert body["accepted_count"] >= 1
        assert body["url"] == "https://example.com/people.csv"

        imported = client.post(
            "/api/import/url",
            json={"url": "https://example.com/people.csv", "plugin": "csv"},
        )
        assert imported.status_code == 200
        assert imported.json()["created"] >= 1

        activity = client.get("/api/import/activity")
        assert activity.status_code == 200
        payload = activity.json()
        assert any(
            item["url"] == "https://example.com/people.csv"
            for item in payload["recent_urls"]
        )
        assert any(
            item["url"] == "https://example.com/people.csv"
            for item in payload["completed"]
        )
    finally:
        app_svc.shutdown()
