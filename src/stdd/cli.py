import json
import sys
from typing import List, Optional
from pathlib import Path

import typer

from .core import (
    ensure_gitignore,
    get_incremental_draw_diff,
    get_logged_draw_diff,
    init_project,
    project_root,
    record_run_entry,
    run_tests,
)
from .draw import create_draw, find_addressed_questions, read_draw_index, serve_draw
from .traceability import associate_node_reference, associate_node_references
from .setup import (
    FRONTEND_ANALYSIS_MODES,
    SUPPORTED_INTEGRATIONS,
    available_integrations,
    configure_frontend_analysis,
    configure_project,
    ensure_stack_gitignore,
    has_frontend_surface,
)

app = typer.Typer(help="STDD: CLI de suporte ao desenvolvimento orientado por testes.")
draw_app = typer.Typer(help="Cria e visualiza desenhos JSON do projeto.")
app.add_typer(draw_app, name="draw")


@app.command()
def init(
    project: Path = typer.Argument(Path("."), help="Diretório do projeto a inicializar; por padrão, o diretório atual."),
    integration: List[str] = typer.Option(None, "--integration", help="Agente a integrar: codex, claude ou gemini; pode repetir."),
    all_integrations: bool = typer.Option(False, "--all-integrations", help="Instala as skills para Codex, Claude e Gemini."),
    interactive: bool = typer.Option(False, "--interactive", help="Abre a seleção numérica de integrações e setup."),
    frontend_analysis: Optional[str] = typer.Option(None, "--frontend-analysis", help="Gate frontend: blocking, warning ou disabled."),
) -> None:
    """Inicializa a estrutura do STDD e instala as skills dos agentes.
    Cria o diretório-alvo quando necessário, depois cria .stdd/ e .agents/skills.
    """
    target = project.expanduser().resolve()
    if target.exists() and not target.is_dir():
        typer.echo(f"Erro: o destino não é um diretório: {target}", err=True)
        raise typer.Exit(1)
    target.mkdir(parents=True, exist_ok=True)
    requested = tuple(integration or ("codex",))
    if all_integrations:
        requested = SUPPORTED_INTEGRATIONS
    elif not integration and (interactive or sys.stdin.isatty()):
        requested = choose_integrations()
    invalid = sorted(set(requested) - set(SUPPORTED_INTEGRATIONS))
    if invalid:
        typer.echo(f"Erro: integrações desconhecidas: {', '.join(invalid)}", err=True)
        raise typer.Exit(1)
    if frontend_analysis is not None and frontend_analysis not in FRONTEND_ANALYSIS_MODES:
        typer.echo("Erro: --frontend-analysis deve ser blocking, warning ou disabled.", err=True)
        raise typer.Exit(1)
    created = init_project(target, integrations=requested)
    typer.echo(f"Projeto inicializado em {target}. {len(created)} itens criados.")
    if interactive or sys.stdin.isatty():
        if typer.confirm("Executar o setup para detectar a stack agora?", default=True):
            ensure_gitignore(target)
            stack = configure_project(target)
            ensure_stack_gitignore(target, stack["languages"])
            typer.echo(f"Stack: {', '.join(stack['languages']) or 'não detectada'}")
            if frontend_analysis is None and has_frontend_surface(target, stack):
                frontend_analysis = choose_frontend_analysis()
    if frontend_analysis is not None:
        configure_frontend_analysis(target, frontend_analysis)
    unavailable = [name for name, found in available_integrations().items() if name in requested and not found]
    if unavailable:
        typer.echo(f"Aviso: agente(s) não encontrado(s) no PATH: {', '.join(unavailable)}.", err=True)


def choose_integrations() -> tuple[str, ...]:
    """Apresenta uma seleção múltipla numerada para os agentes disponíveis.
    Aceita números separados por vírgula ou a opção todos e retorna integrações únicas.
    """
    typer.echo("Selecione as integrações do agente (ex.: 1,3 ou 4 para todos):")
    for index, name in enumerate((*SUPPORTED_INTEGRATIONS, "todos"), start=1):
        typer.echo(f"  {index}. {name.title()}")
    answer = typer.prompt("Integrações", default="1")
    choices = {part.strip() for part in answer.split(",") if part.strip()}
    if "4" in choices or "todos" in {choice.lower() for choice in choices}:
        return SUPPORTED_INTEGRATIONS
    selected = tuple(
        name for index, name in enumerate(SUPPORTED_INTEGRATIONS, start=1) if str(index) in choices
    )
    if not selected:
        typer.echo("Nenhuma opção válida; usando Codex.")
        return ("codex",)
    return selected


