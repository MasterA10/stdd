from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ..agents.instructions import discover_instruction_chain
from ..reporting.models import CommandResult
from .events import opaque, now_iso
from .handoff_render import render_markdown, validate_markdown_parity
from .handoff_scope import select_scope, select_lessons
from .store import LearnStore, write_json, read_json, repository


def _checksum(data: dict[str, Any]) -> str:
    body = {k: v for k, v in data.items() if k not in {"source_checksum", "checksum"}}
    raw = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode()).hexdigest()


def export_package(root: Path, *, session_id: str | None = None, target: str = "generic",
                   scope: dict[str, Any] | None = None) -> CommandResult:
    store = LearnStore(root); result = CommandResult("framework learn handoff export", metadata={"enabled": store.enabled()})
    chain = discover_instruction_chain(store.root)
    result.metadata["instruction_chain"] = [item.path for item in chain.files]
    if not chain.valid:
        result.status, result.exit_code = "blocked", 1; result.actions.append("Instruction-chain conflict blocks handoff export"); return result
    if not store.enabled(): result.status = "disabled"; return result
    session = store.get_session(session_id) if session_id else store.current_session()
    if not session:
        result.status, result.exit_code = "error", 2; result.actions.append("No session found"); return result
    selected = select_scope(store.events(session.session_id), scope)
    lessons = []
    for path in sorted((store.base / "lessons").glob("*.json")):
        try: lessons.append(read_json(path))
        except (OSError, ValueError): continue
    selected_lessons = select_lessons(lessons, selected["scope"])
    from .summarize import build_summary
    package = {"schema_version": 1, "handoff_id": opaque("handoff"), "source_session_id": session.session_id,
               "target": target, "scope": selected["scope"],
               "source_branch": session.branch,
               "context": {"summary": build_summary(selected["events"]), "events": selected["events"],
                            "tasks": sorted({x for e in selected["events"] for x in e.get("tasks", [])}),
                            "files": selected["files"], "symbols": selected["symbols"], "lessons": selected_lessons,
                            "decisions": [], "evidence": sorted({x for e in selected["events"] for x in e.get("evidence", [])})},
               "redaction": {"count": 0, "types": []}, "coverage": session.coverage, "created_at": now_iso()}
    package["source_checksum"] = _checksum(package)
    package_dir = store.base / "handoffs" / package["handoff_id"]
    structured = write_json(store, package_dir / "handoff.json", package)
    markdown = render_markdown(package)
    if not validate_markdown_parity(markdown, package)[0]:
        result.status, result.exit_code = "error", 2; result.actions.append("Could not create equivalent Markdown handoff"); return result
    package_dir.joinpath("handoff.md").write_text(markdown, encoding="utf-8")
    manifest = {"schema_version": 1, "handoff_id": package["handoff_id"], "source_session_id": session.session_id,
                "target": target, "scope": package["scope"], "checksum": package["source_checksum"],
                "structured": "handoff.json", "markdown": "handoff.md", "source_branch": session.branch}
    write_json(store, package_dir / "manifest.json", manifest)
    repository(store).handoff(package)
    result.metadata.update({"handoff_id": package["handoff_id"], "package": str(package_dir.relative_to(store.root)),
                            "source_checksum": package["source_checksum"], "coverage": package["coverage"]})
    result.actions.append("Review the redacted package and run framework security scan before committing")
    return result


def _contains_secret(text: str) -> bool:
    from ..security.patterns import matches
    return any(matches(line) for line in text.splitlines())


def _read_package(package_path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not package_path.exists(): return None, "Handoff package not found"
    raw_text = package_path.read_text(encoding="utf-8", errors="replace")
    if _contains_secret(raw_text): return None, "Sensitive value detected; package was not imported"
    try: return json.loads(raw_text), None
    except json.JSONDecodeError: return None, "Invalid handoff JSON"


def _validate_package(package: dict[str, Any]) -> str | None:
    required = {"schema_version", "handoff_id", "source_session_id", "scope", "context", "source_checksum"}
    if not required.issubset(package): return "Handoff is missing required fields"
    if package.get("schema_version") != 1 or _checksum(package) != package.get("source_checksum"):
        return "Handoff version or checksum conflict"


def _validate_views(package_path: Path, package: dict[str, Any]) -> str | None:
    markdown_path = package_path.with_name("handoff.md")
    if not markdown_path.exists() or not validate_markdown_parity(markdown_path.read_text(encoding="utf-8", errors="replace"), package)[0]:
        return "Structured and Markdown handoff views differ"


def _validate_manifest(package_path: Path, package: dict[str, Any]) -> str | None:
    manifest_path = package_path.with_name("manifest.json")
    if manifest_path.exists():
        try: manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError: manifest = {}
        if manifest.get("handoff_id") != package["handoff_id"] or manifest.get("checksum") != package["source_checksum"]:
            return "Handoff manifest conflict"


def _validate_import_conflicts(store: LearnStore, package: dict[str, Any]) -> str | None:
    existing = repository(store).handoff_record(package["handoff_id"])
    if existing and existing["status"] == "imported": return "Handoff was already imported"
    if package.get("source_branch") and store.git.branch and package["source_branch"] != store.git.branch:
        return "Handoff source branch conflicts with current branch"


def _prepare_import(store: LearnStore, package_path: Path) -> tuple[dict[str, Any] | None, str, str]:
    package, error = _read_package(package_path)
    if error: return None, "blocked" if "Sensitive" in error or "conflict" in error else "error", error
    for validator in (_validate_package, lambda value: _validate_views(package_path, value), lambda value: _validate_manifest(package_path, value), lambda value: _validate_import_conflicts(store, value)):
        error = validator(package)
        if error: return None, "error" if "already imported" in error else "blocked", error
    return package, "passed", ""


def import_package(root: Path, package_path: Path, *, agent: str = "framework", host: str = "framework-cli") -> CommandResult:
    store = LearnStore(root); result = CommandResult("framework learn handoff import", metadata={"enabled": store.enabled()})
    if not store.enabled(): result.status = "disabled"; return result
    package, status, message = _prepare_import(store, package_path.resolve())
    if package is None:
        result.status, result.exit_code = status, 1 if status == "blocked" else 2; result.actions.append(message); return result
    chain = discover_instruction_chain(store.root)
    if not chain.valid:
        result.status, result.exit_code = "blocked", 1; result.actions.append("Applicable instruction-chain conflict blocks import"); return result
    session = store.start_session(parent_session_id=package["source_session_id"], agent=agent, host=host)
    store.append_event({"schema_version": 1, "event_id": opaque("event"), "session_id": session.session_id,
                        "type": "checkpoint", "local_date": session.local_date, "observed_at": now_iso(),
                        "agent": agent, "host": host, "observations": ["Imported redacted handoff"],
                        "evidence": [package["handoff_id"]], "coverage": session.coverage})
    package["status"] = "imported"
    repository(store).handoff(package)
    result.metadata.update({"session": session.to_dict(), "source_session_id": package["source_session_id"],
                            "handoff_id": package["handoff_id"]})
    return result
