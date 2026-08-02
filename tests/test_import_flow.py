"""Tests for Input → Preview → Validate → Import operator flow."""

from __future__ import annotations

from pathlib import Path

from profile_intelligence.application.use_cases.application import ApplicationService
from profile_intelligence.application.use_cases.import_flow import ImportFlow
from profile_intelligence.bootstrap import build_container
from profile_intelligence.domain.value_objects.import_flow import IMPORT_FLOW_STAGES
from profile_intelligence.main import build_parser


def test_import_flow_stages_constant() -> None:
    assert IMPORT_FLOW_STAGES == ("input", "preview", "validate", "import")
    assert ImportFlow.stages == IMPORT_FLOW_STAGES


def test_preview_row_includes_detail_fields(temp_root: Path) -> None:
    container = build_container(root_dir=temp_root)
    app = container.resolve(ApplicationService)
    app.start()
    try:
        csv_path = temp_root / "rich.csv"
        csv_path.write_text(
            "name,email,age,nationality,languages,rates,services,reviews,photos\n"
            'Sofia,sofia@example.com,28,Italian,"English, Italian",'
            '"[{""duration"":""1 hour"",""price"":""300"",""currency"":""EUR""}]",'
            '"[{""name"":""GFE""}]",'
            '"[{""author"":""A"",""rating"":""4.8"",""text"":""Nice""}]",'
            '"[{""original_url"":""https://example.com/sofia.jpg"",""role"":""main""}]"\n',
            encoding="utf-8",
        )
        # CSV importer may not parse nested JSON columns — seed via raw pipeline path.
        from profile_intelligence.application.use_cases.import_flow import (
            _preview_row_from_draft,
        )
        from profile_intelligence.domain.entities.profile import ProfileDraft
        from profile_intelligence.domain.value_objects.profile_children import (
            Photo,
            Rate,
            Review,
            Service,
        )

        draft = ProfileDraft(
            display_name="Sofia",
            location="Amsterdam, Netherlands",
            source="eurogirls",
            raw_json=(
                '{"age":"28","nationality":"Italian",'
                '"languages":"English, Italian"}'
            ),
            rates=(Rate(duration="1 hour", price="300", currency="EUR"),),
            services=(Service(name="GFE"),),
            reviews=(Review(author="A", rating="4.8", text="Nice"),),
            photos=(
                Photo(
                    original_url="https://example.com/sofia.jpg",
                    role="main",
                ),
            ),
            score=80,
        )
        row = _preview_row_from_draft(draft, index=1, status="ok")
        assert row.display_name == "Sofia"
        assert row.age == "28"
        assert row.nationality == "Italian"
        assert "English" in row.languages
        assert row.services == ("GFE",)
        assert any("300" in item for item in row.rates)
        assert any("4.8" in item for item in row.reviews)
        assert row.picture == "https://example.com/sofia.jpg"
        assert row.pictures == ("https://example.com/sofia.jpg",)
    finally:
        app.shutdown()


def test_input_preview_validate_import(temp_root: Path) -> None:
    container = build_container(root_dir=temp_root)
    app = container.resolve(ApplicationService)
    app.start()
    try:
        csv_path = temp_root / "flow_people.csv"
        csv_path.write_text(
            "name,email,organization\n"
            "Ada Lovelace,ada@example.com,AE\n"
            ",bad-email,\n",
            encoding="utf-8",
        )

        flow = container.resolve(ImportFlow)

        resolved = flow.resolve_input(csv_path)
        assert resolved.ok
        assert resolved.plugin == "csv"

        preview = flow.preview(csv_path)
        assert preview.records_read >= 1
        assert preview.accepted_count >= 1
        assert any(row.status == "ok" for row in preview.rows)

        gate = flow.validate(csv_path)
        assert gate.ok
        assert gate.accepted >= 1

        summary = flow.run_import(csv_path)
        assert summary.created >= 1
        assert summary.written >= 1
    finally:
        app.shutdown()


def test_preview_does_not_persist(temp_root: Path) -> None:
    container = build_container(root_dir=temp_root)
    app = container.resolve(ApplicationService)
    app.start()
    try:
        csv_path = temp_root / "preview_only.csv"
        csv_path.write_text(
            "name,email\nGrace Hopper,grace@example.com\n",
            encoding="utf-8",
        )
        flow = container.resolve(ImportFlow)
        preview = flow.preview(csv_path)
        assert preview.ok
        from profile_intelligence.application.use_cases.profile_service import (
            ProfileService,
        )

        assert container.resolve(ProfileService).count() == 0
    finally:
        app.shutdown()


def test_parser_import_flow_flags() -> None:
    parser = build_parser()
    args = parser.parse_args(["import", "file.csv", "--preview"])
    assert args.preview is True
    args = parser.parse_args(["import", "file.csv", "--validate"])
    assert args.import_validate_only is True
    args = parser.parse_args(["import", "file.csv", "--input"])
    assert args.import_input_only is True
