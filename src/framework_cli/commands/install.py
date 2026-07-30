from __future__ import annotations

from pathlib import Path

from ..agents.integrations import integration_keys, resolve_integration
from ..agents.projections import install_projections, integration_status
from ..reporting.models import CommandResult


def install(root: Path, integration: str) -> CommandResult:
    spec = resolve_integration(integration)
    if not spec or not spec.skills_root and not spec.legacy_commands_root:
        choices = ", ".join(integration_keys(installable_only=True))
        return CommandResult("framework integration install", "error", 2, actions=[f"Use framework integration install <{choices}>"])
    data = install_projections(root.resolve(), [integration])
    if data.get("unsupported"):
        return CommandResult("framework integration install", "error", 2, metadata=data,
                             actions=[f"Unsupported integration: {integration}"])
    if data["conflicts"]:
        return CommandResult("framework integration install", "error", 4, metadata=data, actions=["Resolve locally modified projections before reinstalling"])
    return CommandResult("framework integration install", metadata=data)


def integration_list(root: Path) -> CommandResult:
    available = []
    for key in integration_keys(installable_only=True):
        spec = resolve_integration(key)
        available.append({"key": key, "aliases": list(spec.aliases),
                          "installed": key in integration_status(root)["installed_integrations"],
                          "requires_cli": bool(spec.resolve_executable())})
    return CommandResult("framework integration list", metadata={"integrations": available})


def integration_status_command(root: Path) -> CommandResult:
    data = integration_status(root)
    result = CommandResult("framework integration status", metadata=data)
    if data["modified"] or data["missing"] or data["conflicts"]:
        result.status, result.exit_code = "warned", 1
    return result
