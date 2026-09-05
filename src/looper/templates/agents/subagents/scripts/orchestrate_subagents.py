#!/usr/bin/env python3
"""Descobre CLIs e executa tarefas tmux com barreira bloqueante, sem polling."""
from __future__ import annotations

import argparse
import json
import os
import select
import shlex
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

KNOWN_AGENTS = ("codex", "claude", "agy", "gemini", "antigravity")
DEFAULT_MODELS = {
    "codex": "gpt-5.6-luna",
    "agy": "gemini-3.8-flash",
}
DEFAULT_REASONING = {"agy": "low"}
MARKER = "__SUBAGENT_EXIT__"


def discover() -> int:
    entries = []
    for name in KNOWN_AGENTS:
        path = shutil.which(name)
        version = ""
        if path:
            probe = subprocess.run([path, "--version"], capture_output=True, text=True, check=False, timeout=10)
            text = (probe.stdout or probe.stderr).strip()
            version = text.splitlines()[0] if text else ""
        entries.append({"name": name, "available": bool(path), "path": path, "version": version})
    print(json.dumps(entries, ensure_ascii=False, indent=2))
    return 0


def render_command(task: dict) -> list[str]:
    command = task.get("command")
    if not isinstance(command, list) or not command or not all(isinstance(item, str) for item in command):
        raise ValueError("cada tarefa precisa de command como lista de strings")
    command_agent = Path(command[0]).name.lower()
    model = str(task.get("model", ""))
    if not model:
        model = DEFAULT_MODELS.get(command_agent, "")
    reasoning = str(task.get("reasoning", ""))
    if not reasoning:
        reasoning = DEFAULT_REASONING.get(command_agent, "")
    values = {
        "prompt": str(task.get("prompt", "")),
        "model": model,
        "reasoning": reasoning,
        "session_id": str(task.get("session_id", "")),
        "workdir": str(task.get("workdir", Path.cwd())),
    }
    return [
        item.replace("{prompt}", values["prompt"])
        .replace("{model}", values["model"])
        .replace("{reasoning}", values["reasoning"])
        .replace("{session_id}", values["session_id"])
        .replace("{workdir}", values["workdir"])
        for item in command
    ]


def extract_final(stdout: str, task: dict) -> tuple[str, str | None, dict]:
    """Extrai somente a resposta final e metadados de envelopes JSON conhecidos."""
    if task.get("output_format") != "json":
        return stdout.strip(), task.get("session_id"), {}
    candidates = []
    for line in stdout.splitlines():
        try:
            candidates.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    document = candidates[-1] if candidates else {}
    if isinstance(document.get("result"), dict):
        document = document["result"]
    response = document.get("response", "") if isinstance(document, dict) else ""
    session_id = (document.get("conversation_id") or document.get("session_id") or task.get("session_id")) if isinstance(document, dict) else task.get("session_id")
    usage = document.get("usage", {}) if isinstance(document, dict) and isinstance(document.get("usage", {}), dict) else {}
    return str(response).strip(), session_id, usage


