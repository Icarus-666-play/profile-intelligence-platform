"""Settings snapshot and database backups."""

from __future__ import annotations

from pathlib import Path

from profile_intelligence.api import ApiApp
from tests.test_api import _api_context, _request


def test_settings_snapshot_and_backup(temp_root: Path) -> None:
    ctx, app_svc, _container = _api_context(temp_root)
    try:
        api = ApiApp(ctx)
        code, payload = _request(api, "GET", "/api/settings")
        assert code == 200
        for key in (
            "theme",
            "database",
            "plugins",
            "scoring",
            "import_folder",
            "playwright",
            "backups",
        ):
            assert key in payload
        assert payload["database"]["driver"] == "sqlite"
        assert payload["scoring"]["method"] == "completeness"
        assert "display_name" in payload["scoring"]["weights"]
        assert payload["import_folder"]["configured"]
        assert payload["playwright"]["enabled"] is False
        assert payload["plugins"]["count"] >= 1

        code, created = _request(api, "POST", "/api/backups", body={})
        assert code == 200
        assert created["ok"] is True
        assert created["backup"]["name"].startswith("pip-")
        backup_path = Path(created["backup"]["path"])
        assert backup_path.is_file()

        code, listed = _request(api, "GET", "/api/backups")
        assert code == 200
        assert listed["count"] >= 1
        assert any(item["name"] == created["backup"]["name"] for item in listed["items"])
    finally:
        app_svc.shutdown()
