"""Import page."""

from __future__ import annotations

import html
from pathlib import Path

from profile_intelligence.core.exceptions import PipError
from profile_intelligence.ui.context import UiContext
from profile_intelligence.ui.layout import render_page


def render(
    ctx: UiContext,
    *,
    form: dict[str, str] | None = None,
    notice: str | None = None,
    error: str | None = None,
) -> str:
    """Render the import form and status."""
    form = form or {}
    path = form.get("path", "")
    source = form.get("source", "")
    plugin = form.get("plugin", "")
    recursive = form.get("recursive") == "1"

    plugins = ctx.importers.list_plugins()
    options = ['<option value="">Auto-detect</option>']
    for item in plugins:
        selected = " selected" if item.name == plugin else ""
        options.append(
            f'<option value="{html.escape(item.name)}"{selected}>'
            f"{html.escape(item.name)}</option>"
        )

    status = ""
    if notice:
        status = f'<p class="notice ok">{html.escape(notice)}</p>'
    elif error:
        status = f'<p class="notice err">{html.escape(error)}</p>'

    body = f"""
<section class="page-head">
  <h1>Import</h1>
  <p>Load profiles from a local file or folder into SQLite.</p>
</section>
{status}
<form class="form-grid" method="post" action="/import">
  <label>Path
    <input type="text" name="path" value="{html.escape(path)}" required placeholder="/path/to/profiles.csv">
  </label>
  <label>Source label (optional)
    <input type="text" name="source" value="{html.escape(source)}" placeholder="site-a">
  </label>
  <label>Plugin
    <select name="plugin">{"".join(options)}</select>
  </label>
  <label><input type="checkbox" name="recursive" value="1"{" checked" if recursive else ""}> Recurse folders</label>
  <div class="actions">
    <button class="btn" type="submit">Run import</button>
  </div>
</form>
"""
    return render_page(
        title="Import",
        active="import",
        body=body,
        app_name=ctx.config.app.name,
        version=ctx.config.app.version,
    )


def handle_post(ctx: UiContext, form: dict[str, str]) -> str:
    """Execute an import and re-render the page."""
    path_raw = form.get("path", "").strip()
    if not path_raw:
        return render(ctx, form=form, error="Path is required.")
    target = Path(path_raw).expanduser()
    if not target.exists():
        return render(ctx, form=form, error=f"Path not found: {target}")

    source = form.get("source", "").strip() or None
    plugin = form.get("plugin", "").strip() or None
    recursive = form.get("recursive") == "1"

    try:
        if target.is_dir():
            summary = ctx.imports.import_directory(
                target,
                source=source,
                plugin_name=plugin,
                recursive=recursive,
            )
        else:
            summary = ctx.imports.import_path(
                target,
                source=source,
                plugin_name=plugin,
            )
    except (OSError, PipError, ValueError) as exc:
        return render(ctx, form=form, error=str(exc))

    notice = (
        f"Import complete via {summary.plugin}: "
        f"created={summary.created} updated={summary.updated} "
        f"skipped={summary.skipped}"
    )
    return render(ctx, form=form, notice=notice)


def parse_form(body: bytes) -> dict[str, str]:
    """Parse application/x-www-form-urlencoded body into a flat dict."""
    from urllib.parse import parse_qs

    parsed: dict[str, list[str]] = parse_qs(body.decode("utf-8", errors="replace"))
    return {key: (values[0] if values else "") for key, values in parsed.items()}
