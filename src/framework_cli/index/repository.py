from __future__ import annotations

import json
from typing import Any

from .db import IndexDB


class Repository:
    def __init__(self, db: IndexDB):
        self.db = db

    def project(self, project_id: str, root_path: str, profile: str) -> None:
        self.db.execute("INSERT OR REPLACE INTO projects VALUES (?,?,?)", (project_id, root_path, profile))

    def application(self, app_id: str, project_id: str, path: str, data: dict[str, Any]) -> None:
        self.db.execute("INSERT OR REPLACE INTO applications VALUES (?,?,?,?)", (app_id, project_id, path, json.dumps(data)))

    def finding(self, finding: dict[str, Any]) -> None:
        self.db.execute("INSERT OR REPLACE INTO findings VALUES (?,?,?,?,?)", (finding["id"], finding.get("category", "quality"), finding.get("path"), finding.get("line"), json.dumps(finding)))

    def learn_session(self, data: dict[str, Any]) -> None:
        self.db.execute("INSERT OR REPLACE INTO learn_sessions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
            data["session_id"], data.get("parent_session_id"), data["status"], data["local_date"],
            data.get("started_at"), data.get("ended_at"), data.get("agent"), data.get("host"),
            data.get("branch"), data.get("worktree"), data.get("commit_base"), json.dumps(data.get("coverage", {}))))

    def learn_event(self, data: dict[str, Any]) -> None:
        self.db.execute("INSERT OR IGNORE INTO learn_events VALUES (?,?,?,?,?,?)", (
            data["event_id"], data["session_id"], data["type"], data["observed_at"],
            data["fingerprint"], json.dumps(data, sort_keys=True)))

    def lesson(self, data: dict[str, Any]) -> None:
        self.db.execute("INSERT OR REPLACE INTO learn_lessons VALUES (?,?,?,?,?)", (
            data["lesson_id"], data["revision"], data["status"], json.dumps(data, sort_keys=True), data.get("fingerprint", "")))

    def handoff(self, data: dict[str, Any]) -> None:
        self.db.execute("INSERT OR REPLACE INTO handoffs VALUES (?,?,?,?,?,?)", (
            data["handoff_id"], data["source_session_id"], data["target"], data["source_checksum"],
            data.get("status", "created"), json.dumps(data, sort_keys=True)))

    def question(self, data: dict[str, Any]) -> None:
        self.db.execute("INSERT OR REPLACE INTO quiz_questions VALUES (?,?,?,?,?)", (
            data["question_id"], data["revision"], data["status"], data.get("fingerprint", ""), json.dumps(data, sort_keys=True)))

    def job(self, data: dict[str, Any]) -> None:
        self.db.execute("INSERT OR REPLACE INTO quiz_jobs VALUES (?,?,?,?,?)", (
            data["job_id"], data["session_id"], data["provider"], data["status"], json.dumps(data, sort_keys=True)))

    def attempt(self, data: dict[str, Any]) -> None:
        self.db.execute("INSERT OR REPLACE INTO quiz_attempts VALUES (?,?,?,?,?)", (
            data["attempt_id"], data["session_id"], data["question_revision"], json.dumps(data, sort_keys=True)))
