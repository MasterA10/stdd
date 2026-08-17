import re

with open('src/stdd/cli.py', 'r') as f:
    content = f.read()

# Update _compact_backlog_response
content = re.sub(
    r'\("instruction", "remaining", "completed_task_id"\)',
    r'("instruction", "remaining", "completed_task_id", "access_paths")',
    content
)

# Update _format_backlog_response
new_format = '''    if compact.get("instruction"):
        lines.append(f"Próximo passo: {compact['instruction']}")
    access_paths = compact.get("access_paths")
    if isinstance(access_paths, list):
        for path in access_paths:
            lines.append(f"Origem: {path.replace(' → Nó atual', '')}")
    return "\\n".join(lines)'''

content = re.sub(
    r'    if compact\.get\("instruction"\):\n        lines\.append\(f"Próximo passo: \{compact\[\'instruction\'\]\}"\)\n    return "\\n"\.join\(lines\)',
    new_format,
    content
)

with open('src/stdd/cli.py', 'w') as f:
    f.write(content)
