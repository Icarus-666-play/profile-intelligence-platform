"""Import page — Input → Preview → Validate → Import."""

from __future__ import annotations

import html
from pathlib import Path

from profile_intelligence.application.use_cases.import_flow import ImportFlow
from profile_intelligence.core.exceptions import PipError
from profile_intelligence.domain.value_objects.import_flow import (
    IMPORT_FLOW_STAGES,
    PreviewResult,
    ValidationResult,
)
from profile_intelligence.ui.context import UiContext
from profile_intelligence.ui.layout import render_page


def render(
    ctx: UiContext,
    *,
    form: dict[str, str] | None = None,
    step: str = "input",
    notice: str | None = None,
    error: str | None = None,
    preview: PreviewResult | None = None,
    validation: ValidationResult | None = None,
) -> str:
    """Render the staged import wizard."""
    form = form or {}
    path = form.get("path", "")
    source = form.get("source", "")
    plugin = form.get("plugin", "")
    recursive = form.get("recursive") == "1"
    active = step if step in IMPORT_FLOW_STAGES else "input"

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

    preview_html = _render_preview(preview) if preview is not None else ""
    validate_html = _render_validation(validation) if validation is not None else ""

    body = f"""
<section class="page-head">
  <h1>Import</h1>
  <p>Staged operator flow for local files.</p>
</section>
{_render_flow_steps(active)}
{status}
<form class="form-grid" method="post" action="/import">
  <label>Path
    <input type="text" name="path" value="{html.escape(path)}" required
      placeholder="/path/to/profiles.csv">
  </label>
  <label>Source label (optional)
    <input type="text" name="source" value="{html.escape(source)}"
      placeholder="site-a">
  </label>
  <label>Plugin
    <select name="plugin">{"".join(options)}</select>
  </label>
  <label>
    <input type="checkbox" name="recursive" value="1"
      {"checked" if recursive else ""}> Recurse folders (Import stage)
  </label>
  <div class="actions">
    <button class="btn btn-secondary" type="submit" name="action" value="input">
      Input
    </button>
    <button class="btn btn-secondary" type="submit" name="action" value="preview">
      Preview
    </button>
    <button class="btn btn-secondary" type="submit" name="action" value="validate">
      Validate
    </button>
    <button class="btn" type="submit" name="action" value="import">
      Import
    </button>
  </div>
</form>
{preview_html}
{validate_html}
"""
    return render_page(
        title="Import",
        active="import",
        body=body,
        app_name=ctx.config.app.name,
        version=ctx.config.app.version,
    )


def handle_post(ctx: UiContext, form: dict[str, str]) -> str:
    """Dispatch Input / Preview / Validate / Import actions."""
    action = (form.get("action") or "import").strip().lower()
    if action not in IMPORT_FLOW_STAGES:
        action = "import"

    path_raw = form.get("path", "").strip()
    if not path_raw:
        return render(ctx, form=form, step=action, error="Path is required.")
    target = Path(path_raw).expanduser()
    if not target.exists():
        return render(
            ctx,
            form=form,
            step=action,
            error=f"Path not found: {target}",
        )

    source = form.get("source", "").strip() or None
    plugin = form.get("plugin", "").strip() or None
    recursive = form.get("recursive") == "1"
    flow = _flow(ctx)

    try:
        if action == "input":
            resolved = flow.resolve_input(
                target, source=source, plugin_name=plugin
            )
            if not resolved.ok:
                return render(
                    ctx,
                    form=form,
                    step="input",
                    error="; ".join(resolved.errors) or "Input failed",
                )
            notice = (
                f"Input OK — plugin={resolved.plugin} "
                f"path={resolved.path}"
            )
            return render(ctx, form=form, step="input", notice=notice)

        if action == "preview":
            preview = flow.preview(
                target, source=source, plugin_name=plugin
            )
            if not preview.ok and preview.errors:
                return render(
                    ctx,
                    form=form,
                    step="preview",
                    preview=preview,
                    error="; ".join(preview.errors[:3]),
                )
            notice = (
                f"Preview — accepted={preview.accepted_count} "
                f"rejected={preview.rejected_count} "
                f"duplicates={preview.duplicate_count}"
            )
            return render(
                ctx,
                form=form,
                step="preview",
                notice=notice,
                preview=preview,
            )

        if action == "validate":
            gate = flow.validate(
                target, source=source, plugin_name=plugin
            )
            notice = (
                f"Validate — ok={gate.ok} accepted={gate.accepted} "
                f"rejected={gate.rejected}"
            )
            return render(
                ctx,
                form=form,
                step="validate",
                notice=notice if gate.ok else None,
                error=None if gate.ok else "Validate gate failed",
                validation=gate,
            )

        summary = flow.run_import(
            target,
            source=source,
            plugin_name=plugin,
            recursive=recursive,
        )
        notice = (
            f"Import complete via {summary.plugin}: "
            f"created={summary.created} updated={summary.updated} "
            f"skipped={summary.skipped}"
        )
        return render(ctx, form=form, step="import", notice=notice)
    except (OSError, PipError, ValueError) as exc:
        return render(ctx, form=form, step=action, error=str(exc))


