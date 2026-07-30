from __future__ import annotations

import ast
from pathlib import Path

from ..reporting.models import Finding
from ..security.fingerprint import fingerprint


def python_metrics(path: Path) -> list[dict]:
    try: tree = ast.parse(path.read_text(errors="replace"))
    except (OSError, SyntaxError, UnicodeDecodeError): return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = getattr(node, "end_lineno", node.lineno)
            complexity = sum(isinstance(x, (ast.If, ast.For, ast.While, ast.Try, ast.BoolOp, ast.Match, ast.IfExp)) for x in ast.walk(node))
            out.append({"name": node.name, "line": node.lineno, "logical_lines": end - node.lineno + 1, "complexity": complexity})
    return out


def find_complexity(root: Path, function_threshold: int = 50, complexity_threshold: int = 15) -> list[Finding]:
    findings = []
    for path in root.rglob("*.py"):
        if {".framework", ".venv", "venv", "node_modules", "tests", ".git"}.intersection(path.parts): continue
        rel = str(path.relative_to(root))
        for metric in python_metrics(path):
            if metric["logical_lines"] > function_threshold:
                fp = fingerprint(rel, str(metric["line"]), "function-long")
                findings.append(Finding("CMP-" + fp[7:15], "complexity", "block", "open", rel, metric["line"], "function_logical_lines", f"Function {metric['name']} has {metric['logical_lines']} logical lines", "Split the function into cohesive units", {"name": metric["name"], "value": metric["logical_lines"], "threshold": function_threshold}, fp))
            if metric["complexity"] > complexity_threshold:
                fp = fingerprint(rel, str(metric["line"]), "cognitive")
                findings.append(Finding("CMP-" + fp[7:15], "complexity", "block", "open", rel, metric["line"], "cognitive_complexity", f"Function {metric['name']} has complexity {metric['complexity']}", "Reduce branching or extract collaborators", {"name": metric["name"], "value": metric["complexity"], "threshold": complexity_threshold}, fp))
    return findings
