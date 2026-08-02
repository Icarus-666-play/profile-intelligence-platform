"""Application composition root / dependency wiring."""

from __future__ import annotations

from profile_intelligence.core.config import AppConfig, load_config
from profile_intelligence.core.container import Container
from profile_intelligence.core.logging import configure_logging, get_logger
from profile_intelligence.core.types import PathLike
from profile_intelligence.database.connection import Database, create_database
from profile_intelligence.database.repository import ProfileRepository
from profile_intelligence.excel.exporter import ExcelExporter
from profile_intelligence.extractors.profile import ProfileExtractor
from profile_intelligence.importers.registry import ImporterRegistry
from profile_intelligence.scoring.completeness import CompletenessScorer
from profile_intelligence.search.service import ProfileSearchService
from profile_intelligence.services.application import ApplicationService
from profile_intelligence.services.import_service import ImportService
from profile_intelligence.services.profile_service import ProfileService

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
        CompletenessScorer,
        CompletenessScorer,
        name="scorer",
    )
    container.register(
        ProfileExtractor,
        ProfileExtractor,
        name="extractor",
    )
    container.register(
        ProfileSearchService,
        lambda: ProfileSearchService(
            container.resolve(Database),
            default_limit=container.resolve(AppConfig).search.default_limit,
        ),
        name="search",
    )
    container.register(
        ExcelExporter,
        lambda: ExcelExporter(container.resolve(AppConfig)),
        name="excel",
    )
    container.register(
        ImportService,
        lambda: ImportService(
            registry=container.resolve(ImporterRegistry),
            repository=container.resolve(ProfileRepository),
            extractor=container.resolve(ProfileExtractor),
            scorer=container.resolve(CompletenessScorer),
        ),
        name="import",
    )
    container.register(
        ProfileService,
        lambda: ProfileService(
            repository=container.resolve(ProfileRepository),
            search_service=container.resolve(ProfileSearchService),
            exporter=container.resolve(ExcelExporter),
            scorer=container.resolve(CompletenessScorer),
        ),
        name="profile_service",
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