def choose_frontend_analysis() -> str:
    """Pergunta a política do gate frontend após evidência local da superfície."""
    typer.echo("Escolha a política de análise estática frontend:")
    typer.echo("  1. blocking (bloqueia achados comprovados)")
    typer.echo("  2. warning (relata sem bloquear)")
    typer.echo("  3. disabled (desativa somente o frontend)")
    choice = typer.prompt("Análise frontend", default="1")
    return {"1": "blocking", "2": "warning", "3": "disabled"}.get(choice.strip(), "blocking")


@app.command()
def setup(
    project: Path = typer.Argument(Path("."), help="Diretório do projeto a configurar; por padrão, o diretório atual."),
    frontend_analysis: Optional[str] = typer.Option(None, "--frontend-analysis", help="Gate frontend: blocking, warning ou disabled."),
) -> None:
    """Detecta a stack e gera runners e regras de ambiente específicos do projeto.
    Não instala dependências nem executa testes, permitindo revisão antes de ações externas.
    """
    target = project.expanduser().resolve()
    if target.exists() and not target.is_dir():
        typer.echo(f"Erro: o destino não é um diretório: {target}", err=True)
        raise typer.Exit(1)
    target.mkdir(parents=True, exist_ok=True)
    if not (target / ".stdd" / "config.json").exists():
        init_project(target)
    if frontend_analysis is not None and frontend_analysis not in FRONTEND_ANALYSIS_MODES:
        typer.echo("Erro: --frontend-analysis deve ser blocking, warning ou disabled.", err=True)
        raise typer.Exit(1)
    ensure_gitignore(target)
    stack = configure_project(target)
    ensure_stack_gitignore(target, stack["languages"])
    if frontend_analysis is not None:
        configure_frontend_analysis(target, frontend_analysis)
    typer.echo(json.dumps({"stack": stack, "integrations": available_integrations()}, ensure_ascii=False, indent=2))


@app.command("test")
def test_all(
    suite: List[str] = typer.Option(None, "--suite", help="Executa somente as suítes informadas; pode repetir."),
    exclude: List[str] = typer.Option(None, "--exclude", help="Não executa as suítes informadas; pode repetir."),
    profile: Optional[str] = typer.Option(None, "--profile", help="Sobrescreve o perfil de testes desta execução."),
    approve_actions: bool = typer.Option(False, "--approve-actions", help="Autoriza suítes marcadas como caras ou mutáveis."),
) -> None:
    """Executa o alias global de testes e consolida todas as suítes configuradas.
    Inclui contratos, análise estática e runners com seus próprios ciclos de setup e cleanup.
    """
    process, result = run_tests(
        project_root(),
        include_suites=set(suite) if suite else None,
        exclude_suites=set(exclude or []),
        approve_actions=approve_actions,
        profile=profile,
    )
    typer.echo(process.stdout, nl=False)
    typer.echo(f"\nResultado: {result['status']}")
    if result["status"] != "passed":
        typer.echo(process.stderr, err=True)
        raise typer.Exit(process.returncode or 1)


@app.command("log")
def log_work(
    description: str = typer.Argument(..., help="Frase curta explicando o que foi feito."),
    bug: bool = typer.Option(False, "--bug", "-b", help="Marca o tipo de trabalho como bug."),
    teste: bool = typer.Option(False, "--test", "--teste", "-t", help="Marca o tipo de trabalho como teste."),
    implementacao: bool = typer.Option(False, "--impl", "--implementacao", "-i", help="Marca o tipo de trabalho como implementacao."),
    refactor: bool = typer.Option(False, "--refactor", "-r", help="Marca o tipo de trabalho como refactor."),
    work_type: List[str] = typer.Option(
        None,
        "--type",
        help="Tipo de trabalho em formato texto (bug, teste, implementacao, refactor).",
    ),
) -> None:
    """Registra uma alteração de código com estatísticas do Git em .stdd/runs.
    Coleta flags de tipo e marca alterações incrementais grandes como retrabalho automaticamente.
    """
    types: list[str] = []
    if bug:
        types.append("bug")
    if teste:
        types.append("teste")
    if implementacao:
        types.append("implementacao")
    if refactor:
        types.append("refactor")
    if work_type:
        types.extend(work_type)

    try:
        created_file = record_run_entry(project_root(), description, types)
        typer.echo(f"Registro gravado em {created_file}")
    except ValueError as err:
        typer.echo(f"Erro: {err}", err=True)
        raise typer.Exit(1)


