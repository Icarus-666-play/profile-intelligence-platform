"""Application launcher entrypoint."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence

from profile_intelligence import __version__
from profile_intelligence.bootstrap import build_container
from profile_intelligence.core.container import Container
from profile_intelligence.core.exceptions import PipError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.database.seed import DatabaseSeeder
from profile_intelligence.services.application import ApplicationService
from profile_intelligence.services.import_service import ImportService
from profile_intelligence.services.profile_service import ProfileService


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="pip-app",
        description=(
            "Profile Intelligence Platform (PIP) — local-first desktop launcher"
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"Profile Intelligence Platform {__version__}",
    )
    parser.add_argument(
        "--config",
        dest="config_path",
        default=None,
        help="Path to a YAML config override (default: config/local.yaml if present)",
    )

    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("migrate", help="Run database migrations and exit")
    subparsers.add_parser("importers", help="List discovered importer plugins")

    seed_parser = subparsers.add_parser(
        "seed",
        help="Load built-in demo profiles into the database",
    )
    seed_parser.add_argument(
        "--only-if-empty",
        action="store_true",
        help="Skip seeding when profiles already exist",
    )

    import_parser = subparsers.add_parser(
        "import",
        help="Import profiles from a CSV or Excel file",
    )
    import_parser.add_argument("path", help="Path to the file to import")
    import_parser.add_argument(
        "--source",
        default=None,
        help="Override profile source label (default: plugin name)",
    )
    import_parser.add_argument(
        "--plugin",
        default=None,
        help="Force a specific importer plugin name",
    )

    list_parser = subparsers.add_parser("list", help="List stored profiles")
    list_parser.add_argument("--limit", type=int, default=50, help="Max rows")
    list_parser.add_argument("--offset", type=int, default=0, help="Offset")

    search_parser = subparsers.add_parser("search", help="Search stored profiles")
    search_parser.add_argument("query", help="Search text")
    search_parser.add_argument("--limit", type=int, default=None, help="Max rows")

    export_parser = subparsers.add_parser(
        "export",
        help="Export profiles to an Excel workbook",
    )
    export_parser.add_argument(
        "--output",
        default=None,
        help="Output .xlsx path (default: exports/profiles.xlsx)",
    )

    subparsers.add_parser(
        "score",
        help="Recompute completeness scores for all profiles",
    )

    # Backward-compatible flags from Milestone 0.
    parser.add_argument(
        "--migrate-only",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--list-importers",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the application launcher. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    command = _resolve_command(args)

    try:
        container = build_container(config_path=args.config_path)
        app = container.resolve(ApplicationService)
        app.start()
        logger = get_logger(__name__)
        try:
            return _dispatch(command, args, container, logger)
        finally:
            app.shutdown()
    except PipError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"unexpected error: {exc}", file=sys.stderr)
        return 2


def _resolve_command(args: argparse.Namespace) -> str | None:
    if args.migrate_only:
        return "migrate"
    if args.list_importers:
        return "importers"
    command = args.command
    return str(command) if command is not None else None


def _dispatch(
    command: str | None,
    args: argparse.Namespace,
    container: Container,
    logger: logging.Logger,
) -> int:
    if command is None:
        logger.info(
            "%s is ready. Try: import | list | search | export | score | seed",
            container.resolve(ApplicationService).config.app.name,
        )
        return 0

    if command == "migrate":
        logger.info("Migrate-only mode complete")
        return 0

    if command == "importers":
        plugins = container.resolve(ApplicationService).importers.list_plugins()
        if not plugins:
            logger.info("No importer plugins registered")
        else:
            for plugin in plugins:
                logger.info(
                    "Importer: %s — %s (extensions=%s)",
                    plugin.name,
                    plugin.description or "(no description)",
                    ", ".join(plugin.supported_extensions) or "n/a",
                )
        return 0

    if command == "seed":
        result = container.resolve(DatabaseSeeder).seed(
            only_if_empty=args.only_if_empty,
        )
        logger.info(
            "Seeded profiles: created=%d updated=%d skipped=%d",
            result.created,
            result.updated,
            result.skipped,
        )
        return 0

    if command == "import":
        summary = container.resolve(ImportService).import_path(
            args.path,
            source=args.source,
            plugin_name=args.plugin,
        )
        logger.info(
            "Imported %s via %s: created=%d updated=%d skipped=%d",
            summary.path,
            summary.plugin,
            summary.created,
            summary.updated,
            summary.skipped,
        )
        for error in summary.errors:
            logger.warning("Import issue: %s", error)
        if (summary.created + summary.updated) > 0:
            return 0
        return 1 if summary.errors else 0

    profiles = container.resolve(ProfileService)

    if command == "list":
        rows = profiles.list_profiles(limit=args.limit, offset=args.offset)
        total = profiles.count()
        logger.info("Showing %d of %d profile(s)", len(rows), total)
        for profile in rows:
            logger.info(
                "[%s] %s | %s | %s | score=%s",
                profile.id,
                profile.display_name,
                profile.email or "-",
                profile.organization or "-",
                profile.score if profile.score is not None else "-",
            )
        return 0

    if command == "search":
        rows = profiles.search(args.query, limit=args.limit)
        logger.info("Found %d profile(s) for %r", len(rows), args.query)
        for profile in rows:
            logger.info(
                "[%s] %s | %s | %s | score=%s",
                profile.id,
                profile.display_name,
                profile.email or "-",
                profile.organization or "-",
                profile.score if profile.score is not None else "-",
            )
        return 0

    if command == "export":
        path = profiles.export_excel(args.output)
        logger.info("Excel export written to %s", path)
        return 0

    if command == "score":
        updated = profiles.rescore_all()
        logger.info("Updated scores for %d profile(s)", updated)
        return 0

    logger.error("Unknown command: %s", command)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
