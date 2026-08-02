"""Compare page."""

from __future__ import annotations

import html

from profile_intelligence.core.exceptions import PipError, ValidationError
from profile_intelligence.ui.context import UiContext
from profile_intelligence.ui.layout import render_page
from profile_intelligence.ui.pages.import_page import parse_form


def render(
    ctx: UiContext,
    *,
    form: dict[str, str] | None = None,
    table: str | None = None,
    error: str | None = None,
) -> str:
    """Render compare form and optional diff table."""
    form = form or {}
    left = form.get("left", "")
    right = form.get("right", "")
    status = f'<p class="notice err">{html.escape(error)}</p>' if error else ""
    result = table or ""

    body = f"""
<section class="page-head">
  <h1>Compare</h1>
  <p>Diff two stored profiles field by field.</p>
</section>
{status}
<form class="form-grid" method="post" action="/compare">
  <label>Left profile id
    <input type="number" name="left" min="1" step="1" value="{html.escape(left)}" required>
  </label>
  <label>Right profile id
    <input type="number" name="right" min="1" step="1" value="{html.escape(right)}" required>
  </label>
  <div class="actions">
    <button class="btn" type="submit">Compare</button>
  </div>
</form>
{result}
"""
    return render_page(
        title="Compare",
        active="compare",
        body=body,
        app_name=ctx.config.app.name,
        version=ctx.config.app.version,
    )


def handle_post(ctx: UiContext, body: bytes) -> str:
    """Run a comparison and render results."""
    form = parse_form(body)
    try:
        left_id = int(form.get("left", "").strip())
        right_id = int(form.get("right", "").strip())
        comparison = ctx.compare.compare_ids(left_id, right_id)
    except (TypeError, ValueError):
        return render(ctx, form=form, error="Enter two valid profile ids.")
    except (ValidationError, PipError) as exc:
        return render(ctx, form=form, error=str(exc))

    rows = "".join(
        f"<tr class='{'diff-mismatch' if not field.equal else ''}'>"
        f"<td>{html.escape(field.field)}</td>"
        f"<td>{html.escape(field.left)}</td>"
        f"<td>{html.escape(field.right)}</td>"
        f"<td>{'match' if field.equal else 'diff'}</td>"
        "</tr>"
        for field in comparison.fields
    )
    table = f"""
<section class="section">
  <h2>{html.escape(comparison.left_name)} vs {html.escape(comparison.right_name)}</h2>
  <p>{len(comparison.differences)} difference(s), {len(comparison.matches)} match(es).</p>
  <table>
    <thead><tr><th>Field</th><th>Left</th><th>Right</th><th>Status</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</section>
"""
    return render(ctx, form=form, table=table)
