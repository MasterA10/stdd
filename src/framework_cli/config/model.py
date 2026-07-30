from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_RULES: dict[str, dict[str, Any]] = {
    "duplicate_block_statements": {"threshold": 6, "severity": "block_new"},
    "function_logical_lines": {"threshold": 50, "severity": "block_new"},
    "cognitive_complexity": {"threshold": 15, "severity": "block_new"},
    "god_class": {"threshold": 15, "severity": "block_new"},
}


@dataclass
class ProjectConfig:
    root_path: str
    profile: str = "mvp"
    mode: str = "brownfield"
    version: int = 1
    platforms: list[str] = field(default_factory=lambda: ["macos", "linux"])
    applications: dict[str, dict[str, Any]] = field(default_factory=dict)
    agent_integrations: list[str] = field(default_factory=list)
    security: dict[str, Any] = field(default_factory=dict)
    quality: dict[str, Any] = field(default_factory=dict)
    documentation: dict[str, Any] = field(default_factory=lambda: {"test_explanations": "header"})
    scripts: dict[str, Any] = field(default_factory=lambda: {"preferred": "auto"})
    learn: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "profile": self.profile,
            "mode": self.mode,
            "root_path": self.root_path,
            "platforms": self.platforms,
            "applications": self.applications,
            "agent": {"integrations": [{"id": x, "enabled": True} for x in self.agent_integrations]},
            "security": self.security,
            "quality": self.quality,
            "documentation": self.documentation,
            "scripts": self.scripts,
            "learn": self.learn,
        }

    @classmethod
    def from_dict(cls, root: Path, raw: dict[str, Any]) -> "ProjectConfig":
        agent = raw.get("agent", {}) or {}
        integrations = agent.get("integrations", []) if isinstance(agent, dict) else []
        ids = [x.get("id", x) if isinstance(x, dict) else x for x in integrations]
        security = {"secret_scan": True, "scan_history": True, "scan_remote_diff": True,
                    "env_files": [".env", ".env.*"],
                    "safe_examples": [".env.example", ".env.sample", ".env.template"],
                    **(raw.get("security", {}) or {})}
        quality = {"baseline": ".framework/quality/baseline.json", "rules": DEFAULT_RULES.copy(),
                   **(raw.get("quality", {}) or {})}
        documentation = {"test_explanations": "header", **(raw.get("documentation", {}) or {})}
        learn = {"enabled": False, "retention_days": 365, "agent_command": "local", "agents": {},
                 "redaction": {"enabled": True}, **(raw.get("learn", {}) or {})}
        return cls(root_path=str(root.resolve()), version=int(raw.get("version", 1)),
                   profile=str(raw.get("profile", "mvp")), mode=str(raw.get("mode", "brownfield")),
                   platforms=list(raw.get("platforms", ["macos", "linux"])),
                   applications=dict(raw.get("applications", {}) or {}), agent_integrations=ids,
                   security=security, quality=quality, scripts=dict(raw.get("scripts", {"preferred": "auto"}) or {}),
                   documentation=documentation, learn=learn)

    @classmethod
    def default(cls, root: Path, mode: str = "brownfield") -> "ProjectConfig":
        return cls.from_dict(root, {"mode": mode, "security": {}, "quality": {"rules": DEFAULT_RULES.copy()}})
