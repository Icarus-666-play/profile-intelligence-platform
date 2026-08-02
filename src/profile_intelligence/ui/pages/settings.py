"""Settings page."""

from __future__ import annotations

import html

from profile_intelligence.ui.context import UiContext
from profile_intelligence.ui.layout import render_page


def render(ctx: UiContext) -> str:
    """Render a read-only settings snapshot."""
    cfg = ctx.config
    rows = [
        ("App", cfg.app.name),
        ("Version", cfg.app.version),
        ("Environment", cfg.app.environment),
        ("Database", str(cfg.database_path)),
        ("Data dir", str(cfg.data_dir)),
        ("Logs dir", str(cfg.logs_dir)),
        ("Exports dir", str(cfg.exports_dir)),
        ("Plugins dir", str(cfg.plugins_dir)),
        ("AI enabled", str(cfg.ai.enabled)),
        ("AI provider", str(cfg.ai.provider or "null")),
        ("Cache backend", cfg.cache.backend),
        ("Search limit", str(cfg.search.default_limit)),
        ("Dashboard refresh (s)", str(cfg.dashboard.refresh_seconds)),
        ("Daily import folder", cfg.daily.import_dir),
        ("Daily excel path", cfg.daily.excel_path),
        ("Daily dashboard path", cfg.daily.dashboard_path),
    ]
    items = "".join(
        f"<dt>{html.escape(label)}</dt><dd>{html.escape(value)}</dd>"
        for label, value in rows
    )
    body = f"""
<section class="page-head">
  <h1>Settings</h1>
  <p>Active local configuration (read-only). Edit YAML under <code>config/</code>.</p>
</section>
<section class="section">
  <dl class="kv">{items}</dl>
</section>
"""
    return render_page(
        title="Settings",
        active="settings",
        body=body,
        app_name=cfg.app.name,
        version=cfg.app.version,
    )
