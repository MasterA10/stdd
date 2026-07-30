from __future__ import annotations

from typing import Any

from ..security.patterns import matches
from ..security.redaction import redact, redact_text

SENSITIVE_KEYS = ("secret", "token", "password", "credential", "api_key", "apikey", "private_key")


def redact_value(value: Any, *, path: str = "") -> tuple[Any, int, set[str]]:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        count = 0
        kinds: set[str] = set()
        for key, item in value.items():
            key_text = str(key).lower().replace("-", "_")
            if any(term in key_text for term in SENSITIVE_KEYS):
                result[key] = "<redacted>"
                count += 1
                kinds.add("sensitive-field")
                continue
            clean, found, found_kinds = redact_value(item, path=f"{path}.{key}")
            result[key], count = clean, count + found
            kinds.update(found_kinds)
        return result, count, kinds
    if isinstance(value, list):
        result, count, kinds = [], 0, set()
        for index, item in enumerate(value):
            clean, found, found_kinds = redact_value(item, path=f"{path}[{index}]")
            result.append(clean); count += found; kinds.update(found_kinds)
        return result, count, kinds
    if isinstance(value, str):
        found = matches(value)
        if not found:
            return value, 0, set()
        clean = redact_text(value, [secret for _, secret in found])
        return clean, len(found), {rule for rule, _ in found}
    return value, 0, set()


def redact_record(record: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    clean, count, kinds = redact_value(record)
    metadata = {"count": count, "types": sorted(kinds)}
    if isinstance(clean, dict):
        clean["redaction"] = {**(clean.get("redaction") or {}), **metadata}
    return clean, metadata
