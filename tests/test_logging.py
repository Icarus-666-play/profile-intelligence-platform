"""Tests for logging configuration."""

from __future__ import annotations

import yaml

from profile_intelligence.core.config import AppConfig
from profile_intelligence.core.config_manager import load_config
from profile_intelligence.core.logging import (
    configure_logging,
    get_logger,
    reset_logging,
)


def _flush_root_handlers() -> None:
    for handler in get_logger().handlers:
        handler.flush()


def test_configure_logging_writes_split_files(app_config: AppConfig) -> None:
    configure_logging(app_config)

    app_logger = get_logger("tests.logging")
    import_logger = get_logger(
        "profile_intelligence.application.use_cases.import_service"
    )
    importer_plugin_logger = get_logger(
        "profile_intelligence.infrastructure.importers.plugins.csv_importer"
    )

    app_logger.info("general application event")
    import_logger.info("import pipeline event")
    importer_plugin_logger.info("csv importer event")
    app_logger.error("something failed")
    _flush_root_handlers()

    logs_dir = app_config.logs_dir
    application_log = (
        logs_dir / app_config.logging.application_filename
    ).read_text(encoding="utf-8")
    import_log = (logs_dir / app_config.logging.import_filename).read_text(
        encoding="utf-8"
    )
    errors_log = (logs_dir / app_config.logging.errors_filename).read_text(
        encoding="utf-8"
    )

    assert "general application event" in application_log
    assert "import pipeline event" in application_log
    assert "something failed" in application_log

    assert "import pipeline event" in import_log
    assert "csv importer event" in import_log
    assert "general application event" not in import_log

    assert "something failed" in errors_log
    assert "general application event" not in errors_log


def test_logging_filename_alias(app_config: AppConfig) -> None:
    assert app_config.logging.filename == app_config.logging.application_filename
    assert app_config.logging.application_filename == "application.log"
    assert app_config.logging.import_filename == "import.log"
    assert app_config.logging.errors_filename == "errors.log"


def test_legacy_filename_maps_to_application(temp_root) -> None:
    logging_path = temp_root / "config" / "logging.yaml"
    logging_path.write_text(
        yaml.safe_dump(
            {
                "level": "INFO",
                "console": False,
                "file": True,
                "filename": "legacy-app.log",
            }
        ),
        encoding="utf-8",
    )
    config = load_config(root_dir=temp_root)
    assert config.logging.application_filename == "legacy-app.log"
    assert config.logging.import_filename == "import.log"
    assert config.logging.errors_filename == "errors.log"


def test_get_logger_namespaces() -> None:
    assert get_logger().name == "profile_intelligence"
    assert get_logger("core").name == "profile_intelligence.core"
    assert (
        get_logger("profile_intelligence.database").name
        == "profile_intelligence.database"
    )


def test_configure_is_idempotent(app_config: AppConfig) -> None:
    configure_logging(app_config)
    handler_count = len(get_logger().handlers)
    configure_logging(app_config)
    assert len(get_logger().handlers) == handler_count
    configure_logging(app_config, force=True)
    assert len(get_logger().handlers) == handler_count


def test_reset_logging(app_config: AppConfig) -> None:
    configure_logging(app_config)
    reset_logging()
    assert get_logger().handlers == []
