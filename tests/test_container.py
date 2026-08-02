"""Tests for the DI container."""

from __future__ import annotations

import pytest

from profile_intelligence.core.container import Container, ContainerError


class Service:
    def __init__(self, value: int = 1) -> None:
        self.value = value


def test_register_instance_and_resolve() -> None:
    container = Container()
    service = Service(42)
    container.register_instance(Service, service, name="svc")
    assert container.resolve(Service) is service
    assert container.resolve_by_name("svc") is service


def test_factory_singleton() -> None:
    container = Container()
    calls = {"n": 0}

    def factory() -> Service:
        calls["n"] += 1
        return Service(calls["n"])

    container.register(Service, factory)
    first = container.resolve(Service)
    second = container.resolve(Service)
    assert first is second
    assert calls["n"] == 1


def test_missing_service() -> None:
    container = Container()
    with pytest.raises(ContainerError):
        container.resolve(Service)


def test_duplicate_registration() -> None:
    container = Container()
    container.register_instance(Service, Service())
    with pytest.raises(ContainerError):
        container.register(Service, Service)
