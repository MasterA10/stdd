from __future__ import annotations

import hashlib


def fingerprint(*parts: str) -> str:
    return "sha256:" + hashlib.sha256("\0".join(parts).encode()).hexdigest()
