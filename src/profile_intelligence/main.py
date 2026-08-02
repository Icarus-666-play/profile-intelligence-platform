"""Application launcher entrypoint.

Primary commands::

    pip-app migrate
    pip-app import
    pip-app search
    pip-app compare
    pip-app export
    pip-app dashboard
    pip-app nightly
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from profile_intelligence import __version__
from profile_intelligence.application.use_cases.application import ApplicationService
from profile_intelligence.application.use_cases.compare_service import CompareService
from profile_intelligence.application.use_cases.import_service import ImportService
from profile_intelligence.application.use_cases.nightly_pipeline import NightlyPipeline
from profile_intelligence.application.use_cases.profile_service import ProfileService
from profile_intelligence.bootstrap import build_container
from profile_intelligence.core.container import Container
from profile_intelligence.core.exceptions import PipError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.infrastructure.dashboard import DashboardService
from profile_intelligence.infrastructure.database.seed import DatabaseSeeder

logger = get_logger(__name__)

_PRIMARY_COMMANDS = (
    "migrate",
    "import",
    "list",
    "search",
    "compare",
    "export",
    "dashboard",
    "nightly",
)


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="pip-app",
        description=(
            "Profile Intelligence Platform (PIP) — local-first desktop launcher"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "primary commands:\n"
            "  pip-app migrate\n"
            "  pip-app import <path>\n"
            "  pip-app list\n"
            "  pip-app search <query>\n"
            "  pip-app compare <id_a> <id_b>\n"
            "  pip-app export\n"
            "  pip-app dashboard\n"
            "  pip-app nightly\n"
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
        help="Optional settings YAML merged over config/settings.yaml",
    )

    subparsers = parser.add_subparsers(dest="command")

    # Primary command set
    subparsers.add_parser("migrate", help="Run database migrations and exit")

    import_parser = subparsers.add_parser(
        "import",
        help="Import profiles from a file (CSV/Excel/plugin formats)",
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

    search_parser = subparsers.add_parser(
        "search",
        help="Search stored profiles",
    )
    search_parser.add_argument("query", help="Search text")
    search_parser.add_argument("--limit", type=int, default=None, help="Max rows")

    compare_parser = subparsers.add_parser(
        "compare",
        help="Compare two profiles by id, or two sources",
    )
    compare_parser.add_argument(
        "left",
        nargs="?",
        default=None,
        help="Left profile id (or left source with --sources)",
    )
    compare_parser.add_argument(
        "right",
        nargs="?",
        default=None,
        help="Right profile id (or right source with --sources)",
    )
    compare_parser.add_argument(
        "--sources",
        nargs=2,
        metavar=("SOURCE_A", "SOURCE_B"),
        default=None,
        help="Compare aggregate stats for two source labels",
    )

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
        "dashboard",
        help="Show a local console dashboard summary",
    )

    nightly_parser = subparsers.add_parser(
        "nightly",
        help=(
            "Run nightly automation: import → update DB → rescore → "
            "Excel report → dashboard export"
        ),
    )
    nightly_parser.add_argument(
        "--import-dir",
        default=None,
        help="Inbox directory (default: config nightly.import_dir)",
    )
    nightly_parser.add_argument(
        "--excel-output",
        default=None,
        help="Excel report path (default: config nightly.excel_path)",
    )
    nightly_parser.add_argument(
        "--dashboard-output",
        default=None,
        help="Dashboard text path (default: config nightly.dashboard_path)",
    )
    nightly_parser.add_argument(
        "--no-rescore",
        action="store_true",
        help="Skip the recalculate scores stage",
    )
    nightly_parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recurse into subdirectories of the import inbox",
    )

    # Additional utilities
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

    list_parser = subparsers.add_parser("list", help="List stored profiles")
    list_parser.add_argument("--limit", type=int, default=50, help="Max rows")
    list_parser.add_argument("--offset", type=int, default=0, help="Offset")

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
        try:
            return _dispatch(command, args, container)
        finally:
            app.shutdown()
    except PipError as exc:
        logger.error("%s", exc)
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        logger.exception("Unexpected error")
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
) -> int:
    if command is None:
        app_name = container.resolve(ApplicationService).config.app.name
        logger.info("%s is ready.", app_name)
        print(app_name + " is ready.")
        print("Primary commands:")
        for name in _PRIMARY_COMMANDS:
            print(f"  pip-app {name}")
        return 0

    if command == "migrate":
        logger.info("Migrate complete")
        print("Migrations applied.")
        return 0

    if command == "importers":
        plugins = container.resolve(ApplicationService).importers.list_plugins()
        if not plugins:
            print("No importer plugins registered")
        else:
            for plugin in plugins:
                extensions = ", ".join(plugin.supported_extensions) or "n/a"
                line = (
                    f"{plugin.name} — {plugin.description or '(no description)'} "
                    f"(extensions={extensions})"
                )
                logger.info("Importer: %s", line)
                print(line)
        return 0

    if command == "seed":
        result = container.resolve(DatabaseSeeder).seed(
            only_if_empty=args.only_if_empty,
        )
        message = (
            f"Seeded profiles: created={result.created} "
            f"updated={result.updated} skipped={result.skipped}"
        )
        logger.info("%s", message)
        print(message)
        return 0

    if command == "import":
        summary = container.resolve(ImportService).import_path(
            args.path,
            source=args.source,
            plugin_name=args.plugin,
        )
        message = (
            f"Imported {summary.path} via {summary.plugin}: "
            f"created={summary.created} updated={summary.updated} "
            f"skipped={summary.skipped}"
        )
        logger.info("%s", message)
        print(message)
        for error in summary.errors:
            logger.warning("Import issue: %s", error)
            print(f"issue: {error}", file=sys.stderr)
        if (summary.created + summary.updated) > 0:
            return 0
        return 1 if summary.errors else 0

    if command == "compare":
        return _cmd_compare(args, container)

    if command == "dashboard":
        text = container.resolve(DashboardService).render_text()
        print(text)
        logger.info("Dashboard rendered (%d chars)", len(text))
        return 0

    if command == "nightly":
        return _cmd_nightly(args, container)

    profiles = container.resolve(ProfileService)

    if command == "list":
        rows = profiles.list_profiles(limit=args.limit, offset=args.offset)
        total = profiles.count()
        print(f"Showing {len(rows)} of {total} profile(s)")
        for profile in rows:
            print(_format_profile(profile))
        return 0

    if command == "search":
        rows = profiles.search(args.query, limit=args.limit)
        print(f"Found {len(rows)} profile(s) for {args.query!r}")
        for profile in rows:
            print(_format_profile(profile))
        return 0

    if command == "export":
        path = profiles.export_excel(args.output)
        message = f"Excel export written to {path}"
        logger.info("%s", message)
        print(message)
        return 0

    if command == "score":
        updated = profiles.rescore_all()
        message = f"Updated scores for {updated} profile(s)"
        logger.info("%s", message)
        print(message)
        return 0

    logger.error("Unknown command: %s", command)
    print(f"error: unknown command: {command}", file=sys.stderr)
    return 2


def _cmd_nightly(args: argparse.Namespace, container: Container) -> int:
    result = container.resolve(NightlyPipeline).run(
        import_dir=args.import_dir,
        excel_path=args.excel_output,
        dashboard_path=args.dashboard_output,
        rescore=False if args.no_rescore else None,
        recursive=True if args.recursive else None,
    )
    print("Nightly pipeline complete")
    print(f"  stages:   {' → '.join(result.stages_run)}")
    print(
        f"  import:   files={result.files_imported} "
        f"created={result.created} updated={result.updated} "
        f"skipped={result.skipped}"
    )
    print(f"  database: profiles={result.profile_count}")
    print(f"  scores:   rescored={result.rescored}")
    print(f"  excel:    {result.excel_path}")
    print(f"  dashboard: {result.dashboard_path}")
    for error in result.errors:
        print(f"issue: {error}", file=sys.stderr)
    return 0 if result.success else 1


def _cmd_compare(args: argparse.Namespace, container: Container) -> int:
    compare = container.resolve(CompareService)

    if args.sources is not None:
        left_source, right_source = args.sources
        for line in compare.compare_sources(left_source, right_source):
            print(line)
        return 0

    if args.left is None or args.right is None:
        print(
            "usage: pip-app compare <id_a> <id_b> | "
            "pip-app compare --sources SOURCE_A SOURCE_B",
            file=sys.stderr,
        )
        return 2

    try:
        left_id = int(args.left)
        right_id = int(args.right)
    except ValueError:
        print(
            "error: compare requires integer profile ids "
            "(or use --sources NAME_A NAME_B)",
            file=sys.stderr,
        )
        return 2

    result = compare.compare_ids(left_id, right_id)
    print(
        f"Compare [{result.left_id}] {result.left_name}  vs  "
        f"[{result.right_id}] {result.right_name}"
    )
    print(f"Differences: {len(result.differences)}  Matches: {len(result.matches)}")
    print("-" * 72)
    print(f"{'field':<14} {'left':<28} {'right':<28}")
    for item in result.fields:
        marker = " " if item.equal else "*"
        print(
            f"{marker}{item.field:<13} {item.left:<28} {item.right:<28}"
        )
    return 0


def _format_profile(profile: object) -> str:
    profile_id = getattr(profile, "id", "-")
    name = getattr(profile, "display_name", "-")
    email = getattr(profile, "email", None) or "-"
    organization = getattr(profile, "organization", None) or "-"
    score = getattr(profile, "score", None)
    score_text = str(score) if score is not None else "-"
    return f"[{profile_id}] {name} | {email} | {organization} | score={score_text}"


if __name__ == "__main__":
    raise SystemExit(main())
