"""Tests for profile analysis toolkit."""

from __future__ import annotations

from dataclasses import dataclass

import profile_intelligence.main as main_module
from profile_intelligence.application.use_cases.application import ApplicationService
from profile_intelligence.bootstrap import build_container
from profile_intelligence.domain.entities.profile import ProfileDraft
from profile_intelligence.domain.interfaces.repositories import IProfileRepository
from profile_intelligence.infrastructure.analysis import (
    AnalysisService,
    ProfileClassifier,
    ProfileDuplicateAnalyzer,
    ProfileRecommender,
    ProfileSimilarityAnalyzer,
    ProfileSummarizer,
)
from profile_intelligence.main import build_parser, main


@dataclass
class _FakeProfile:
    id: int | None
    display_name: str
    email: str | None = None
    phone: str | None = None
    title: str | None = None
    organization: str | None = None
    location: str | None = None
    tags: str | None = None
    notes: str | None = None
    external_id: str | None = None
    source: str | None = None
    score: int | None = None


def test_similarity_and_recommendation() -> None:
    left = _FakeProfile(
        id=1,
        display_name="Ada Lovelace",
        email="ada@example.com",
        organization="Analytical Engines",
        location="London",
        tags="math,engines",
        source="test",
    )
    right = _FakeProfile(
        id=2,
        display_name="Ada Lovelace",
        email="ada@example.com",
        organization="Analytical Engines",
        location="London",
        tags="math",
        source="test",
    )
    other = _FakeProfile(
        id=3,
        display_name="Grace Hopper",
        email="grace@example.com",
        source="navy",
    )

    similarity = ProfileSimilarityAnalyzer()
    score = similarity.score(left, right, left_id=1, right_id=2)
    assert score.value >= 0.75
    assert "display_name" in score.matched_fields

    recs = ProfileRecommender(similarity, min_score=0.3).recommend(
        left,  # type: ignore[arg-type]
        [left, right, other],  # type: ignore[list-item]
        limit=5,
    )
    assert len(recs) == 1
    assert recs[0].profile_id == 2


def test_summarization_classification_duplicates() -> None:
    rich = _FakeProfile(
        id=1,
        display_name="Ada",
        email="ada@example.com",
        phone="1",
        title="Analyst",
        organization="AE",
        location="London",
        tags="math",
        notes="note",
        external_id="a1",
        source="eurogirls",
        score=90,
    )
    twin = _FakeProfile(
        id=2,
        display_name="Ada",
        email="ada@example.com",
        phone="1",
        title="Analyst",
        organization="AE",
        location="London",
        tags="math",
        notes="note",
        external_id="a1",
        source="eurogirls",
        score=88,
    )
    sparse = _FakeProfile(id=3, display_name="Bob", source="custom", score=10)

    summary = ProfileSummarizer().summarize(rich)  # type: ignore[arg-type]
    assert summary.source == "heuristic"
    assert "Ada" in summary.text
    assert "London" in summary.text

    classified = ProfileClassifier().classify(rich)  # type: ignore[arg-type]
    assert classified.confidence_band == "high"
    assert classified.completeness_class == "rich"
    assert "source:eurogirls" in classified.labels

    result = ProfileDuplicateAnalyzer(threshold=0.7).analyze(
        [rich, twin, sparse]  # type: ignore[list-item]
    )
    assert result.scanned == 3
    assert len(result.pairs) >= 1
    assert len(result.groups) == 1
    assert set(result.groups[0].profile_ids) == {1, 2}


def test_analysis_service_end_to_end(temp_root: object) -> None:
    from pathlib import Path

    assert isinstance(temp_root, Path)
    container = build_container(root_dir=temp_root)
    app = container.resolve(ApplicationService)
    app.start()

    repo = container.resolve(IProfileRepository)
    first, _ = repo.upsert_draft(
        ProfileDraft(
            display_name="Ada Lovelace",
            external_id="ada-1",
            email="ada@example.com",
            organization="AE",
            location="London",
            tags="math",
            source="site-a",
            score=80,
        )
    )
    second, _ = repo.upsert_draft(
        ProfileDraft(
            display_name="Ada Lovelace",
            external_id="ada-2",
            email="ada@example.com",
            organization="AE",
            location="London",
            tags="math,engines",
            source="site-b",
            score=75,
        )
    )
    assert first.id is not None
    assert second.id is not None

    analysis = container.resolve(AnalysisService)
    score = analysis.similarity(first.id, second.id)
    assert score.value > 0.5
    assert analysis.summarize(first.id).text
    assert analysis.classify(first.id).source_class == "site-a"
    assert analysis.recommend(first.id)
    dups = analysis.find_duplicates(threshold=0.6)
    assert dups.scanned >= 2

    app.shutdown()


def test_parser_analyze_subcommands() -> None:
    parser = build_parser()
    args = parser.parse_args(["analyze", "similarity", "1", "2"])
    assert args.command == "analyze"
    assert args.analyze_command == "similarity"
    assert args.left_id == 1
    assert args.right_id == 2


def test_cli_analyze_summarize(
    temp_root: object,
    monkeypatch: object,
    capsys: object,
) -> None:
    from pathlib import Path

    assert isinstance(temp_root, Path)
    container = build_container(root_dir=temp_root)
    app = container.resolve(ApplicationService)
    app.start()
    repo = container.resolve(IProfileRepository)
    entity, _ = repo.upsert_draft(
        ProfileDraft(display_name="Ada", email="ada@example.com", source="test")
    )
    app.shutdown()
    assert entity.id is not None

    original = build_container

    def _build(*args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        kwargs.setdefault("root_dir", temp_root)
        return original(*args, **kwargs)

    monkeypatch.setattr(main_module, "build_container", _build)  # type: ignore[attr-defined]
    assert main(["analyze", "summarize", str(entity.id)]) == 0
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "Ada" in out
