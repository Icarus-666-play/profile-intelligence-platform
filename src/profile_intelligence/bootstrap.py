"""Application composition root / dependency wiring."""

from __future__ import annotations

from profile_intelligence.application.use_cases import ImportPipeline
from profile_intelligence.application.use_cases.application import ApplicationService
from profile_intelligence.application.use_cases.compare_service import CompareService
from profile_intelligence.application.use_cases.import_service import ImportService
from profile_intelligence.application.use_cases.nightly_pipeline import NightlyPipeline
from profile_intelligence.application.use_cases.profile_service import ProfileService
from profile_intelligence.core.config import AppConfig
from profile_intelligence.core.config_manager import ConfigManager
from profile_intelligence.core.container import Container
from profile_intelligence.core.logging import configure_logging, get_logger
from profile_intelligence.core.types import PathLike
from profile_intelligence.domain.entities.profile import ProfileExtractor
from profile_intelligence.infrastructure.dashboard import DashboardService
from profile_intelligence.infrastructure.database.connection import (
    Database,
    create_database,
)
from profile_intelligence.infrastructure.database.repository import SQLiteRepository
from profile_intelligence.infrastructure.database.seed import DatabaseSeeder
from profile_intelligence.infrastructure.excel.exporter import ExcelExporter
from profile_intelligence.infrastructure.importers.registry import ImporterRegistry
from profile_intelligence.infrastructure.media import (
    ImageDuplicateFinder,
    ImageRepository,
    ThumbnailService,
)
from profile_intelligence.infrastructure.scoring.completeness import CompletenessScorer
from profile_intelligence.infrastructure.search.service import ProfileSearchService

logger = get_logger(__name__)


def build_container(
    config_path: PathLike | None = None,
    *,
    root_dir: PathLike | None = None,
) -> Container:
    """Load config, configure logging, and wire core services."""
    manager = ConfigManager(config_path, root_dir=root_dir)
    config = manager.load()
    configure_logging(config)
    manager.ensure_directories()

    container = Container()
    container.register_instance(ConfigManager, manager, name="config_manager")
    container.register_instance(AppConfig, config, name="config")

    database = create_database(config)
    container.register_instance(Database, database, name="database")

    importers = ImporterRegistry()
    container.register_instance(ImporterRegistry, importers, name="importers")

    container.register(
        SQLiteRepository,
        lambda: SQLiteRepository(container.resolve(Database)),
        name="profiles",
    )
    container.register(
        CompletenessScorer,
        lambda: CompletenessScorer(container.resolve(AppConfig).scoring),
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
        ThumbnailService,
        lambda: ThumbnailService(container.resolve(AppConfig)),
        name="thumbnails",
    )
    container.register(
        ImageRepository,
        lambda: ImageRepository(
            container.resolve(Database),
            container.resolve(AppConfig),
            thumbnail_service=container.resolve(ThumbnailService),
        ),
        name="images",
    )
    container.register(
        ImageDuplicateFinder,
        lambda: ImageDuplicateFinder(
            algorithm=container.resolve(AppConfig).media.hash_algorithm
        ),
        name="image_duplicates",
    )
    container.register(
        ImportPipeline,
        lambda: ImportPipeline(
            registry=container.resolve(ImporterRegistry),
            repository=container.resolve(SQLiteRepository),
            stages=container.resolve(AppConfig).pipeline.stages,
            extractor=container.resolve(ProfileExtractor),
            scorer=container.resolve(CompletenessScorer),
        ),
        name="pipeline",
    )
    container.register(
        ImportService,
        lambda: ImportService(
            registry=container.resolve(ImporterRegistry),
            repository=container.resolve(SQLiteRepository),
            extractor=container.resolve(ProfileExtractor),
            scorer=container.resolve(CompletenessScorer),
            pipeline=container.resolve(ImportPipeline),
        ),
        name="import",
    )
    container.register(
        ProfileService,
        lambda: ProfileService(
            repository=container.resolve(SQLiteRepository),
            search_service=container.resolve(ProfileSearchService),
            exporter=container.resolve(ExcelExporter),
            scorer=container.resolve(CompletenessScorer),
        ),
        name="profile_service",
    )
    container.register(
        CompareService,
        lambda: CompareService(container.resolve(SQLiteRepository)),
        name="compare",
    )
    container.register(
        DashboardService,
        lambda: DashboardService(container.resolve(SQLiteRepository)),
        name="dashboard",
    )
    container.register(
        NightlyPipeline,
        lambda: NightlyPipeline(
            config=container.resolve(AppConfig),
            import_service=container.resolve(ImportService),
            profile_service=container.resolve(ProfileService),
            dashboard=container.resolve(DashboardService),
            database=container.resolve(Database),
            registry=container.resolve(ImporterRegistry),
        ),
        name="nightly",
    )
    container.register(
        DatabaseSeeder,
        lambda: DatabaseSeeder(
            repository=container.resolve(SQLiteRepository),
            scorer=container.resolve(CompletenessScorer),
        ),
        name="seeder",
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