@draw_app.command("create")
def draw_create(
    data_json: str = typer.Option(..., "--data-json", help="Payload JSON inline do desenho."),
) -> None:
    """Valida e grava somente o JSON de um desenho em .stdd/draws.
    Atualiza o índice leve e nunca cria HTML individual para o desenho.
    """
    try:
        payload = json.loads(data_json)
        created = create_draw(project_root(), payload)
    except (json.JSONDecodeError, ValueError) as error:
        typer.echo(f"Erro: {error}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Desenho gravado em {created}")


@draw_app.command("list")
def draw_list() -> None:
    """Lista os desenhos disponíveis sem carregar seus grafos completos.
    Lê somente os metadados de .stdd/draws/index.json.
    """
    try:
        entries = read_draw_index(project_root()).get("draws", [])
    except ValueError as error:
        typer.echo(f"Erro: {error}", err=True)
        raise typer.Exit(1)
    if not entries:
        typer.echo("Nenhum desenho disponível.")
        return
    for entry in entries:
        typer.echo(f"{entry['id']}\t{entry.get('title', '')}\t{entry.get('node_count', 0)} nós\t{entry.get('edge_count', 0)} relações")


@draw_app.command("questions")
def draw_questions() -> None:
    """Localiza perguntas abertas marcadas com @stdd para o Draw Answer."""
    try:
        questions = find_addressed_questions(project_root())
    except (OSError, ValueError, RuntimeError) as error:
        typer.echo(f"Erro: {error}", err=True)
        raise typer.Exit(1)
    typer.echo(json.dumps(questions, ensure_ascii=False, indent=2))


@draw_app.command("diff")
def draw_diff(
    run_id: Optional[str] = typer.Option(None, "--run-id", help="ID do log histórico a consultar."),
) -> None:
    """Exibe mudanças atuais dos JSONs de Draws desde o último stdd log.
    Com --run-id, consulta o diff histórico salvo naquele log.
    """
    root = project_root()
    if run_id is None:
        diff_stats, draws, _ = get_incremental_draw_diff(root)
        typer.echo("Alterações dos Draws desde o último log:")
        typer.echo(
            f"Arquivos: {diff_stats['files_changed']} · "
            f"Linhas: +{diff_stats['lines_added']} / -{diff_stats['lines_deleted']}"
        )
    else:
        diff_record = get_logged_draw_diff(root, run_id=run_id)
        if diff_record is None:
            typer.echo("Nenhum snapshot de Draw encontrado nos logs.")
            return
        typer.echo(f"Log: {diff_record['run_id']} · {diff_record['timestamp']}")
        draws = diff_record.get("draws", [])
    if not draws:
        message = (
            "Nenhuma alteração nos JSONs de Draws desde o último log."
            if run_id is None
            else "Nenhuma alteração nos JSONs de Draws neste log."
        )
        typer.echo(message)
        return
    for draw in draws:
        typer.echo(f"\n[{draw.get('status', 'changed')}] {draw.get('path', 'desenho desconhecido')}")
        typer.echo(str(draw.get("diff", "")))


@draw_app.command("associate-reference")
def draw_associate_reference(
    draw_id: str = typer.Option(..., "--draw-id", help="ID do desenho que contém o nó."),
    node_id: Optional[int] = typer.Option(None, "--node-id", help="ID numérico do nó para associação unitária."),
    qualified_name: Optional[str] = typer.Option(None, "--qualified-name", help="Símbolo qualificado da codebase."),
    source_dependency: List[str] = typer.Option(None, "--source-dependency", help="Símbolo qualificado relacionado; pode repetir."),
    batch_json: Optional[str] = typer.Option(None, "--batch-json", help="Lista JSON de associações unitárias."),
) -> None:
    """Associa um nó a símbolos qualificados sem calcular facts derivados."""
    try:
        if batch_json is not None:
            batch = json.loads(batch_json)
            output = associate_node_references(project_root(), draw_id, batch)
        else:
            if node_id is None or qualified_name is None:
                raise ValueError("node_id e qualified_name são obrigatórios fora do modo lote")
            output = associate_node_reference(project_root(), draw_id, node_id, qualified_name, source_dependency or [])
    except (json.JSONDecodeError, ValueError) as error:
        typer.echo(f"Erro: {error}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Referência associada em {output}")


@draw_app.command("serve")
def draw_serve(
    port: int = typer.Option(8765, "--port", min=1, max=65535, help="Porta local do viewer."),
) -> None:
    """Serve o viewer Draw localmente para carregar JSONs por fetch.
    Vincula o servidor a 127.0.0.1 e mantém o processo ativo até interrupção.
    """
    try:
        serve_draw(project_root(), port=port)
    except (RuntimeError, ValueError) as error:
        typer.echo(f"Erro: {error}", err=True)
        raise typer.Exit(1)







if __name__ == "__main__":
    app()
