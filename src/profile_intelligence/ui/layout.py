"""HTML document shell for the Dashboard UI."""

from __future__ import annotations

import html
from pathlib import Path

from profile_intelligence.ui.navigation import NAV_ITEMS

_STATIC_DIR = Path(__file__).resolve().parent / "static"


def read_static(name: str) -> bytes:
    """Read a packaged static asset."""
    path = _STATIC_DIR / name
    return path.read_bytes()


def render_page(
    *,
    title: str,
    active: str,
    body: str,
    app_name: str,
    version: str,
) -> str:
    """Wrap page body in the shared application chrome."""
    nav = _render_nav(active)
    safe_title = html.escape(title)
    safe_app = html.escape(app_name)
    safe_version = html.escape(version)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title} · {safe_app}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=Manrope:wght@400;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
  <div class="app-shell">
    <aside class="sidebar">
      <div>
        <a class="brand-mark" href="/">{_brand_html(safe_app)}</a>
        <p class="brand-kicker">Local profile intelligence</p>
      </div>
      <nav aria-label="Primary">
        <ul class="nav-list">
          {nav}
        </ul>
      </nav>
      <p class="sidebar-foot">v{safe_version}<br>Local-first · SQLite</p>
    </aside>
    <main class="main">
      {body}
    </main>
  </div>
  <script src="/static/app.js"></script>
</body>
</html>
"""


def _brand_html(escaped_name: str) -> str:
    """Split a long product name for the sidebar brand mark."""
    if escaped_name.endswith(" Platform"):
        head = escaped_name[: -len(" Platform")]
        return f"{head}<span>Platform</span>"
    return escaped_name


def _render_nav(active: str) -> str:
    items: list[str] = []
    for item in NAV_ITEMS:
        cls = ' class="is-active"' if item.key == active else ""
        label = html.escape(item.label)
        path = html.escape(item.path)
        items.append(f'<li><a href="{path}"{cls}>{label}</a></li>')
    return "\n".join(items)


__all__ = ["read_static", "render_page"]
