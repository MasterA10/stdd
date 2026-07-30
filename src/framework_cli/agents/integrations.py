from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class IntegrationSpec:
    """Filesystem and CLI contract for one local coding agent."""

    key: str
    aliases: tuple[str, ...]
    executable_names: tuple[str, ...]
    skills_root: str | None
    legacy_commands_root: str | None = None
    cli_mode: str = "argument"
    multi_install_safe: bool = False

    def resolve_executable(self) -> str | None:
        override = os.environ.get(f"FRAMEWORK_AGENT_{self.key.upper()}_EXECUTABLE", "").strip()
        if override:
            return override
        for name in self.executable_names:
            value = shutil.which(name)
            if value:
                return value
        return None

    def skill_path(self, root: Path, name: str) -> Path | None:
        if not self.skills_root:
            return None
        return root / self.skills_root / name / "SKILL.md"

    def legacy_path(self, root: Path, name: str) -> Path | None:
        if not self.legacy_commands_root:
            return None
        return root / self.legacy_commands_root / f"{name}.md"


INTEGRATIONS: dict[str, IntegrationSpec] = {
    "codex": IntegrationSpec("codex", (), ("codex",), ".agents/skills", cli_mode="argument",
                              multi_install_safe=True),
    "claude": IntegrationSpec("claude", (), ("claude",), ".claude/skills",
                               legacy_commands_root=".claude/commands", cli_mode="stdin",
                               multi_install_safe=True),
    "agy": IntegrationSpec("agy", ("antigravity",), ("agy", "antigravity"), ".agents/skills",
                            cli_mode="argument", multi_install_safe=False),
    "cloud": IntegrationSpec("cloud", (), ("cloud",), None, cli_mode="request"),
}


def resolve_integration(value: str) -> IntegrationSpec | None:
    normalized = value.strip().lower()
    for spec in INTEGRATIONS.values():
        if normalized == spec.key or normalized in spec.aliases:
            return spec
    return None


def integration_keys(*, installable_only: bool = False) -> tuple[str, ...]:
    values = [spec.key for spec in INTEGRATIONS.values()
              if not installable_only or spec.skills_root or spec.legacy_commands_root]
    return tuple(values)


def incompatible_integrations(integrations: list[str]) -> list[tuple[str, str]]:
    canonical = {resolve_integration(item).key for item in integrations if resolve_integration(item)}
    pairs: list[tuple[str, str]] = []
    if {"agy", "codex"}.issubset(canonical):
        pairs.append(("agy", "codex"))
    return pairs
