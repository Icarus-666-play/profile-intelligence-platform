"""Tests for Downloader → Parser → Extractor → Normalizer → Validator → Importer."""

from __future__ import annotations

from pathlib import Path

from profile_intelligence.application.pipeline.plugin_pipeline import (
    PLUGIN_PIPELINE_STAGES,
    PluginPipeline,
)
from profile_intelligence.domain.interfaces.plugin_pipeline import (
    StageValidationResult,
)
from profile_intelligence.domain.value_objects.importing import RawRecord
from profile_intelligence.infrastructure.download import DocumentDownloader


class _Parser:
    def parse(self, path: Path) -> dict[str, object]:
        text = path.read_text(encoding="utf-8")
        return {"text": text, "path": str(path)}


class _Extractor:
    def extract_many(self, document: object) -> list[object]:
        assert isinstance(document, dict)
        lines = [
            line.strip()
            for line in str(document["text"]).splitlines()
            if line.strip() and not line.startswith("name")
        ]
        rows: list[object] = []
        for line in lines:
            parts = line.split(",")
            rows.append(
                {
                    "name": parts[0].strip() if parts else "",
                    "email": parts[1].strip() if len(parts) > 1 else None,
                }
            )
        return rows


class _Normalizer:
    def normalize(
        self, extracted: object, document: object | None = None
    ) -> RawRecord:
        assert isinstance(extracted, dict)
        return {
            "name": extracted.get("name"),
            "display_name": extracted.get("name"),
            "email": extracted.get("email"),
            "source": "test",
        }


class _Validator:
    def validate(
        self,
        record: RawRecord,
        *,
        extracted: object | None = None,
    ) -> StageValidationResult:
        name = str(record.get("display_name") or "").strip()
        if not name:
            return StageValidationResult(ok=False, errors=("name is required",))
        return StageValidationResult(ok=True)


def test_plugin_pipeline_stage_order() -> None:
    assert PLUGIN_PIPELINE_STAGES == (
        "downloader",
        "parser",
        "extractor",
        "normalizer",
        "validator",
        "importer",
    )


def test_plugin_pipeline_run(tmp_path: Path) -> None:
    source = tmp_path / "people.csv"
    source.write_text(
        "name,email\nAda Lovelace,ada@example.com\n,\nbad@x\n",
        encoding="utf-8",
    )
    # second data row ",bad@x" has empty name → rejected by validator
    # third would be incomplete - actually lines: Ada, empty name line ",bad@x" wait
    # "\n,\nbad@x\n" → line "," → name empty; line "bad@x" → name bad@x
    source.write_text(
        "name,email\nAda Lovelace,ada@example.com\n,missing-name@example.com\n",
        encoding="utf-8",
    )

    pipeline = PluginPipeline(
        parser=_Parser(),
        extractor=_Extractor(),
        normalizer=_Normalizer(),
        validator=_Validator(),
    )
    result = pipeline.run(source)
    assert "parser" in result.stages_run
    assert "extractor" in result.stages_run
    assert "normalizer" in result.stages_run
    assert "validator" in result.stages_run
    assert "importer" in result.stages_run
    assert result.ok
    assert result.skipped >= 1
    assert any(row.get("display_name") == "Ada Lovelace" for row in result.records)


def test_document_downloader_local(tmp_path: Path) -> None:
    source = tmp_path / "doc.csv"
    source.write_text("name\nAda\n", encoding="utf-8")
    downloader = DocumentDownloader(tmp_path / "downloads", allow_remote=False)
    artifact = downloader.download(source)
    assert artifact.path.is_file()
    assert artifact.path.read_text(encoding="utf-8") == "name\nAda\n"

    pipeline = PluginPipeline(
        downloader=downloader,
        parser=_Parser(),
        extractor=_Extractor(),
        normalizer=_Normalizer(),
        validator=_Validator(),
    )
    result = pipeline.run(source)
    assert "downloader" in result.stages_run
    assert result.ok
