"""Importer plugin discovery and registry."""

from __future__ import annotations

import importlib
import importlib.util
import pkgutil
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from types import ModuleType

from profile_intelligence.core.exceptions import ImporterError, PluginError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike
from profile_intelligence.infrastructure.importers.base import ImporterPlugin
from profile_intelligence.infrastructure.importers.profile_importer import (
    ProfileImporter,
)

logger = get_logger(__name__)


class ImporterRegistry:
    """Registry of available importer plugins."""

    def __init__(self) -> None:
        self._plugins: dict[str, ImporterPlugin] = {}

    def register(self, plugin: ImporterPlugin) -> None:
        """Register a plugin instance by its ``name``."""
        name = getattr(plugin, "name", None)
        if not name or not isinstance(name, str):
            raise PluginError(
                f"Importer plugin {type(plugin).__name__} must define a string name"
            )
        if name in self._plugins:
            raise PluginError(f"Importer plugin already registered: {name}")
        self._plugins[name] = plugin
        logger.debug("Registered importer plugin: %s", name)

    def get(self, name: str) -> ImporterPlugin:
        """Return a registered plugin by name."""
        try:
            return self._plugins[name]
        except KeyError as exc:
            raise ImporterError(f"Unknown importer plugin: {name}") from exc

    def list_plugins(self) -> Sequence[ImporterPlugin]:
        """Return all registered plugins sorted by name."""
        return tuple(self._plugins[name] for name in sorted(self._plugins))

    def find_handler(self, path: PathLike) -> ImporterPlugin | None:
        """Return the first plugin that reports it can handle *path*."""
        for plugin in self.list_plugins():
            try:
                if plugin.can_handle(path):
                    return plugin
            except Exception:
                logger.exception(
                    "Plugin %s raised during can_handle for %s",
                    plugin.name,
                    path,
                )
        return None

    def discover_builtin(self) -> int:
        """Import built-in plugin package modules and register subclasses."""
        try:
            package = importlib.import_module(
                "profile_intelligence.infrastructure.importers.plugins"
            )
        except ImportError as exc:
            raise PluginError(
                "Unable to import built-in importers package",
                cause=exc,
            ) from exc
        return self._load_from_package(package)

    def discover_directory(self, directory: PathLike) -> int:
        """Load plugin modules and packages from an external directory.

        Supports:
        - top-level ``*.py`` modules under *directory*
        - subpackages such as ``plugins/eurogirls/``, ``plugins/eros/``,
          ``plugins/custom/`` (each with ``__init__.py``)
        """
        path = Path(directory)
        if not path.exists():
            logger.debug("Plugins directory does not exist yet: %s", path)
            return 0
        if not path.is_dir():
            raise PluginError(f"Plugins path is not a directory: {path}")

        count = 0
        sys_path_added = False
        path_str = str(path.resolve())
        if path_str not in sys.path:
            sys.path.insert(0, path_str)
            sys_path_added = True

        try:
            for module_path in sorted(path.glob("*.py")):
                if module_path.name.startswith("_"):
                    continue
                module = self._import_module_from_file(module_path)
                count += self._register_plugins_from_module(module)

            for child in sorted(path.iterdir()):
                if not child.is_dir():
                    continue
                if child.name.startswith(("_", ".")):
                    continue
                count += self._discover_plugin_package(child)
        finally:
            if sys_path_added and path_str in sys.path:
                sys.path.remove(path_str)

        return count

    def _discover_plugin_package(self, package_dir: Path) -> int:
        """Import a plugin package directory and register plugin classes."""
        init_file = package_dir / "__init__.py"
        if not init_file.exists():
            # Loose modules inside a folder (no package): load *.py files.
            count = 0
            for module_path in sorted(package_dir.glob("*.py")):
                if module_path.name.startswith("_"):
                    continue
                module = self._import_module_from_file(module_path)
                count += self._register_plugins_from_module(module)
            return count

        package_name = package_dir.name
        try:
            package = importlib.import_module(package_name)
        except Exception as exc:
            raise PluginError(
                f"Failed importing plugin package: {package_dir}",
                cause=exc,
            ) from exc

        count = self._register_plugins_from_module(package)
        count += self._load_from_package(package)
        logger.debug(
            "Discovered %d plugin(s) from package %s",
            count,
            package_name,
        )
        return count

    def discover(
        self,
        *,
        plugins_dir: PathLike | None = None,
        enabled: Iterable[str] | None = None,
    ) -> int:
        """Discover built-in and optional external plugins.

        If *enabled* is provided and non-empty, unregister plugins whose names
        are not in that set.
        """
        total = self.discover_builtin()
        if plugins_dir is not None:
            total += self.discover_directory(plugins_dir)

        if enabled:
            allowed = set(enabled)
            for name in list(self._plugins):
                if name not in allowed:
                    logger.info(
                        "Disabling importer plugin not in enabled list: %s",
                        name,
                    )
                    del self._plugins[name]
        return total

    def _load_from_package(self, package: ModuleType) -> int:
        count = 0
        package_path = getattr(package, "__path__", None)
        if package_path is None:
            return self._register_plugins_from_module(package)

        for module_info in pkgutil.iter_modules(package_path):
            if module_info.name.startswith("_"):
                continue
            full_name = f"{package.__name__}.{module_info.name}"
            module = importlib.import_module(full_name)
            count += self._register_plugins_from_module(module)
        return count

    def _register_plugins_from_module(self, module: ModuleType) -> int:
        count = 0
        for value in vars(module).values():
            if not self._is_plugin_class(value):
                continue
            try:
                instance = value()
            except Exception as exc:
                raise PluginError(
                    f"Failed to instantiate importer plugin {value!r}",
                    cause=exc,
                ) from exc
            if instance.name in self._plugins:
                continue
            self.register(instance)
            count += 1
        return count

    @staticmethod
    def _is_plugin_class(value: object) -> bool:
        return (
            isinstance(value, type)
            and issubclass(value, ImporterPlugin)
            and value not in {ImporterPlugin, ProfileImporter}
            and not getattr(value, "__abstractmethods__", None)
        )

    @staticmethod
    def _import_module_from_file(module_path: Path) -> ModuleType:
        module_name = f"pip_external_plugin_{module_path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise PluginError(f"Unable to load plugin module: {module_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            raise PluginError(
                f"Failed executing plugin module: {module_path}",
                cause=exc,
            ) from exc
        return module
