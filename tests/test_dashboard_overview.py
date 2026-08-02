"""Dashboard KPIs: Profiles, Imported Today, Countries, Price, Rating + lists."""

from __future__ import annotations

from pathlib import Path

from profile_intelligence.application.use_cases.application import ApplicationService
from profile_intelligence.bootstrap import build_container
from profile_intelligence.domain.entities.profile import ProfileDraft
from profile_intelligence.domain.interfaces.repositories import (
    IProfileRepository,
    IRateRepository,
    IReviewRepository,
)
from profile_intelligence.domain.value_objects.profile_children import Rate, Review
from profile_intelligence.infrastructure.dashboard import DashboardService
from profile_intelligence.infrastructure.importers.import_ledger import ImportFileLedger


def test_dashboard_overview_kpis_and_panels(temp_root: Path) -> None:
    container = build_container(root_dir=temp_root)
    app = container.resolve(ApplicationService)
    app.start()
    try:
        repo = container.resolve(IProfileRepository)
        left, _ = repo.upsert_draft(
            ProfileDraft(
                display_name="Sofia",
                location="Amsterdam, Netherlands",
                source="eurogirls",
                score=88,
            )
        )
        right, _ = repo.upsert_draft(
            ProfileDraft(
                display_name="Clara",
                location="Paris, France",
                source="newwebsite",
                score=72,
            )
        )
        assert left.id is not None and right.id is not None

        rates = container.resolve(IRateRepository)
        rates.replace_for_profile(
            left.id,
            [
                Rate(duration="1 hour", price="300", currency="EUR"),
                Rate(duration="2 hours", price="€500", currency="EUR"),
            ],
        )
        reviews = container.resolve(IReviewRepository)
        reviews.replace_for_profile(
            left.id,
            [Review(text="Great", author="a", rating="4.8")],
        )
        reviews.replace_for_profile(
            right.id,
            [Review(text="Nice", author="b", rating="4.9")],
        )

        inbox = temp_root / "data" / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)
        queued = inbox / "waiting.csv"
        queued.write_text("name,email\nQueued,q@example.com\n", encoding="utf-8")
        imported = inbox / "done.csv"
        imported.write_text("name,email\nDone,d@example.com\n", encoding="utf-8")
        container.resolve(ImportFileLedger).mark_imported(imported)

        snapshot = container.resolve(DashboardService).snapshot()
        assert snapshot.total_profiles >= 2
        assert snapshot.imported_today >= 2
        assert snapshot.countries >= 2
        assert snapshot.average_price == 400.0
        assert snapshot.average_rating == 4.85
        assert any(row.display_name == "Sofia" for row in snapshot.newest_profiles)
        assert any(item.name == "done.csv" for item in snapshot.latest_imports)
        assert any(item.name == "waiting.csv" for item in snapshot.import_queue)

        payload_text = container.resolve(DashboardService).render_text(snapshot)
        assert "Imported today:" in payload_text
        assert "Average price:" in payload_text
    finally:
        app.shutdown()
