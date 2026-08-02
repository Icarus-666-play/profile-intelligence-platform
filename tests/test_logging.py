"""Tests for logging configuration."""

from __future__ import annotations

from profile_intelligence.core.config import AppConfig
from profile_intelligence.core.logging import (
    configure_logging,
    get_logger,
    reset_logging,
)


def test_configure_logging_creates_file(app_config: AppConfig) -> None:
    configure_logging(app_config)
    logger = get_logger("tests.logging")
    logger.info("hello from test")
    log_file = app_config.logs_dir / app_config.logging.filename
    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "hello from test" in content


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
