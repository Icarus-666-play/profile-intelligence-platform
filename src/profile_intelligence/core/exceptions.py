"""Application exception hierarchy.

All PIP-raised errors should inherit from :class:`PipError` so callers can
catch platform failures without swallowing unrelated exceptions.
"""

from __future__ import annotations


class PipError(Exception):
    """Base exception for Profile Intelligence Platform errors."""

    def __init__(self, message: str, *, cause: BaseException | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.cause = cause

    def __str__(self) -> str:
        return self.message


class ConfigurationError(PipError):
    """Raised when configuration is missing, invalid, or cannot be loaded."""


class ValidationError(PipError):
    """Raised when domain or input validation fails."""


class DatabaseError(PipError):
    """Raised for SQLite / SQLAlchemy connection and persistence failures."""


class MigrationError(DatabaseError):
    """Raised when a database migration cannot be applied or recorded."""


class RepositoryError(DatabaseError):
    """Raised when a repository operation fails."""


class PluginError(PipError):
    """Raised for plugin discovery, registration, or lifecycle failures."""


class ImporterError(PluginError):
    """Raised when an importer plugin fails to load or process data."""


class ExtractorError(PipError):
    """Raised when data extraction fails."""


class ScoringError(PipError):
    """Raised when profile scoring fails."""


class ExcelError(PipError):
    """Raised when Excel export or import operations fail."""


class MediaError(PipError):
    """Raised when media / image operations fail."""


class CacheError(PipError):
    """Raised when cache backend operations fail."""


class SearchError(PipError):
    """Raised when search operations fail."""


class AIError(PipError):
    """Raised when AI provider integration fails."""


class ServiceError(PipError):
    """Raised when an application service operation fails."""
