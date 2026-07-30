from __future__ import annotations

import re


def redact(value: str) -> str:
    if not value: return ""
    return f"<redacted:{len(value)} chars>"


def redact_text(text: str, values: list[str]) -> str:
    for value in sorted({v for v in values if v}, key=len, reverse=True):
        text = text.replace(value, redact(value))
    return text
