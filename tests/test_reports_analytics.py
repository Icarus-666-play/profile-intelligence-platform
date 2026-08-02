"""Reports panels: Countries, Prices, Languages, Services, Imports."""

from __future__ import annotations

import json
from pathlib import Path

from profile_intelligence.application.use_cases.application import ApplicationService
from profile_intelligence.bootstrap import build_container
from profile_intelligence.domain.entities.profile import ProfileDraft
from profile_intelligence.domain.interfaces.repositories import IProfileRepository
from profile_intelligence.domain.value_objects.profile_children import Rate, Service
from profile_intelligence.infrastructure.dashboard import ReportsAnalyticsService
from profile_intelligence.infrastructure.importers.import_ledger import ImportFileLedger


def test_reports_analytics_panels(temp_root: Path) -> None:
    container = build_container(root_dir=temp_root)
    app = container.resolve(ApplicationService)
    app.start()
    try:
        repo = container.resolve(IProfileRepository)
        raw_a = {
            "country": "Netherlands",
            "languages": "English, Dutch",
            "rates": [{"duration": "1 hour", "price": "300", "currency": "EUR"}],
        }
        raw_b = {
            "country": "France",
            "languages": ["French", "English"],
            "rates": [{"duration": "1 hour", "price": "250", "currency": "EUR"}],
        }
        left, _ = repo.upsert_draft(
            ProfileDraft(
                display_name="Ana Netherlands",
                location="Amsterdam, Netherlands",
                source="eurogirls",
                raw_json=json.dumps(raw_a),
                rates=(Rate(duration="1 hour", price="300", currency="EUR"),),
                services=(
                    Service(name="GFE"),
                    Service(name="Dinner date"),
                ),
            )
        )
        right, _ = repo.upsert_draft(
            ProfileDraft(
                display_name="Ana France",
                location="Paris, France",
                source="newwebsite",
                raw_json=json.dumps(raw_b),
                rates=(Rate(duration="1 hour", price="250", currency="EUR"),),
                services=(Service(name="GFE"),),
            )
        )
        assert left.id is not None and right.id is not None

        inbox = temp_root / "data" / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)
        imported = inbox / "batch.csv"
        imported.write_text("name\nX\n", encoding="utf-8")
        container.resolve(ImportFileLedger).mark_imported(imported)

        reports = container.resolve(ReportsAnalyticsService).build()
        country_names = {row.name for row in reports.countries}
        assert "Netherlands" in country_names
        assert "France" in country_names
        assert any(row.name == "English" for row in reports.languages)
        assert any(row.name == "GFE" and row.count >= 2 for row in reports.services)
        assert any(
            row.label == "1 hour" and row.average == 275.0
            for row in reports.average_prices
        )
        assert len(reports.monthly_imports) == 12
        assert sum(row.count for row in reports.monthly_imports) >= 1
        assert len(reports.import_trend) == 30
        assert sum(row.count for row in reports.import_trend) >= 1
        # Near-duplicate scan is best-effort; panel payload must always be present.
        assert isinstance(reports.duplicates, tuple)
    finally:
        app.shutdown()
