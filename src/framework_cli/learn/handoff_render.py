from __future__ import annotations

from typing import Any


def render_markdown(package: dict[str, Any]) -> str:
    context = package.get("context", {})
    lines = [f"# Handoff {package.get('handoff_id', '')}", "", f"- Target: `{package.get('target', 'generic')}`",
             f"- Source session: `{package.get('source_session_id', '')}`", f"- Schema: `{package.get('schema_version', 1)}`", "",
             "## Summary", ""]
    summary = context.get("summary", {})
    for key in ("lesson", "observations", "inferences", "evidence"):
        values = summary.get(key, [])
        if values:
            lines.append(f"### {key.title()}")
            lines.extend(f"- {value}" for value in values)
    for key in ("tasks", "files", "symbols"):
        values = context.get(key, summary.get(key, []))
        if values:
            lines.append(f"### {key.title()}")
            lines.extend(f"- `{value}`" for value in values)
    if context.get("lessons"):
        lines.extend(["", "## Lessons", ""])
        lines.extend(f"- {item.get('title', '')}: {'; '.join(item.get('content', []))}" for item in context["lessons"])
    lines.extend(["", "## Coverage", "", f"- {package.get('coverage', {})}", "", "_This view is equivalent to the structured scope._"])
    return "\n".join(lines) + "\n"
