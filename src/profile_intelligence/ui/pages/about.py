"""About page."""

from __future__ import annotations

import html

from profile_intelligence import __version__
from profile_intelligence.ui.context import UiContext
from profile_intelligence.ui.layout import render_page


def render(ctx: UiContext) -> str:
    """Render application identity."""
    app = ctx.config.app
    body = f"""
<section class="page-head">
  <h1 class="hero-brand">{html.escape(app.name).replace(" Platform", "<em> Platform</em>")}</h1>
  <p>Local-first desktop profile analysis for import, search, scoring, and Excel reporting.</p>
</section>
<section class="section">
  <dl class="kv">
    <dt>Product</dt><dd>{html.escape(app.name)}</dd>
    <dt>Short name</dt><dd>{html.escape(app.short_name)}</dd>
    <dt>Version</dt><dd>{html.escape(app.version)} <span class="meta">(package {html.escape(__version__)})</span></dd>
    <dt>Runtime</dt><dd>Python 3.12 · SQLite · local UI</dd>
    <dt>CLI</dt><dd>pip-app ui · pip-app dashboard · pip-app daily</dd>
  </dl>
</section>
"""
    return render_page(
        title="About",
        active="about",
        body=body,
        app_name=app.name,
        version=app.version,
    )
