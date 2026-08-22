"""TUI nativa, controlada somente pelo teclado, para configurar o Looper."""

from __future__ import annotations

import curses
import json
import os
import termios
import tempfile
import textwrap
from copy import deepcopy
from pathlib import Path
from typing import Any

from .backlog import VALID_CHILDREN_MODES, VALID_DEVELOPMENT_MODES, VALID_LOOP_MODES
from .core import init_project
from .reviews import DEFAULT_REVIEW_CONFIG, ensure_review_workspace
from .setup import SUPPORTED_INTEGRATIONS, configure_project, ensure_stack_gitignore

CONFIG_RELATIVE_PATH = ".looper/config.json"
REVIEW_RELATIVE_PATH = ".looper/review-agents.json"
INSTRUCTIONS_RELATIVE_PATH = ".looper/loop-instructions.md"


def _default_config() -> dict[str, Any]:
    return {"test_commands": [], "testing": {"profile": "mvp"}, "contract": {"enabled": True}, "static_analysis": {"enabled": True}, "tracked_extensions": [], "backlog": {"development_mode": "sequential", "task_delivery_scope": "task", "task_batch_size": 1, "task_batch_scope": "task", "test_loop_enabled": True, "bootstrap_task": True, "final_verification_task": False, "min_task_interval_seconds": 0, "test_loop": {}, "implementation_loop": {}}, "version": 1}


def _read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"JSON inválido em {path}: linha {error.lineno}, coluna {error.colno}") from error
    except (OSError, UnicodeError):
        return deepcopy(default)
    return value if isinstance(value, dict) else deepcopy(default)


def load_documents(root: Path) -> dict[str, Any]:
    """Carrega configuração, revisão e instrução crítica sem perder chaves desconhecidas."""
    if not (root / CONFIG_RELATIVE_PATH).exists():
        init_project(root, integrations=())
    ensure_review_workspace(root)
    instruction_path = root / INSTRUCTIONS_RELATIVE_PATH
    return {"config": _read_json(root / CONFIG_RELATIVE_PATH, _default_config()), "review": _read_json(root / REVIEW_RELATIVE_PATH, DEFAULT_REVIEW_CONFIG), "instructions": instruction_path.read_text(encoding="utf-8") if instruction_path.exists() else ""}


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def validate_documents(config: dict[str, Any], review: dict[str, Any], instructions: str) -> None:
    """Valida modos conhecidos antes de persistir qualquer documento."""
    if not isinstance(config, dict) or not isinstance(review, dict) or not isinstance(instructions, str):
        raise ValueError("documentos inválidos")
    backlog = config.get("backlog", {})
    if not isinstance(backlog, dict) or backlog.get("development_mode", "sequential") not in VALID_DEVELOPMENT_MODES:
        raise ValueError("backlog.development_mode inválido")
    if backlog.get("task_delivery_scope", "task") not in {"task", "node"}:
        raise ValueError("backlog.task_delivery_scope inválido")
    for name in ("test_loop", "implementation_loop"):
        loop = backlog.get(name, {})
        if not isinstance(loop, dict) or loop.get("mode", "task_order") not in VALID_LOOP_MODES or loop.get("l2_children_mode", "none") not in VALID_CHILDREN_MODES:
            raise ValueError(f"backlog.{name} inválido")
    if review.get("default_agent", "codex") not in {"codex", "claude", "gemini", "antigravity"}:
        raise ValueError("agente de revisão inválido")
    if not isinstance(review.get("enabled", False), bool):
        raise ValueError("review-agents.enabled deve ser booleano")


def save_documents(root: Path, documents: dict[str, Any]) -> None:
    """Salva configuração, revisão e instruções de forma atômica."""
    validate_documents(documents["config"], documents["review"], documents["instructions"])
    _atomic_write(root / CONFIG_RELATIVE_PATH, json.dumps(documents["config"], indent=2, ensure_ascii=False) + "\n")
    _atomic_write(root / REVIEW_RELATIVE_PATH, json.dumps(documents["review"], indent=2, ensure_ascii=False) + "\n")
    _atomic_write(root / INSTRUCTIONS_RELATIVE_PATH, documents["instructions"])