def parse_form(body: bytes) -> dict[str, str]:
    """Parse application/x-www-form-urlencoded body into a flat dict."""
    from urllib.parse import parse_qs

    parsed: dict[str, list[str]] = parse_qs(
        body.decode("utf-8", errors="replace")
    )
    return {key: (values[0] if values else "") for key, values in parsed.items()}


def _flow(ctx: UiContext) -> ImportFlow:
    if ctx.import_flow is not None:
        return ctx.import_flow
    return ImportFlow(ctx.imports, registry=ctx.importers)


def _render_flow_steps(active: str) -> str:
    parts: list[str] = ['<ol class="flow-steps" aria-label="Import flow">']
    for stage in IMPORT_FLOW_STAGES:
        cls = " is-active" if stage == active else ""
        label = stage.capitalize()
        parts.append(f'<li class="flow-step{cls}">{html.escape(label)}</li>')
    parts.append("</ol>")
    return "\n".join(parts)


def _render_preview(preview: PreviewResult) -> str:
    if not preview.rows:
        return (
            "<section class='section'><h2>Preview</h2>"
            "<p class='notice'>No preview rows.</p></section>"
        )
    rows = "".join(
        "<div class='row'>"
        f"<span class='id'>#{row.index}</span>"
        f"<span>{html.escape(row.display_name)}</span>"
        f"<span class='meta'>{html.escape(row.status)} · "
        f"confidence={html.escape(str(row.score if row.score is not None else '—'))}"
        f"</span></div>"
        for row in preview.rows[:40]
    )
    return (
        "<section class='section'><h2>Preview</h2>"
        f"<p>{preview.accepted_count} accepted · "
        f"{preview.rejected_count} rejected · "
        f"{preview.duplicate_count} duplicates</p>"
        f"<div class='stack'>{rows}</div></section>"
    )


def _render_validation(gate: ValidationResult) -> str:
    if not gate.issues:
        return (
            "<section class='section'><h2>Validate</h2>"
            f"<p class='notice ok'>Gate ok={gate.ok} — "
            f"accepted={gate.accepted}, rejected={gate.rejected}</p>"
            "</section>"
        )
    items = "".join(
        f"<div class='row'><span class='id'>{html.escape(issue.severity)}</span>"
        f"<span>{html.escape(issue.message)}</span>"
        f"<span class='meta'>"
        f"{'row ' + str(issue.index) if issue.index is not None else '—'}"
        f"</span></div>"
        for issue in gate.issues[:40]
    )
    return (
        "<section class='section'><h2>Validate</h2>"
        f"<p>ok={gate.ok} · accepted={gate.accepted} · "
        f"rejected={gate.rejected}</p>"
        f"<div class='stack'>{items}</div></section>"
    )
