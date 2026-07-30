from __future__ import annotations

TARGETS = {"generic": {"supported": True}, "codex": {"supported": True}, "claude": {"supported": True},
           "antigravity": {"supported": True}, "new-session": {"supported": True}}


def target_info(name: str) -> dict:
    return {"target": name, **TARGETS.get(name, {"supported": False})}
