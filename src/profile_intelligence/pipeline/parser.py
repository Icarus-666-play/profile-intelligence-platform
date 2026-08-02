"""Parser stage: RawDocument → raw profile records."""

from __future__ import annotations

from profile_intelligence.core.exceptions import ImporterError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.importers.base import ImporterPlugin
from profile_intelligence.importers.registry import ImporterRegistry
from profile_intelligence.pipeline.documents import ParsedDocument, RawDocument

logger = get_logger(__name__)


class DocumentParser:
    """Parse a :class:`RawDocument` using a registered importer plugin."""

    def __init__(self, registry: ImporterRegistry) -> None:
        self._registry = registry

    def resolve_plugin(
        self,
        document: RawDocument,
        *,
        plugin: ImporterPlugin | None = None,
    ) -> ImporterPlugin:
        """Resolve the importer for *document*."""
        if plugin is not None:
            return plugin
        if document.plugin_name:
            return self._registry.get(document.plugin_name)
        found = self._registry.find_handler(document.path)
        if found is None:
            raise ImporterError(
                f"No importer plugin can handle file: {document.path}"
            )
        return found

    def parse(
        self,
        document: RawDocument,
        *,
        plugin: ImporterPlugin | None = None,
        **options: object,
    ) -> ParsedDocument:
        """Parser stage: produce raw records from *document*."""
        resolved_plugin = self.resolve_plugin(document, plugin=plugin)
        logger.info(
            "Parser stage: %s via '%s'",
            document.path,
            resolved_plugin.name,
        )
        result = resolved_plugin.import_file(document.path, **options)
        if not result.success:
            message = "; ".join(result.errors) or "Parse failed"
            raise ImporterError(message)

        parsed = ParsedDocument(
            document=document,
            plugin_name=resolved_plugin.name,
            records=tuple(dict(record) for record in result.records),
            records_read=result.records_read,
            records_skipped=result.records_skipped,
            errors=tuple(result.errors),
            metadata=dict(result.metadata),
        )
        logger.debug(
            "Parser stage complete: records=%d skipped=%d",
            len(parsed.records),
            parsed.records_skipped,
        )
        return parsed
