from __future__ import annotations

from typing import Any


def validate_question(question: dict[str, Any]) -> list[str]:
    errors = []
    options = question.get("options")
    if not isinstance(options, list) or not 3 <= len(options) <= 5: errors.append("options must contain 3 to 5 choices")
    if len(set(options or [])) != len(options or []): errors.append("options must be unique")
    if question.get("correct_option") not in (options or []): errors.append("exactly one correct option is required")
    if not str(question.get("prompt", "")).strip() or len(str(question.get("prompt", "")).split()) > 80: errors.append("prompt must be short")
    if len(str(question.get("explanation", "")).split()) > 80: errors.append("explanation must contain at most 80 words")
    if question.get("category") not in {"architecture", "modularization", "practice", "trade-off", "business-rule", "test", "security", "operation"}:
        errors.append("unsupported category")
    if not question.get("sources"): errors.append("at least one stable source is required")
    return errors