def apply_backlog_form(config: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
    """Aplica valores guiados mantendo todas as opções avançadas existentes."""
    result = deepcopy(config)
    backlog = result.setdefault("backlog", {})
    for key in ("development_mode", "task_delivery_scope", "task_batch_scope"):
        if values.get(key) not in (None, ""):
            backlog[key] = values[key]
    for key in ("task_batch_size", "min_task_interval_seconds"):
        if values.get(key) not in (None, ""):
            backlog[key] = int(values[key])
    for key in ("test_loop_enabled", "bootstrap_task", "final_verification_task"):
        if key in values and values[key] is not None:
            backlog[key] = bool(values[key])
    for loop_name in ("test_loop", "implementation_loop"):
        loop = backlog.setdefault(loop_name, {})
        prefix = "test" if loop_name == "test_loop" else "implementation"
        for key in ("mode", "l2_children_mode"):
            if values.get(f"{prefix}_{key}") not in (None, ""):
                loop[key] = values[f"{prefix}_{key}"]
        if values.get(f"{prefix}_batch_size") not in (None, ""):
            loop["batch_size"] = int(values[f"{prefix}_batch_size"])
        for key in ("l3_loop_enabled", "l3_include_parent"):
            if f"{prefix}_{key}" in values:
                loop[key] = bool(values[f"{prefix}_{key}"])
    return result


class KeyboardTUI:
    """Editor de terminal com menus, formulários e editor bruto de texto."""

    PAGES = (("init", "Init"), ("backlog", "Backlog"), ("config", "Config JSON"), ("review", "Revisão"), ("instructions", "Instruções"))

    def __init__(self, screen: Any, root: Path):
        self.screen = screen
        self.root = root
        self.documents = load_documents(root)
        self.page = 0
        self.field = 0
        self.message = "1-5 abas · ? ajuda · Esc destrava · Enter seleciona · S/F2 salva · Q sai"
        self.integration_values = {name: True for name in SUPPORTED_INTEGRATIONS}
        self._terminal_attributes = None

    def colors(self) -> None:
        curses.start_color()
        curses.use_default_colors()
        if curses.COLORS >= 256:
            curses.init_pair(1, 255, curses.COLOR_BLACK)
            curses.init_pair(2, 208, curses.COLOR_BLACK)
        else:
            curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
            curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        self.screen.bkgd(" ", curses.color_pair(1))

    def run(self) -> None:
        self.colors()
        curses.curs_set(1)
        self.screen.keypad(True)
        self.screen.timeout(-1)
        try:
            self._disable_flow_control()
            while True:
                self.render()
                if self.handle(self.screen.get_wch()):
                    break
        except KeyboardInterrupt:
            # Ctrl+C deve sair sem deixar o terminal preso no modo curses.
            pass
        finally:
            self._restore_terminal()

    def _disable_flow_control(self) -> None:
        """Libera Ctrl+S do controle de fluxo do terminal para o comando salvar."""
        try:
            descriptor = self.screen.fileno()
            self._terminal_attributes = termios.tcgetattr(descriptor)
            current = termios.tcgetattr(descriptor)
            current[0] &= ~(termios.IXON | termios.IXOFF | termios.IXANY)
            termios.tcsetattr(descriptor, termios.TCSANOW, current)
        except (AttributeError, OSError, termios.error):
            self._terminal_attributes = None

    def _restore_terminal(self) -> None:
        if self._terminal_attributes is None:
            return
        try:
            termios.tcsetattr(self.screen.fileno(), termios.TCSANOW, self._terminal_attributes)
        except (AttributeError, OSError, termios.error):
            pass

    def fields(self) -> list[tuple[str, str, str]]:
        if self.page == 0:
            return [("integration_" + name, name.title(), "bool") for name in SUPPORTED_INTEGRATIONS] + [("init-project", "Inicializar / atualizar skills", "action"), ("run-setup", "Executar setup da stack", "action")]
        if self.page == 1:
            return [(key, label, "choice") for key, label in (("development_mode", "Modo de desenvolvimento"), ("task_delivery_scope", "Entrega"), ("task_batch_size", "Tamanho do lote"), ("task_batch_scope", "Escopo do lote"), ("min_task_interval_seconds", "Intervalo mínimo"), ("test_loop_enabled", "Loop de testes"), ("bootstrap_task", "Bootstrap"), ("final_verification_task", "Verificação final"), ("test_mode", "Modo de testes"), ("test_l2_children_mode", "Filhos L3 nos testes"), ("implementation_mode", "Modo de implementação"), ("implementation_l2_children_mode", "Filhos L3 na implementação"), ("test_l3_loop_enabled", "Loop L3 nos testes"), ("implementation_l3_loop_enabled", "Loop L3 na implementação"), ("test_l3_include_parent", "Pai L2 no L3"))]
        if self.page == 2:
            return [(key, label, "choice") for key, label in (("testing_profile", "Perfil de testes"), ("contract_enabled", "Contrato habilitado"), ("contract_language", "Linguagem do contrato"), ("description_language", "Idioma das descrições"), ("static_enabled", "Análise estática habilitada"), ("allow_marked_credentials", "Permitir credenciais marcadas"), ("tracked_extensions", "Extensões rastreadas"), ("test_commands", "Comandos de teste"), ("static_adapter", "Adaptador estático"), ("contract_max_chars", "Tamanho máximo da descrição"))]
        if self.page == 3:
            fields = [(key, label, "choice") for key, label in (("review_enabled", "Revisão automática"), ("review_agent", "Agente padrão"), ("review_model", "Modelo"), ("review_reasoning", "Reasoning"), ("review_prompt", "Prompt padrão"), ("review_timeout", "Timeout"))]
            for event in ("test", "implementation", "change"):
                for scope in ("l2", "l3", "l2_and_l3", "all"):
                    fields.append((f"review_trigger_{event}_{scope}", f"Revisar {event} · {scope}", "choice"))
            return fields
        return [("instructions", "Informação crítica", "choice")]

    def _nested(self, key: str) -> tuple[dict[str, Any], str]:
        if key.startswith("test_"):
            return self.documents["config"]["backlog"].setdefault("test_loop", {}), key[5:]
        if key.startswith("implementation_"):
            return self.documents["config"]["backlog"].setdefault("implementation_loop", {}), key[15:]
        return self.documents["config"].setdefault("backlog", {}), key

    def value(self, key: str) -> Any:
        if key.startswith("integration_"):
            return self.integration_values[key[12:]]
        if key.startswith("review_"):
            if key.startswith("review_trigger_"):
                event, scope = key.removeprefix("review_trigger_").split("_", 1)
                return self.documents["review"].get("triggers", {}).get(event, {}).get(scope, False)
            if key == "review_timeout":
                return self.documents["review"].get("timeout_seconds", 900)
            if key == "review_prompt":
                return self.documents["review"].get("standard_prompt", "")
            return self.documents["review"].get(key[7:], "")
        if key == "instructions":
            return self.documents["instructions"] or "(vazio)"
        if key == "testing_profile":
            return self.documents["config"].get("testing", {}).get("profile", "mvp")
        if key == "contract_enabled":
            return self.documents["config"].get("contract", {}).get("enabled", True)
        if key == "contract_language":
            return self.documents["config"].get("contract", {}).get("code_language", "python")
        if key == "description_language":
            return self.documents["config"].get("contract", {}).get("description_language", "pt-BR")
        if key == "static_enabled":
            return self.documents["config"].get("static_analysis", {}).get("enabled", True)
        if key == "allow_marked_credentials":
            return self.documents["config"].get("static_analysis", {}).get("allow_marked_test_credentials", True)
        if key == "tracked_extensions":
            return self.documents["config"].get("tracked_extensions", "default")
        if key == "test_commands":
            return "configurados" if self.documents["config"].get("test_commands") else "nenhum"
        if key == "static_adapter":
            command = self.documents["config"].get("static_analysis", {}).get("adapter_command")
            return "nenhum" if not command else "configurado"
        if key == "contract_max_chars":
            return self.documents["config"].get("contract", {}).get("short_description_max_chars", 160)
        target, name = self._nested(key)
        return target.get(name, False if key.endswith(("enabled", "parent")) else "")

    def set_value(self, key: str, value: Any) -> None:
        if key.startswith("integration_"):
            self.integration_values[key[12:]] = bool(value)
        elif key.startswith("review_"):
            if key.startswith("review_trigger_"):
                event, scope = key.removeprefix("review_trigger_").split("_", 1)
                self.documents["review"].setdefault("triggers", {}).setdefault(event, {})[scope] = bool(value)
            elif key == "review_timeout":
                self.documents["review"]["timeout_seconds"] = int(value)
            elif key == "review_prompt":
                self.documents["review"]["standard_prompt"] = value
            else:
                self.documents["review"][key[7:]] = value
        elif key == "instructions":
            self.documents["instructions"] = "" if value == "(vazio)" else value
        elif key in {"testing_profile", "contract_enabled", "contract_language", "description_language"}:
            self.documents["config"].setdefault("testing", {})["profile"] = value if key == "testing_profile" else self.documents["config"].setdefault("testing", {}).get("profile", "mvp")
            if key.startswith("contract_"):
                self.documents["config"].setdefault("contract", {})[key.removeprefix("contract_") if key != "contract_language" else "code_language"] = value
            if key == "description_language":
                self.documents["config"].setdefault("contract", {})["description_language"] = value
        elif key in {"static_enabled", "allow_marked_credentials"}:
            self.documents["config"].setdefault("static_analysis", {})["enabled" if key == "static_enabled" else "allow_marked_test_credentials"] = value
        elif key == "tracked_extensions":
            presets = {"default": [".py", ".js", ".ts"], "python": [".py"], "web": [".html", ".css", ".js", ".ts"]}
            self.documents["config"]["tracked_extensions"] = presets.get(value, self.documents["config"].get("tracked_extensions", []))
        elif key == "test_commands":
            presets = {"nenhum": [], "pytest": [{"name": "all", "command": ["pytest", "-q"]}], "npm test": [{"name": "all", "command": ["npm", "test"]}]}
            self.documents["config"]["test_commands"] = presets.get(value, self.documents["config"].get("test_commands", []))
        elif key == "static_adapter":
            self.documents["config"].setdefault("static_analysis", {})["adapter_command"] = None if value == "nenhum" else self.documents["config"].get("static_analysis", {}).get("adapter_command")
        elif key == "contract_max_chars":
            self.documents["config"].setdefault("contract", {})["short_description_max_chars"] = int(value)
        else:
            target, name = self._nested(key)
            target[name] = value

    def choices(self, key: str) -> list[Any]:
        current = self.value(key)
        if key.startswith("review_trigger_"):
            return [False, True]
        known: dict[str, list[Any]] = {
            "development_mode": ["sequential", "separated"], "task_delivery_scope": ["task", "node"], "task_batch_size": [1, 2, 3, 4, 5], "task_batch_scope": ["task", "node"], "min_task_interval_seconds": [0, 3, 5, 10, 30, 60, 300], "test_loop_enabled": [True, False], "bootstrap_task": [True, False], "final_verification_task": [False, True], "test_mode": list(VALID_LOOP_MODES), "implementation_mode": list(VALID_LOOP_MODES), "test_l2_children_mode": list(VALID_CHILDREN_MODES), "implementation_l2_children_mode": list(VALID_CHILDREN_MODES), "test_l3_loop_enabled": [True, False], "implementation_l3_loop_enabled": [True, False], "test_l3_include_parent": [True, False], "testing_profile": ["mvp", "full"], "contract_enabled": [True, False], "contract_language": ["python", "javascript", "typescript", "php"], "description_language": ["pt-BR", "en-US"], "static_enabled": [True, False], "allow_marked_credentials": [True, False], "tracked_extensions": ["default", "python", "web"], "test_commands": ["nenhum", "pytest", "npm test"], "static_adapter": ["nenhum", "configurado"], "contract_max_chars": [80, 120, 160, 240], "review_enabled": [True, False], "review_agent": ["codex", "claude", "gemini", "antigravity"], "review_model": ["", "gpt-5", "claude-sonnet", "gemini-2.5-pro"], "review_reasoning": ["low", "medium", "high"], "review_timeout": [300, 600, 900, 1800], "review_prompt": ["Confirme se a task aprovada foi implementada completamente.", "Confira o Draw e crie changes para lacunas.", "Não criar changes quando estiver completo."], "instructions": ["(vazio)", "Sempre validar o contexto antes de implementar.", "Nunca ignorar informação crítica."]}
        options = list(known.get(key, [current]))
        if current not in options:
            options.insert(0, current)
        return options

    def cycle(self, key: str) -> None:
        options = self.choices(key)
        current = self.value(key)
        self.set_value(key, options[(options.index(current) + 1) % len(options)])

    def help_for(self, key: str) -> str:
        """Explica, em linguagem curta, o efeito da opção selecionada."""
        descriptions = {
            "development_mode": "Define se L2 e L3 seguem uma fila única ou podem ser consumidos em loops separados.",
            "task_delivery_scope": "Escolhe se cada entrega contém uma task ou o pacote completo do nó.",
            "task_batch_size": "Define quantos itens são entregues por vez ao agente.",
            "task_batch_scope": "Define se o lote agrupa tasks ou nós.",
            "min_task_interval_seconds": "Impõe uma pausa mínima entre entregas ao agente.",
            "test_loop_enabled": "Liga ou desliga o loop que cria e valida testes.",
            "bootstrap_task": "Inclui a preparação inicial do projeto no backlog.",
            "final_verification_task": "Inclui uma verificação final no backlog.",
            "test_mode": "Escolhe a ordem de entrega do loop de testes.",
            "implementation_mode": "Escolhe a ordem de entrega do loop de implementação.",
            "test_l2_children_mode": "Define se o L2 leva contexto ou os filhos L3 no loop de testes.",
            "implementation_l2_children_mode": "Define se o L2 leva contexto ou os filhos L3 no loop de implementação.",
            "test_l3_loop_enabled": "Permite desativar somente o loop L3 de testes.",
            "implementation_l3_loop_enabled": "Permite desativar somente o loop L3 de implementação.",
            "test_l3_include_parent": "Inclui o L2 pai como contexto quando o loop entrega L3.",
            "review_enabled": "Ativa ou desativa a chamada automática do agente de revisão.",
            "review_agent": "Escolhe qual agente externo revisará uma task concluída.",
            "review_model": "Escolhe o modelo enviado ao agente de revisão.",
            "review_reasoning": "Define o nível de raciocínio solicitado ao agente de revisão.",
            "review_prompt": "Escolhe o prompt padrão usado na revisão.",
            "review_timeout": "Limita o tempo de espera pela revisão.",
            "instructions": "Texto crítico repetido em todos os loops configurados.",
            "init-project": "Salva as escolhas e executa o bootstrap das skills selecionadas.",
            "run-setup": "Detecta a stack e atualiza a configuração operacional do projeto.",
        }
        if key.startswith("review_trigger_"):
            return "Controla se a revisão automática é disparada para este evento e escopo de loop."
        if key.startswith("integration_"):
            return "Define se esta integração recebe as skills durante o init."
        return descriptions.get(key, "Altera a opção correspondente no arquivo de configuração.")

    def help_path(self, key: str) -> str:
        if key.startswith("review_"):
            return f"{REVIEW_RELATIVE_PATH}:{key[7:]}"
        if key == "instructions":
            return INSTRUCTIONS_RELATIVE_PATH
        if key.startswith("integration_") or key in {"init-project", "run-setup"}:
            return "looper init / .looper/config.json"
        if key.startswith("test_"):
            return f"{CONFIG_RELATIVE_PATH}:backlog.test_loop"
        if key.startswith("implementation_"):
            return f"{CONFIG_RELATIVE_PATH}:backlog.implementation_loop"
        return f"{CONFIG_RELATIVE_PATH}:backlog.{key}"

    def show_help(self) -> None:
        """Mostra ajuda contextual sem abrir editor nem exigir digitação."""
        entries = self.fields()
        key, label, _ = entries[self.field]
        height, width = self.screen.getmaxyx()
        self.screen.erase()
        self.screen.addstr(0, 0, " AJUDA DA OPÇÃO ".center(width)[:width], curses.color_pair(2) | curses.A_BOLD)
        lines = [
            label,
            "",
            f"O que muda: {self.help_for(key)}",
            f"Arquivo/caminho: {self.help_path(key)}",
            f"Valor atual: {self.value(key)}",
        ]
        if self.choices(key):
            lines.append("Opções: " + ", ".join(str(option) for option in self.choices(key)))
        row = 2
        for paragraph in lines:
            wrapped = textwrap.wrap(paragraph, width=max(10, width - 6)) or [""]
            for line in wrapped:
                if row >= height - 2:
                    break
                self.screen.addstr(row, 2, line[: max(1, width - 4)], curses.color_pair(1))
                row += 1
        self.screen.addstr(height - 1, 2, "Qualquer tecla volta · Esc também volta"[: max(1, width - 4)], curses.color_pair(2))
        self.screen.refresh()
        self.screen.get_wch()

    def render(self) -> None:
        height, width = self.screen.getmaxyx()
        self.screen.erase()
        self.screen.addstr(0, 0, " LOOPER CONFIG ".center(width), curses.color_pair(2) | curses.A_BOLD)
        tabs = "  ".join(f"[{i + 1} {label}]" if i == self.page else f"  {i + 1} {label} " for i, (_, label) in enumerate(self.PAGES))
        self.screen.addstr(2, 2, tabs[: max(1, width - 4)], curses.color_pair(2))
        entries = self.fields()
        height_for_fields = max(1, height - 7)
        start = max(0, min(self.field - height_for_fields + 1, len(entries) - height_for_fields))
        for row, (key, label, kind) in enumerate(entries[start : start + height_for_fields], start=4):
            index = start + row - 4
            selected = index == self.field
            value = "[x]" if kind in {"bool", "choice"} and self.value(key) is True else "[ ]" if kind in {"bool", "choice"} and self.value(key) is False else "" if kind == "action" else str(self.value(key))
            text = f"{'▶' if selected else ' '} {label}: {value}"
            self.screen.addstr(row, 2, text[: max(1, width - 4)], (curses.color_pair(2) if selected else curses.color_pair(1)) | (curses.A_BOLD if selected else 0))
        self.screen.addstr(max(4, height - 3), 2, self.message[: max(1, width - 4)], curses.color_pair(2))
        footer = "1-5 abas · ↑/↓/Tab opções · Enter/Space selecionar · ? ajuda · Esc destrava · R/F5 recarrega · S/F2 salva · Q sai"
        self.screen.addstr(height - 1, 2, footer[: max(1, width - 3)], curses.color_pair(1))
        self.screen.refresh()

    def action(self, key: str) -> None:
        if key == "init-project":
            save_documents(self.root, self.documents)
            init_project(self.root, integrations=tuple(name for name, enabled in self.integration_values.items() if enabled))
            self.message = "Init concluído: skills atualizadas."
        elif key == "run-setup":
            stack = configure_project(self.root)
            ensure_stack_gitignore(self.root, stack.get("languages", []))
            self.documents = load_documents(self.root)
            self.message = "Setup concluído: " + (", ".join(stack.get("languages", [])) or "stack não detectada")

    def handle(self, key: Any) -> bool:
        if key in ("q", "Q", 3, 17):
            return True
        numeric_key = chr(key) if isinstance(key, int) and ord("1") <= key <= ord("5") else key
        if numeric_key in ("1", "2", "3", "4", "5"):
            self.page = int(numeric_key) - 1
            self.field = 0
            self.message = f"Aba {numeric_key} selecionada."
            return False
        if key in ("\x1b", 27):
            self.page = 0
            self.field = 0
            self.message = "TUI destravada e seleção reiniciada."
            return False
        if key in ("?", "h", "H"):
            self.show_help()
            return False
        if key in ("r", "R", curses.KEY_F5):
            self.documents = load_documents(self.root)
            self.page = 0
            self.field = 0
            self.message = "Configurações recarregadas; alterações não salvas foram descartadas."
            return False
        if key in (curses.KEY_RIGHT, 14):
            self.page = (self.page + 1) % len(self.PAGES)
            self.field = 0
            return False
        if key in (curses.KEY_LEFT, 16):
            self.page = (self.page - 1) % len(self.PAGES)
            self.field = 0
            return False
        entries = self.fields()
        if key in (curses.KEY_DOWN, "\t"):
            self.field = (self.field + 1) % len(entries)
            return False
        if key == curses.KEY_UP:
            self.field = (self.field - 1) % len(entries)
            return False
        if key in (" ", "\n", curses.KEY_ENTER):
            item, _, kind = entries[self.field]
            if kind in {"bool", "choice"}:
                self.cycle(item)
            else:
                try:
                    self.action(item)
                except (OSError, ValueError, json.JSONDecodeError) as error:
                    self.message = f"Erro: {error}"
            return False
        if key in (19, 23, "s", "S", curses.KEY_F2):
            try:
                save_documents(self.root, self.documents)
                self.message = "Configurações salvas."
            except ValueError as error:
                self.message = f"Erro: {error}"
            return False
        return False


def run_tui(root: Path) -> None:
    """Inicia a TUI nativa sem dependências externas ou mouse."""
    try:
        curses.wrapper(lambda screen: KeyboardTUI(screen, root).run())
    except curses.error as error:
        raise RuntimeError("o terminal atual não suporta curses adequadamente") from error
