"""Plugins page."""

from __future__ import annotations

import html

from profile_intelligence.ui.context import UiContext
from profile_intelligence.ui.layout import render_page


def render(ctx: UiContext) -> str:
    """Render discovered importer plugins."""
    plugins = ctx.importers.list_plugins()
    if plugins:
        rows = "".join(
            "<div class='row'>"
            f"<span class='id'>plug</span>"
            f"<span>{html.escape(plugin.name)}</span>"
            f"<span class='meta'>{html.escape(plugin.description or '—')} · "
            f"{html.escape(', '.join(plugin.supported_extensions) or 'n/a')}</span>"
            "</div>"
            for plugin in plugins
        )
    else:
        rows = "<p class='notice'>No importer plugins discovered.</p>"

    body = f"""
<section class="page-head">
  <h1>Plugins</h1>
  <p>Importer plugins available to the local pipeline.</p>
</section>
<section class="section">
  <div class="stack">{rows}</div>
</section>
"""
    return render_page(
        title="Plugins",
        active="plugins",
        body=body,
        app_name=ctx.config.app.name,
        version=ctx.config.app.version,
    )
