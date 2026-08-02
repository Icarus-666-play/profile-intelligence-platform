"""Reports page."""

from __future__ import annotations

import html
from pathlib import Path

from profile_intelligence.core.exceptions import PipError
from profile_intelligence.ui.context import UiContext
from profile_intelligence.ui.layout import render_page


def render(
    ctx: UiContext,
    *,
    notice: str | None = None,
    error: str | None = None,
) -> str:
    """Render reports / Excel export controls."""
    exports_dir = ctx.config.exports_dir
    files = _list_exports(exports_dir)
    file_rows = "".join(
        f"<div class='row'><span class='id'>xlsx</span>"
        f"<span>{html.escape(path.name)}</span>"
        f"<span class='meta'>{html.escape(str(path.stat().st_size))} bytes</span></div>"
        for path in files
    ) or "<p class='notice'>No export files yet.</p>"

    status = ""
    if notice:
        status = f'<p class="notice ok">{html.escape(notice)}</p>'
    elif error:
        status = f'<p class="notice err">{html.escape(error)}</p>'

    body = f"""
<section class="page-head">
  <h1>Reports</h1>
  <p>Generate Excel workbooks from the local profile database.</p>
</section>
{status}
<form method="post" action="/reports">
  <div class="actions">
    <button class="btn" type="submit" name="action" value="export">Export Excel</button>
  </div>
</form>
<section class="section">
  <h2>Exports folder</h2>
  <p>{html.escape(str(exports_dir))}</p>
  <div class="stack">{file_rows}</div>
</section>
"""
    return render_page(
        title="Reports",
        active="reports",
        body=body,
        app_name=ctx.config.app.name,
        version=ctx.config.app.version,
    )


def handle_post(ctx: UiContext) -> str:
    """Run Excel export and re-render."""
    try:
        path = ctx.profiles.export_excel()
    except (OSError, PipError) as exc:
        return render(ctx, error=str(exc))
    return render(ctx, notice=f"Exported workbook to {path}")


def _list_exports(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    files = [path for path in directory.iterdir() if path.is_file()]
    return sorted(files, key=lambda path: path.stat().st_mtime, reverse=True)[:20]
