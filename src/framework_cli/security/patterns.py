from __future__ import annotations

import math
import re


PRIVATE_KEY = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")
PROVIDER_PATTERNS = [
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
]
SENSITIVE_ASSIGNMENT = re.compile(r"(?i)\b(api[_-]?key|secret|password|token|access[_-]?key)\b\s*[:=]\s*[\"']?([^\s\"']{8,})")


def entropy(value: str) -> float:
    if not value: return 0.0
    counts = {c: value.count(c) for c in set(value)}
    return -sum((n / len(value)) * math.log2(n / len(value)) for n in counts.values())


def matches(line: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if PRIVATE_KEY.search(line): found.append(("private-key", PRIVATE_KEY.search(line).group(0)))
    for name, pattern in PROVIDER_PATTERNS:
        match = pattern.search(line)
        if match: found.append((name, match.group(0)))
    assignment = SENSITIVE_ASSIGNMENT.search(line)
    if assignment and assignment.group(2).lower() not in {"example", "changeme", "placeholder", "your-key-here", "test-value"}:
        found.append(("sensitive-assignment", assignment.group(2)))
    return found
