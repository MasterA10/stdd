from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from ..learn.redaction import redact_record


class QuestionProvider(Protocol):
    name: str
    version: str
    def generate(self, request: dict[str, Any]) -> dict[str, Any]: ...


@dataclass
class ExternalProvider:
    name: str = "external"
    version: str = "1"
    callback: Any = None

    def generate(self, request: dict[str, Any]) -> dict[str, Any]:
        clean, _ = redact_record(request)
        if self.callback is None:
            return {"status": "failed", "job_id": request["job_id"], "error": {"code": "provider-unavailable"}, "request": clean}
        response = self.callback(clean)
        return response if isinstance(response, dict) else {"status": "failed", "job_id": request["job_id"], "error": {"code": "malformed-response"}}


def acknowledgment(response: dict[str, Any]) -> dict[str, str]:
    return {"status": str(response.get("status", "failed")), "job_id": str(response.get("job_id", ""))}
