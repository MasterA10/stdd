from __future__ import annotations

import base64
import hashlib
import json
import re
from typing import Any


def projection(package: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in package.items() if key not in {"source_checksum", "checksum"}}


def _marker(package: dict[str, Any]) -> str:
    raw = json.dumps(projection(package), sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode()


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
    lines.extend(["", "## Coverage", "", f"- {package.get('coverage', {})}", "", "_This view is equivalent to the structured scope._",
                  "", f"<!-- framework-handoff-projection: {_marker(package)} -->"])
    body = "\n".join(lines) + "\n"
    digest = hashlib.sha256(body.encode()).hexdigest()
    return body + f"<!-- framework-handoff-markdown-sha256: {digest} -->\n"


def validate_markdown_parity(markdown: str, package: dict[str, Any]) -> tuple[bool, str]:
    checksum = re.search(r"<!-- framework-handoff-markdown-sha256: ([a-f0-9]+) -->\s*\Z", markdown)
    if not checksum or hashlib.sha256(markdown[:checksum.start()].encode()).hexdigest() != checksum.group(1):
        return False, "Markdown checksum mismatch"
    match = re.search(r"<!-- framework-handoff-projection: ([A-Za-z0-9_=-]+) -->", markdown)
    if not match: return False, "missing parity projection"
    try: decoded = json.loads(base64.urlsafe_b64decode(match.group(1) + "=" * (-len(match.group(1)) % 4)).decode())
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError): return False, "invalid parity projection"
    expected = projection(package)
    return (decoded == expected, "" if decoded == expected else "structured and Markdown views differ")
