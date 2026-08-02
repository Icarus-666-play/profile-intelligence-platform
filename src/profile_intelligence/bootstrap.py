"""Application composition root / dependency wiring."""

from __future__ import annotations

from profile_intelligence.core.config import AppConfig, load_config
from profile_intelligence.core.container import Container
from profile_intelligence.core.logging import configure_logging, get_logger
from profile_intelligence.core.types import PathLike
from profile_intelligence.database.connection import Database, create_database
from profile_intelligence.database.repository import ProfileRepository
from profile_intelligence.importers.registry import ImporterRegistry
from profile_intelligence.services.application import ApplicationService

logger = get_logger(__name__)


def build_container(
    config_path: PathLike | None = None,
    *,
    root_dir: PathLike | None = None,
) -> Container:
    """Load config, configure logging, and wire core services."""
    config = load_config(config_path, root_dir=root_dir)
    configure_logging(config)
    config.ensure_directories()

    container = Container()
    container.register_instance(AppConfig, config, name="config")

    database = create_database(config)
    container.register_instance(Database, database, name="database")

    importers = ImporterRegistry()
    container.register_instance(ImporterRegistry, importers, name="importers")

    container.register(
        ProfileRepository,
        lambda: ProfileRepository(container.resolve(Database)),
        name="profiles",
    )
    container.register(
        ApplicationService,
        lambda: ApplicationService(
            config=container.resolve(AppConfig),
            database=container.resolve(Database),
            importers=container.resolve(ImporterRegistry),
        ),
        name="app",
    )

    logger.debug("Dependency container built")
    return container
