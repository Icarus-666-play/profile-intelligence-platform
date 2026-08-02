"""Core application primitives: config, logging, DI, exceptions."""

from __future__ import annotations

from profile_intelligence.core.config import AppConfig, ScoringSection
from profile_intelligence.core.config_manager import ConfigManager, load_config
from profile_intelligence.core.container import Container
from profile_intelligence.core.exceptions import (
    CacheError,
    ConfigurationError,
    DatabaseError,
    ImporterError,
    MigrationError,
    PipError,
    PluginError,
    RepositoryError,
    ValidationError,
)
from profile_intelligence.core.logging import configure_logging, get_logger

__all__ = [
    "AppConfig",
    "CacheError",
    "ConfigManager",
    "ConfigurationError",
    "Container",
    "DatabaseError",
    "ImporterError",
    "MigrationError",
    "PipError",
    "PluginError",
    "RepositoryError",
    "ScoringSection",
    "ValidationError",
    "configure_logging",
    "get_logger",
    "load_config",
]
