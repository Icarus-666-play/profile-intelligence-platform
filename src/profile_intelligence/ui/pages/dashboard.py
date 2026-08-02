"""Dashboard home page."""

from __future__ import annotations

import html
from collections.abc import Sequence

from profile_intelligence.domain.interfaces.repositories import ProfileEntity
from profile_intelligence.ui.context import UiContext
from profile_intelligence.ui.layout import render_page


def render(ctx: UiContext) -> str:
    """Render the Dashboard overview."""
    snap = ctx.dashboard.snapshot()
    app_name = ctx.config.app.name
    avg = snap.average_score
    avg_label = f"{avg:.1f}" if avg is not None else "n/a"
    avg_count = f"{avg:.1f}" if avg is not None else ""

    sources = "".join(
        f"<li>{html.escape(source)} · {count}</li>"
        for source, count in snap.by_source[:8]
    ) or "<li>No sources yet</li>"

    top = _profile_rows(snap.top_profiles) or (
        '<p class="notice">No profiles yet. Use Import to load local files.</p>'
    )
    needs = _profile_rows(snap.incomplete_profiles) or (
        '<p class="notice">Nothing needs attention.</p>'
    )

    brand = html.escape(app_name)
    if brand.endswith(" Platform"):
        brand_html = f"{brand[: -len(' Platform')]}<em> Platform</em>"
    else:
        brand_html = brand

    body = f"""
<section class="page-head">
  <h1 class="hero-brand">{brand_html}</h1>
  <p>Dashboard — local overview of stored profiles, confidence scores, and sources.</p>
</section>

<section class="metrics" aria-label="Key metrics">
  <div>
    <span class="metric-label">Profiles</span>
    <span class="metric-value" data-count="{snap.total_profiles}">{snap.total_profiles}</span>
  </div>
  <div>
    <span class="metric-label">Scored</span>
    <span class="metric-value" data-count="{snap.scored_profiles}">{snap.scored_profiles}</span>
  </div>
  <div>
    <span class="metric-label">Avg confidence</span>
    <span class="metric-value"{f' data-count="{avg_count}"' if avg_count else ""}>{avg_label}</span>
  </div>
</section>

<section class="section">
  <h2>By source</h2>
  <ul class="pill-list">{sources}</ul>
</section>

<section class="section">
  <h2>Top confidence</h2>
  <div class="stack">{top}</div>
</section>

<section class="section">
  <h2>Needs attention</h2>
  <div class="stack">{needs}</div>
</section>
"""
    return render_page(
        title="Dashboard",
        active="dashboard",
        body=body,
        app_name=app_name,
        version=ctx.config.app.version,
    )


def _profile_rows(profiles: Sequence[ProfileEntity]) -> str:
    rows: list[str] = []
    for profile in profiles:
        score = profile.score if profile.score is not None else "—"
        rows.append(
            "<div class='row'>"
            f"<span class='id'>#{profile.id}</span>"
            f"<span>{html.escape(profile.display_name)}</span>"
            f"<span class='meta'>{html.escape(profile.source or '—')} · "
            f"confidence={html.escape(str(score))}</span>"
            "</div>"
        )
    return "".join(rows)
