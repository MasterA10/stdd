from __future__ import annotations

from pathlib import Path


HOOK_MARKER = "# framework-managed-hook"


def install_hooks(root: Path) -> dict:
    hooks = root / ".git" / "hooks"
    if not hooks.is_dir(): return {"installed": [], "conflicts": ["Git hooks directory unavailable"]}
    result = {"installed": [], "conflicts": []}
    for name in ("pre-commit", "pre-push"):
        path = hooks / name
        body = "#!/bin/sh\n# framework-managed-hook\nframework security scan && framework check\n"
        if path.exists() and HOOK_MARKER not in path.read_text(errors="replace"):
            result["conflicts"].append(str(path.relative_to(root)))
            continue
        path.write_text(body)
        path.chmod(0o755)
        result["installed"].append(str(path.relative_to(root)))
    return result
