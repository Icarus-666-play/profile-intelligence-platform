"""Search page."""

from __future__ import annotations

import html
from urllib.parse import parse_qs

from profile_intelligence.ui.context import UiContext
from profile_intelligence.ui.layout import render_page


def render(ctx: UiContext, *, query_string: str = "") -> str:
    """Render search form and optional results."""
    params = parse_qs(query_string)
    query = (params.get("q") or [""])[0].strip()
    results_html = ""
    if query:
        rows = ctx.profiles.search(query)
        if rows:
            items = "".join(
                "<div class='row'>"
                f"<span class='id'>#{row.id}</span>"
                f"<span>{html.escape(row.display_name)}</span>"
                f"<span class='meta'>{html.escape(row.source or '—')} · "
                f"confidence={html.escape(str(row.score if row.score is not None else '—'))}</span>"
                "</div>"
                for row in rows
            )
            results_html = (
                f"<section class='section'><h2>Results</h2>"
                f"<p>{len(rows)} match(es) for "
                f"<strong>{html.escape(query)}</strong></p>"
                f"<div class='stack'>{items}</div></section>"
            )
        else:
            results_html = (
                "<section class='section'><p class='notice'>"
                f"No matches for <strong>{html.escape(query)}</strong>."
                "</p></section>"
            )

    body = f"""
<section class="page-head">
  <h1>Search</h1>
  <p>Find profiles in the local SQLite database.</p>
</section>
<form class="form-grid" method="get" action="/search" role="search">
  <label>Query
    <input type="search" name="q" value="{html.escape(query)}" placeholder="name, email, org…" autofocus>
  </label>
  <div class="actions">
    <button class="btn" type="submit">Search</button>
  </div>
</form>
{results_html}
"""
    return render_page(
        title="Search",
        active="search",
        body=body,
        app_name=ctx.config.app.name,
        version=ctx.config.app.version,
    )
