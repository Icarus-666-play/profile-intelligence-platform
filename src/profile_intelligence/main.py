"""Application launcher entrypoint.

Primary commands::

    pip-app migrate
    pip-app import
    pip-app search
    pip-app compare
    pip-app export
    pip-app dashboard
    pip-app ui
    pip-app daily
    pip-app analyze
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from profile_intelligence import __version__
from profile_intelligence.api import ApiContext, serve_fastapi
from profile_intelligence.application.use_cases.application import ApplicationService
from profile_intelligence.application.use_cases.compare_service import CompareService
from profile_intelligence.application.use_cases.daily_pipeline import DailyPipeline
from profile_intelligence.application.use_cases.import_flow import ImportFlow
from profile_intelligence.application.use_cases.import_service import ImportService
from profile_intelligence.application.use_cases.profile_service import ProfileService
from profile_intelligence.bootstrap import build_container
from profile_intelligence.core.config import AppConfig
from profile_intelligence.core.container import Container
from profile_intelligence.core.exceptions import PipError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.domain.interfaces.repositories import IProfileRepository
from profile_intelligence.infrastructure.analysis import AnalysisService
from profile_intelligence.infrastructure.auth import LocalAuthService
from profile_intelligence.infrastructure.dashboard import DashboardService
from profile_intelligence.infrastructure.database.seed import DatabaseSeeder
from profile_intelligence.infrastructure.download import DocumentDownloader
from profile_intelligence.infrastructure.importers.import_activity import (
    ImportActivityStore,
)
from profile_intelligence.infrastructure.importers.registry import ImporterRegistry
from profile_intelligence.ui import UiContext, serve_ui

logger = get_logger(__name__)

_PRIMARY_COMMANDS = (
    "migrate",
    "import",
    "list",
    "search",
    "compare",
    "export",
    "dashboard",
    "ui",
    "daily",
    "nightly",
    "analyze",
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
            "  pip-app ui\n"
            "  pip-app daily\n"
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
        help="Import profiles from a file or directory",
    )
    import_parser.add_argument(
        "path",
        help="Path to a file or directory to import",
    )
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
    import_parser.add_argument(
        "--recursive",
        action="store_true",
        help="When path is a directory, recurse into subfolders",
    )
    import_mode = import_parser.add_mutually_exclusive_group()
    import_mode.add_argument(
        "--input",
        action="store_true",
        dest="import_input_only",
        help="Input stage only: resolve path and plugin",
    )
    import_mode.add_argument(
        "--preview",
        action="store_true",
        help="Preview stage: dry-run rows (no database write)",
    )
    import_mode.add_argument(
        "--validate",
        action="store_true",
        dest="import_validate_only",
        help="Validate stage: gate check before Import",
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

    ui_parser = subparsers.add_parser(
        "ui",
        help=(
            "Open React + FastAPI (Browser → React → REST → FastAPI → "
            "Application → Repository → SQLite → File Storage)"
        ),
    )
    ui_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind host (default: 127.0.0.1)",
    )
    ui_parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Bind port (default: 8765)",
    )
    ui_parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open a system browser",
    )
    ui_parser.add_argument(
        "--legacy-wsgi",
        action="store_true",
        help="Serve the legacy stdlib WSGI HTML UI instead of React+FastAPI",
    )

    daily_parser = subparsers.add_parser(
        "daily",
        help=(
            "Run Daily automation: Import Folder → Detect new files → "
            "Import → Update → Generate Excel → Create Dashboard → "
            "Email Report (future)"
        ),
    )
    _add_daily_arguments(daily_parser)

    nightly_parser = subparsers.add_parser(
        "nightly",
        help="Alias for pip-app daily (backward compatible)",
    )
    _add_daily_arguments(nightly_parser)

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
        help="Recompute Confidence Scores (0-100) for all profiles",
    )

    analyze_parser = subparsers.add_parser(
        "analyze",
        help=(
            "Profile analysis: similarity, recommendation, summarization, "
            "classification, duplicates"
        ),
    )
    analyze_sub = analyze_parser.add_subparsers(dest="analyze_command")
    sim_parser = analyze_sub.add_parser(
        "similarity",
        help="Score similarity between two profiles",
    )
    sim_parser.add_argument("left_id", type=int)
    sim_parser.add_argument("right_id", type=int)
    rec_parser = analyze_sub.add_parser(
        "recommend",
        help="Recommend similar profiles",
    )
    rec_parser.add_argument("profile_id", type=int)
    rec_parser.add_argument("--limit", type=int, default=5)
    sum_parser = analyze_sub.add_parser(
        "summarize",
        help="Summarize one profile",
    )
    sum_parser.add_argument("profile_id", type=int)
    cls_parser = analyze_sub.add_parser(
        "classify",
        help="Classify one profile (or all with --all)",
    )
    cls_parser.add_argument("profile_id", type=int, nargs="?", default=None)
    cls_parser.add_argument(
        "--all",
        action="store_true",
        dest="classify_all",
        help="Classify all stored profiles",
    )
    dup_parser = analyze_sub.add_parser(
        "duplicates",
        help="Find near-duplicate profiles",
    )
    dup_parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Similarity threshold 0.0-1.0 (default 0.75)",
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
        return _cmd_import(args, container)

    if command == "compare":
        return _cmd_compare(args, container)

    if command == "dashboard":
        text = container.resolve(DashboardService).render_text()
        print(text)
        logger.info("Dashboard rendered (%d chars)", len(text))
        return 0

    if command == "ui":
        return _cmd_ui(args, container)

    if command in {"daily", "nightly"}:
        return _cmd_daily(args, container, label=command)

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
        message = f"Updated confidence scores for {updated} profile(s)"
        logger.info("%s", message)
        print(message)
        return 0

    if command == "analyze":
        return _cmd_analyze(args, container)

    logger.error("Unknown command: %s", command)
    print(f"error: unknown command: {command}", file=sys.stderr)
    return 2


def _cmd_analyze(args: argparse.Namespace, container: Container) -> int:
    analysis = container.resolve(AnalysisService)
    action = getattr(args, "analyze_command", None)
    if action is None:
        print(
            "usage: pip-app analyze {similarity,recommend,summarize,"
            "classify,duplicates}",
            file=sys.stderr,
        )
        return 2

    if action == "similarity":
        score = analysis.similarity(args.left_id, args.right_id)
        print(
            f"similarity={score.value:.2f} ({score.percent}%) "
            f"matched={','.join(score.matched_fields) or '-'}"
        )
        return 0

    if action == "recommend":
        rows = analysis.recommend(args.profile_id, limit=args.limit)
        print(f"Recommendations for id={args.profile_id}: {len(rows)}")
        for row in rows:
            print(
                f"  [{row.profile_id}] {row.display_name} "
                f"score={row.score.value:.2f} — {row.reason}"
            )
        return 0

    if action == "summarize":
        summary = analysis.summarize(args.profile_id)
        print(f"[{summary.profile_id}] {summary.display_name} ({summary.source})")
        print(summary.text)
        return 0

    if action == "classify":
        if args.classify_all:
            rows = analysis.classify_all()
            print(f"Classified {len(rows)} profile(s)")
            for row in rows:
                print(
                    f"  [{row.profile_id}] {row.display_name} "
                    f"{' '.join(row.labels)}"
                )
            return 0
        if args.profile_id is None:
            print(
                "usage: pip-app analyze classify <profile_id> | --all",
                file=sys.stderr,
            )
            return 2
        row = analysis.classify(args.profile_id)
        print(f"[{row.profile_id}] {row.display_name}")
        print(" ".join(row.labels))
        return 0

    if action == "duplicates":
        result = analysis.find_duplicates(threshold=args.threshold)
        print(
            f"Scanned {result.scanned} profile(s): "
            f"pairs={len(result.pairs)} groups={len(result.groups)}"
        )
        for group in result.groups:
            print(f"  group: {', '.join(str(item) for item in group.profile_ids)}")
        return 0

    print(f"error: unknown analyze command: {action}", file=sys.stderr)
    return 2


def _add_daily_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--import-dir",
        default=None,
        help="Import folder (default: config daily.import_dir)",
    )
    parser.add_argument(
        "--excel-output",
        default=None,
        help="Excel report path (default: config daily.excel_path)",
    )
    parser.add_argument(
        "--dashboard-output",
        default=None,
        help="Dashboard text path (default: config daily.dashboard_path)",
    )
    parser.add_argument(
        "--no-rescore",
        action="store_true",
        help="Skip confidence rescoring inside the Update stage",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recurse into subdirectories of the import folder",
    )
    parser.add_argument(
        "--force-all-files",
        action="store_true",
        help="Import all detected files, ignoring the new-file ledger",
    )


def _cmd_import(args: argparse.Namespace, container: Container) -> int:
    """Run Input → Preview → Validate → Import (or a single stage)."""
    flow = container.resolve(ImportFlow)
    target = Path(args.path)
    source = args.source
    plugin = args.plugin

    if args.import_input_only:
        resolved = flow.resolve_input(
            target, source=source, plugin_name=plugin
        )
        print("Import flow: Input")
        print(f"  path:   {resolved.path}")
        print(f"  plugin: {resolved.plugin or '(none)'}")
        print(f"  source: {resolved.source or '(default)'}")
        print(f"  ok:     {resolved.ok}")
        for error in resolved.errors:
            print(f"issue: {error}", file=sys.stderr)
        return 0 if resolved.ok else 1

    if args.preview:
        preview = flow.preview(target, source=source, plugin_name=plugin)
        print("Import flow: Preview")
        print(f"  path:     {preview.path}")
        print(f"  plugin:   {preview.plugin}")
        print(f"  records:  {preview.records_read}")
        print(
            f"  accepted: {preview.accepted_count}  "
            f"rejected: {preview.rejected_count}  "
            f"duplicates: {preview.duplicate_count}  "
            f"updates: {preview.update_count}"
        )
        for row in preview.rows[:50]:
            score = row.score if row.score is not None else "-"
            print(
                f"  [{row.index}] {row.display_name} | "
                f"{row.status} | confidence={score}"
            )
        for error in preview.errors:
            print(f"issue: {error}", file=sys.stderr)
        return 0 if preview.ok else 1

    if args.import_validate_only:
        gate = flow.validate(target, source=source, plugin_name=plugin)
        print("Import flow: Validate")
        print(f"  path:     {gate.path}")
        print(f"  plugin:   {gate.plugin}")
        print(f"  ok:       {gate.ok}")
        print(f"  accepted: {gate.accepted}  rejected: {gate.rejected}")
        for issue in gate.issues:
            prefix = "warning" if issue.severity == "warning" else "issue"
            loc = f"row {issue.index}: " if issue.index is not None else ""
            print(f"{prefix}: {loc}{issue.message}", file=sys.stderr)
        return 0 if gate.ok else 1

    # Import stage (full persist)
    summary = flow.run_import(
        target,
        source=source,
        plugin_name=plugin,
        recursive=bool(args.recursive),
    )
    report = summary.render_report()
    logger.info("%s", report.replace("\n", " | "))
    print("Import flow: Import")
    print(report)
    detail = (
        f"via {summary.plugin}: created={summary.created} "
        f"updated={summary.updated} skipped={summary.skipped}"
    )
    logger.info("Import detail %s %s", summary.path, detail)
    print()
    print(detail)
    for error in summary.errors:
        logger.warning("Import issue: %s", error)
        print(f"issue: {error}", file=sys.stderr)
    if (summary.created + summary.updated) > 0:
        return 0
    return 1 if summary.errors else 0


def _cmd_ui(args: argparse.Namespace, container: Container) -> int:
    api_context = ApiContext(
        config=container.resolve(AppConfig),
        profiles=container.resolve(ProfileService),
        repository=container.resolve(IProfileRepository),
        imports=container.resolve(ImportService),
        import_flow=container.resolve(ImportFlow),
        compare=container.resolve(CompareService),
        dashboard=container.resolve(DashboardService),
        analysis=container.resolve(AnalysisService),
        importers=container.resolve(ImporterRegistry),
        downloader=container.resolve(DocumentDownloader),
        auth=container.resolve(LocalAuthService),
        import_activity=container.resolve(ImportActivityStore),
    )
    if bool(getattr(args, "legacy_wsgi", False)):
        context = UiContext(
            config=container.resolve(AppConfig),
            dashboard=container.resolve(DashboardService),
            profiles=container.resolve(ProfileService),
            imports=container.resolve(ImportService),
            compare=container.resolve(CompareService),
            importers=container.resolve(ImporterRegistry),
            import_flow=container.resolve(ImportFlow),
        )
        serve_ui(
            context,
            host=str(args.host),
            port=int(args.port),
            open_browser=not bool(args.no_browser),
            api_context=api_context,
        )
        return 0

    serve_fastapi(
        api_context,
        host=str(args.host),
        port=int(args.port),
        open_browser=not bool(args.no_browser),
    )
    return 0


def _cmd_daily(
    args: argparse.Namespace,
    container: Container,
    *,
    label: str = "daily",
) -> int:
    result = container.resolve(DailyPipeline).run(
        import_dir=args.import_dir,
        excel_path=args.excel_output,
        dashboard_path=args.dashboard_output,
        rescore=False if args.no_rescore else None,
        recursive=True if args.recursive else None,
        force_all_files=bool(getattr(args, "force_all_files", False)),
    )
    title = "Daily" if label == "daily" else "Nightly (Daily alias)"
    print(f"{title} pipeline complete")
    print(f"  stages:   {' → '.join(result.stages_run)}")
    print(f"  folder:   {result.import_folder}")
    print(
        f"  detect:   candidates={result.files_detected} "
        f"new={result.files_new}"
    )
    print(
        f"  import:   files={result.files_imported} "
        f"created={result.created} updated={result.updated} "
        f"skipped={result.skipped}"
    )
    print(f"  update:   profiles={result.profile_count} rescored={result.rescored}")
    print(f"  excel:    {result.excel_path}")
    print(f"  dashboard: {result.dashboard_path}")
    print(
        f"  email:    "
        f"{'sent' if result.email_sent else 'skipped'} "
        f"({result.email_message or 'n/a'})"
    )
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
    return (
        f"[{profile_id}] {name} | {email} | {organization} | "
        f"confidence={score_text}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
