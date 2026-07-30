from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol



class QuestionCommand(Protocol):
    name: str
    version: str
    def generate(self, request: dict[str, Any]) -> dict[str, Any]: ...


@dataclass
class CommandResponseFixture:
    """Test-only command response shim; production uses subprocess execution."""
    name: str = "local-command"
    version: str = "1"
    callback: Any = None

    def generate(self, request: dict[str, Any]) -> dict[str, Any]:
        if self.callback is None:
            return {"status": "failed", "job_id": request["job_id"], "error": {"code": "command-unavailable"}}
        response = self.callback(request)
        return response if isinstance(response, dict) else {"status": "failed", "job_id": request["job_id"], "error": {"code": "malformed-command-response"}}


def acknowledgment(response: dict[str, Any]) -> dict[str, str]:
    return {"status": str(response.get("status", "failed")), "job_id": str(response.get("job_id", ""))}
