"""Tests for the exception hierarchy."""

from __future__ import annotations

from profile_intelligence.core.exceptions import (
    ConfigurationError,
    DatabaseError,
    ImporterError,
    MigrationError,
    PipError,
    PluginError,
    RepositoryError,
)


def test_pip_error_str_and_cause() -> None:
    cause = ValueError("root")
    err = PipError("boom", cause=cause)
    assert str(err) == "boom"
    assert err.message == "boom"
    assert err.cause is cause


def test_hierarchy() -> None:
    assert issubclass(ConfigurationError, PipError)
    assert issubclass(DatabaseError, PipError)
    assert issubclass(MigrationError, DatabaseError)
    assert issubclass(RepositoryError, DatabaseError)
    assert issubclass(PluginError, PipError)
    assert issubclass(ImporterError, PluginError)
