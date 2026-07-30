from __future__ import annotations

from pathlib import Path

from ..security.scanner import SecurityScanner


def security_scan(root: Path, *, staged_only: bool = False):
    return SecurityScanner(root).scan(staged_only=staged_only)