def run(manifest_path: Path, output_path: Path, fifo: bool = False) -> int:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    tasks = manifest.get("tasks") if isinstance(manifest, dict) else None
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("manifesto precisa conter tasks não vazio")
    if any(not isinstance(task, dict) or not isinstance(task.get("id"), str) or not task["id"] or not isinstance(task.get("prompt"), str) for task in tasks):
        raise ValueError("cada tarefa precisa de id e prompt")
    if len({task["id"] for task in tasks}) != len(tasks):
        raise ValueError("IDs de tarefas devem ser únicos")

    root = Path(manifest.get("workdir", Path.cwd())).resolve()
    timeout = int(manifest.get("timeout_seconds", 900))
    run_id = uuid.uuid4().hex[:10]
    session = f"subagents-{run_id}"[:48]
    sessions: list[str] = [session]
    pane_targets: dict[str, str] = {}
    keep_session = bool(manifest.get("keep_session", True))
    completed_run = False
    results: list[dict] = []
    started = time.time()
    locks = {task["id"]: f"subagents-{run_id}-{task['id']}" for task in tasks}
    fifo_path = root / f".subagents-{run_id}.fifo"
    try:
        if fifo:
            os.mkfifo(fifo_path)
        else:
            # Cada lock é adquirido antes do disparo. O worker libera-o ao sair;
            # o segundo acquire abaixo bloqueia, sem consultar estado repetidamente.
            for channel in locks.values():
                subprocess.run(["tmux", "wait-for", "-L", channel], cwd=root, check=True)

        for task in tasks:
            task_id = task["id"]
            log_path = root / f".subagent-{run_id}-{task_id}.log"
            stdout_path = root / f".subagent-{run_id}-{task_id}.stdout"
            stderr_path = root / f".subagent-{run_id}-{task_id}.stderr"
            code_path = root / f".subagent-{run_id}-{task_id}.code"
            command = shlex.join(render_command(task))
            workdir = str(Path(task.get("workdir", root)).resolve())
            if fifo:
                completion = f"printf '%s\\n' {shlex.quote(task_id)} > {shlex.quote(str(fifo_path))}"
            else:
                completion = f"tmux wait-for -U {shlex.quote(locks[task_id])}"
            script = (
                f"cd {shlex.quote(workdir)} && {command} > {shlex.quote(str(stdout_path))} 2> {shlex.quote(str(stderr_path))}; "
                f"code=$?; printf '%s' $code > {shlex.quote(str(code_path))}; {completion}; "
                f"{'exec bash' if keep_session else 'exit $code'}"
            )
            launch = (["tmux", "new-session", "-d", "-P", "-F", "#{pane_id}", "-s", session, "bash", "-lc", script]
                      if task is tasks[0]
                      else ["tmux", "split-window", "-h", "-P", "-F", "#{pane_id}", "-t", session, "bash", "-lc", script])
            launched = subprocess.run(launch, cwd=root, capture_output=True, text=True, check=False)
            if launched.returncode:
                raise RuntimeError(launched.stderr.strip() or f"falha ao iniciar {task_id}")
            pane_targets[task_id] = launched.stdout.strip().splitlines()[-1]
            subprocess.run(["tmux", "select-layout", "-t", session, "even-horizontal"], cwd=root, check=True)

        if not manifest.get("headless", False):
            terminal_command = f"tmux attach-session -t {shlex.quote(session)}"
            subprocess.run(["osascript", "-e", f'tell application "Terminal" to do script "{terminal_command}"'], cwd=root, check=True, capture_output=True, text=True)

        deadline = time.monotonic() + timeout
        for task in tasks:
            task_id = task["id"]
            if fifo:
                fd = os.open(fifo_path, os.O_RDONLY | os.O_NONBLOCK)
                try:
                    ready, _, _ = select.select([fd], [], [], max(0.1, deadline - time.monotonic()))
                    if not ready:
                        results.append({"id": task_id, "status": "timeout", "returncode": None, "session_id": task.get("session_id")})
                        continue
                    os.read(fd, 4096)
                finally:
                    os.close(fd)
            else:
                remaining = max(0.1, deadline - time.monotonic())
                try:
                    subprocess.run(["tmux", "wait-for", "-L", locks[task_id]], cwd=root, timeout=remaining, check=True)
                except subprocess.TimeoutExpired:
                    results.append({"id": task_id, "status": "timeout", "returncode": None, "session_id": task.get("session_id")})
                    continue
            stdout_path = root / f".subagent-{run_id}-{task_id}.stdout"
            stderr_path = root / f".subagent-{run_id}-{task_id}.stderr"
            code_path = root / f".subagent-{run_id}-{task_id}.code"
            stdout = stdout_path.read_text(encoding="utf-8") if stdout_path.exists() else ""
            stderr = stderr_path.read_text(encoding="utf-8") if stderr_path.exists() else ""
            code_file = code_path
            code = int(code_file.read_text(encoding="utf-8")) if code_file.exists() else None
            response, session_id, usage = extract_final(stdout, task)
            result = {"id": task_id, "status": "completed" if code == 0 else "failed", "returncode": code, "session_id": session_id, "tmux_session": session, "pane_target": pane_targets.get(task_id), "response": response, "usage": usage, "error": stderr.strip() or None}
            results.append(result)
            if response and keep_session:
                display = shlex.quote(response)
                subprocess.run(["tmux", "send-keys", "-t", pane_targets[task_id], f"printf '%s\\n' {display}", "C-m"], cwd=root, check=False)
            for path in (stdout_path, stderr_path, code_path):
                path.unlink(missing_ok=True)
        completed_run = True
    finally:
        if not completed_run or not keep_session:
            subprocess.run(["tmux", "kill-session", "-t", session], cwd=root, capture_output=True, check=False)
        fifo_path.unlink(missing_ok=True)

    complete = len(results) == len(tasks) and all(item["status"] == "completed" for item in results)
    output_path.write_text(json.dumps({"status": "completed" if complete else "incomplete", "elapsed_seconds": time.time() - started, "results": results}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


def continue_task(state_path: Path, task_id: str, command: str) -> int:
    state = json.loads(state_path.read_text(encoding="utf-8"))
    item = next((result for result in state.get("results", []) if result.get("id") == task_id), None)
    if not item or not item.get("pane_target"):
        raise ValueError(f"tarefa sem pane persistido: {task_id}")
    subprocess.run(["tmux", "send-keys", "-t", item["pane_target"], command, "C-m"], check=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="action", required=True)
    subparsers.add_parser("discover")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--manifest", type=Path, required=True)
    run_parser.add_argument("--output", type=Path, required=True)
    run_parser.add_argument("--fifo", action="store_true")
    run_parser.add_argument("--headless", action="store_true", help="não abrir o Terminal; destinado a CI")
    continue_parser = subparsers.add_parser("continue")
    continue_parser.add_argument("--state", type=Path, required=True)
    continue_parser.add_argument("--task-id", required=True)
    continue_parser.add_argument("--command", required=True)
    args = parser.parse_args()
    try:
        if args.action == "discover":
            return discover()
        if args.action == "continue":
            return continue_task(args.state, args.task_id, args.command)
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
        data["headless"] = args.headless
        runtime_manifest = args.manifest.with_suffix(args.manifest.suffix + ".runtime")
        runtime_manifest.write_text(json.dumps(data), encoding="utf-8")
        try:
            return run(runtime_manifest, args.output, args.fifo)
        finally:
            runtime_manifest.unlink(missing_ok=True)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError, subprocess.SubprocessError) as error:
        print(f"subagents: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
