"""Application launcher entrypoint."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from profile_intelligence import __version__
from profile_intelligence.bootstrap import build_container
from profile_intelligence.core.exceptions import PipError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.services.application import ApplicationService


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
    parser.add_argument(
        "--migrate-only",
        action="store_true",
        help="Run database migrations and exit",
    )
    parser.add_argument(
        "--list-importers",
        action="store_true",
        help="Discover and list importer plugins, then exit",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the application launcher. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        container = build_container(config_path=args.config_path)
        app = container.resolve(ApplicationService)
        app.start()
        logger = get_logger(__name__)

        if args.migrate_only:
            logger.info("Migrate-only mode complete")
            app.shutdown()
            return 0

        if args.list_importers:
            plugins = app.importers.list_plugins()
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
            app.shutdown()
            return 0

        logger.info(
            "%s is initialized. Desktop dashboard UI will attach in a later milestone.",
            app.config.app.name,
        )
        app.shutdown()
        return 0
    except PipError as exc:
        # Logging may not be configured if failure happened very early.
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"unexpected error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
