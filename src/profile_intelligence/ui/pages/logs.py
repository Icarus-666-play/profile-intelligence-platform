"""Logs page."""

from __future__ import annotations

import html
from pathlib import Path

from profile_intelligence.ui.context import UiContext
from profile_intelligence.ui.layout import render_page

_LOG_FILES = ("application.log", "import.log", "errors.log")


def render(ctx: UiContext) -> str:
    """Render tails of local log files."""
    logs_dir = ctx.config.logs_dir
    blocks: list[str] = []
    for name in _LOG_FILES:
        path = logs_dir / name
        content = _tail(path)
        blocks.append(
            f"<section class='section'><h2>{html.escape(name)}</h2>"
            f"<p>{html.escape(str(path))}</p>"
            f"<pre class='log-block'>{html.escape(content)}</pre></section>"
        )

    body = f"""
<section class="page-head">
  <h1>Logs</h1>
  <p>Recent lines from the local rotating log files.</p>
</section>
{"".join(blocks)}
"""
    return render_page(
        title="Logs",
        active="logs",
        body=body,
        app_name=ctx.config.app.name,
        version=ctx.config.app.version,
    )


def _tail(path: Path, *, max_lines: int = 80) -> str:
    if not path.is_file():
        return "(file not found)"
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"(unable to read: {exc})"
    lines = text.splitlines()
    if not lines:
        return "(empty)"
    return "\n".join(lines[-max_lines:])
