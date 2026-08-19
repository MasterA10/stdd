import re
from pathlib import Path

with open('src/looper/backlog.py', 'r') as f:
    content = f.read()

# Add imports
if 'EDGE_CONDITIONS' not in content:
    content = content.replace('from .draw import generate_draws, read_draw_index\n', 
                              'from .draw import generate_draws, read_draw_index, read_draw, EDGE_CONDITIONS\n')

# Update definition
new_def = '''def _task_context(root: Path, payload: dict[str, Any], task: dict[str, Any], phase: str, kind: str, instruction: str | None = None) -> dict[str, Any]:
    """Retorna a task atual com pai e subtasks para o agente manter contexto."""
    tasks = payload.get("tasks", [])
    parent = _parent_task(tasks, task)
    descendants = [
        item for item in tasks
        if item.get("id") in parent.get("child_task_ids", [])
    ]
    subtask = task if task.get("id") != parent.get("id") else next(
        (item for item in descendants if item.get("status") != "done"),
        None,
    )
    
    origin_nodes = []
    origin_edges = []
    access_paths = []
    
    draw_id = task.get("backlog_id")
    node_id = task.get("node_id")
    
    if draw_id and node_id:
        try:
            document = read_draw(root, draw_id)
            nodes = {n.get("id"): n for n in document.get("nodes", [])}
            for edge in document.get("edges", []):
                if edge.get("to") == node_id:
                    origin_edges.append(edge)
                    from_id = edge.get("from")
                    if from_id in nodes:
                        from_node = nodes[from_id]
                        origin_nodes.append(from_node)
                        label = from_node.get("label") or str(from_id)
                        condition = EDGE_CONDITIONS.get(edge.get("condition"), "então")
                        access_paths.append(f"Nó {label} → {condition} → Nó atual")
        except Exception:
            pass

    response: dict[str, Any] = {
        "kind": kind,
        "phase": phase,
        "task": task,
        "parent_task": parent,
        "subtask": subtask,
        "subtasks": descendants,
        "origin_nodes": origin_nodes,
        "origin_edges": origin_edges,
        "access_paths": access_paths,
    }
    if instruction is not None:
        response["instruction"] = instruction
    return response'''

old_def_regex = r'def _task_context\(payload: dict\[str, Any\], task: dict\[str, Any\], phase: str, kind: str, instruction: str \| None = None\) -> dict\[str, Any\]:\n.*?return response'
content = re.sub(old_def_regex, new_def, content, flags=re.DOTALL)

# Update all calls
content = re.sub(r'_task_context\(\s*payload,', r'_task_context(root, payload,', content)

with open('src/looper/backlog.py', 'w') as f:
    f.write(content)
