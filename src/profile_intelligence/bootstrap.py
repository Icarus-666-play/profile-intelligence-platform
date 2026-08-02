"""Application composition root / dependency wiring."""

from __future__ import annotations

from profile_intelligence.application.events import InMemoryEventBus
from profile_intelligence.application.use_cases import ImportPipeline
from profile_intelligence.application.use_cases.application import ApplicationService
from profile_intelligence.application.use_cases.compare_service import CompareService
from profile_intelligence.application.use_cases.daily_pipeline import DailyPipeline
from profile_intelligence.application.use_cases.import_flow import ImportFlow
from profile_intelligence.application.use_cases.import_service import ImportService
from profile_intelligence.application.use_cases.media_pipeline import ImagePipeline
from profile_intelligence.application.use_cases.nightly_pipeline import NightlyPipeline
from profile_intelligence.application.use_cases.profile_service import ProfileService
from profile_intelligence.core.config import AppConfig
from profile_intelligence.core.config_manager import ConfigManager
from profile_intelligence.core.container import Container
from profile_intelligence.core.logging import configure_logging, get_logger
from profile_intelligence.core.types import PathLike
from profile_intelligence.domain.entities.profile import ProfileExtractor
from profile_intelligence.domain.interfaces.ai import IAIProvider
from profile_intelligence.domain.interfaces.cache import ICache
from profile_intelligence.domain.interfaces.events import IEventBus
from profile_intelligence.domain.interfaces.repositories import (
    IPhotoRepository,
    IProfileRepository,
    IRateRepository,
    IReviewRepository,
    IServiceRepository,
)
from profile_intelligence.infrastructure.ai import create_ai_provider
from profile_intelligence.infrastructure.analysis import (
    AnalysisService,
    ProfileClassifier,
    ProfileDuplicateAnalyzer,
    ProfileRecommender,
    ProfileSimilarityAnalyzer,
    ProfileSummarizer,
)
from profile_intelligence.infrastructure.cache import create_cache
from profile_intelligence.infrastructure.dashboard import DashboardService
from profile_intelligence.infrastructure.database.child_repositories import (
    SQLitePhotoRepository,
    SQLiteRateRepository,
    SQLiteReviewRepository,
    SQLiteServiceRepository,
)
from profile_intelligence.infrastructure.database.connection import (
    Database,
    create_database,
)
from profile_intelligence.infrastructure.database.repository import (
    PostgreSQLProfileRepository,
    SQLiteProfileRepository,
    create_profile_repository,
)
from profile_intelligence.infrastructure.database.seed import DatabaseSeeder
from profile_intelligence.infrastructure.download import DocumentDownloader
from profile_intelligence.infrastructure.excel.exporter import ExcelExporter
from profile_intelligence.infrastructure.importers.import_ledger import ImportFileLedger
from profile_intelligence.infrastructure.importers.registry import ImporterRegistry
from profile_intelligence.infrastructure.media import (
    ImageDownloader,
    ImageDuplicateFinder,
    ImageRepository,
    ThumbnailService,
)
from profile_intelligence.infrastructure.reporting import EmailReportService
from profile_intelligence.infrastructure.scoring.completeness import CompletenessScorer
from profile_intelligence.infrastructure.scoring.confidence import ConfidenceScorer
from profile_intelligence.infrastructure.search.service import ProfileSearchService
from profile_intelligence.infrastructure.storage import FileStorage

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
        IProfileRepository,
        lambda: create_profile_repository(
            container.resolve(Database),
            driver=container.resolve(AppConfig).database.driver,
        ),
        name="iprofile",
    )
    container.register(
        SQLiteProfileRepository,
        lambda: SQLiteProfileRepository(container.resolve(Database)),
        name="sqlite_profiles",
    )
    container.register(
        PostgreSQLProfileRepository,
        lambda: PostgreSQLProfileRepository(container.resolve(Database)),
        name="postgres_profiles",
    )
    container.register(
        IRateRepository,
        lambda: SQLiteRateRepository(container.resolve(Database)),
        name="irates",
    )
    container.register(
        IServiceRepository,
        lambda: SQLiteServiceRepository(container.resolve(Database)),
        name="iservices",
    )
    container.register(
        IReviewRepository,
        lambda: SQLiteReviewRepository(container.resolve(Database)),
        name="ireviews",
    )
    container.register(
        IPhotoRepository,
        lambda: SQLitePhotoRepository(container.resolve(Database)),
        name="iphotos",
    )
    container.register(
        CompletenessScorer,
        lambda: CompletenessScorer(container.resolve(AppConfig).scoring),
        name="completeness_scorer",
    )
    container.register(
        ConfidenceScorer,
        lambda: ConfidenceScorer(
            engine=container.resolve(CompletenessScorer),
        ),
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
        ImageDownloader,
        lambda: ImageDownloader(
            container.resolve(AppConfig).media_downloads_dir,
            allow_remote=container.resolve(AppConfig).media.allow_remote_download,
            timeout_seconds=container.resolve(
                AppConfig
            ).media.download_timeout_seconds,
        ),
        name="image_downloader",
    )
    container.register(
        DocumentDownloader,
        lambda: DocumentDownloader(
            container.resolve(AppConfig).data_dir / "inbox" / "downloads",
            allow_remote=container.resolve(AppConfig).media.allow_remote_download,
            timeout_seconds=container.resolve(
                AppConfig
            ).media.download_timeout_seconds,
        ),
        name="document_downloader",
    )
    container.register(
        FileStorage,
        lambda: FileStorage(container.resolve(AppConfig)),
        name="file_storage",
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
        ImagePipeline,
        lambda: ImagePipeline(
            config=container.resolve(AppConfig),
            image_repository=container.resolve(ImageRepository),
            downloader=container.resolve(ImageDownloader),
            thumbnail_service=container.resolve(ThumbnailService),
            photo_repository=container.resolve(IPhotoRepository),
        ),
        name="image_pipeline",
    )
    container.register(
        ImportPipeline,
        lambda: ImportPipeline(
            registry=container.resolve(ImporterRegistry),
            repository=container.resolve(IProfileRepository),
            stages=container.resolve(AppConfig).pipeline.stages,
            extractor=container.resolve(ProfileExtractor),
            scorer=container.resolve(ConfidenceScorer),
        ),
        name="pipeline",
    )
    container.register(
        ImportService,
        lambda: ImportService(
            registry=container.resolve(ImporterRegistry),
            repository=container.resolve(IProfileRepository),
            extractor=container.resolve(ProfileExtractor),
            scorer=container.resolve(ConfidenceScorer),
            pipeline=container.resolve(ImportPipeline),
        ),
        name="import",
    )
    container.register(
        ImportFlow,
        lambda: ImportFlow(
            container.resolve(ImportService),
            registry=container.resolve(ImporterRegistry),
            pipeline=container.resolve(ImportPipeline),
        ),
        name="import_flow",
    )
    container.register(
        ProfileService,
        lambda: ProfileService(
            repository=container.resolve(IProfileRepository),
            search_service=container.resolve(ProfileSearchService),
            exporter=container.resolve(ExcelExporter),
            scorer=container.resolve(ConfidenceScorer),
        ),
        name="profile_service",
    )
    container.register(
        CompareService,
        lambda: CompareService(container.resolve(IProfileRepository)),
        name="compare",
    )
    container.register(
        DashboardService,
        lambda: DashboardService(container.resolve(IProfileRepository)),
        name="dashboard",
    )
    container.register(
        InMemoryEventBus,
        lambda: InMemoryEventBus(),
        name="event_bus",
    )
    container.register(
        IEventBus,
        lambda: container.resolve(InMemoryEventBus),
        name="ievent_bus",
    )
    container.register(
        ICache,
        lambda: create_cache(container.resolve(AppConfig)),
        name="cache",
    )
    container.register(
        IAIProvider,
        lambda: create_ai_provider(container.resolve(AppConfig)),
        name="ai",
    )
    container.register(
        ProfileSimilarityAnalyzer,
        ProfileSimilarityAnalyzer,
        name="similarity",
    )
    container.register(
        ProfileRecommender,
        lambda: ProfileRecommender(container.resolve(ProfileSimilarityAnalyzer)),
        name="recommender",
    )
    container.register(
        ProfileSummarizer,
        lambda: ProfileSummarizer(container.resolve(IAIProvider)),
        name="summarizer",
    )
    container.register(
        ProfileClassifier,
        ProfileClassifier,
        name="classifier",
    )
    container.register(
        ProfileDuplicateAnalyzer,
        lambda: ProfileDuplicateAnalyzer(
            container.resolve(ProfileSimilarityAnalyzer)
        ),
        name="profile_duplicates",
    )
    container.register(
        AnalysisService,
        lambda: AnalysisService(
            repository=container.resolve(IProfileRepository),
            similarity=container.resolve(ProfileSimilarityAnalyzer),
            recommender=container.resolve(ProfileRecommender),
            summarizer=container.resolve(ProfileSummarizer),
            classifier=container.resolve(ProfileClassifier),
            duplicates=container.resolve(ProfileDuplicateAnalyzer),
            ai=container.resolve(IAIProvider),
        ),
        name="analysis",
    )
    container.register(
        ImportFileLedger,
        lambda: ImportFileLedger(container.resolve(Database)),
        name="import_ledger",
    )
    container.register(
        EmailReportService,
        lambda: EmailReportService(
            enabled=container.resolve(AppConfig).daily.email_enabled,
            recipients=(
                (container.resolve(AppConfig).daily.email_to,)
                if container.resolve(AppConfig).daily.email_to
                else ()
            ),
        ),
        name="email_report",
    )
    container.register(
        DailyPipeline,
        lambda: DailyPipeline(
            config=container.resolve(AppConfig),
            import_service=container.resolve(ImportService),
            profile_service=container.resolve(ProfileService),
            dashboard=container.resolve(DashboardService),
            database=container.resolve(Database),
            registry=container.resolve(ImporterRegistry),
            event_bus=container.resolve(IEventBus),
            photo_repository=container.resolve(IPhotoRepository),
            image_repository=container.resolve(ImageRepository),
            image_pipeline=container.resolve(ImagePipeline),
            import_ledger=container.resolve(ImportFileLedger),
            email_report=container.resolve(EmailReportService),
        ),
        name="daily",
    )
    container.register(
        NightlyPipeline,
        lambda: NightlyPipeline(container.resolve(DailyPipeline)),
        name="nightly",
    )
    container.register(
        DatabaseSeeder,
        lambda: DatabaseSeeder(
            repository=container.resolve(IProfileRepository),
            scorer=container.resolve(ConfidenceScorer),
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
