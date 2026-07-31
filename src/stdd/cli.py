import json
from typing import List, Optional
from pathlib import Path

import typer

from .core import ensure_gitignore, init_project, project_root, record_run_entry, run_tests
from .draw import create_draw, read_draw_index, serve_draw
from .setup import SUPPORTED_INTEGRATIONS, available_integrations, configure_project, ensure_stack_gitignore

app = typer.Typer(help="STDD: CLI de suporte ao desenvolvimento orientado por testes.")
draw_app = typer.Typer(help="Cria e visualiza desenhos JSON do projeto.")
app.add_typer(draw_app, name="draw")


@app.command()
def init(
    project: Path = typer.Argument(Path("."), help="Diretório do projeto a inicializar; por padrão, o diretório atual."),
    integration: List[str] = typer.Option(None, "--integration", help="Agente a integrar: codex, claude ou gemini; pode repetir."),
    all_integrations: bool = typer.Option(False, "--all-integrations", help="Instala as skills para Codex, Claude e Gemini."),
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
    invalid = sorted(set(requested) - set(SUPPORTED_INTEGRATIONS))
    if invalid:
        typer.echo(f"Erro: integrações desconhecidas: {', '.join(invalid)}", err=True)
        raise typer.Exit(1)
    created = init_project(target, integrations=requested)
    typer.echo(f"Projeto inicializado em {target}. {len(created)} itens criados.")
    unavailable = [name for name, found in available_integrations().items() if name in requested and not found]
    if unavailable:
        typer.echo(f"Aviso: agente(s) não encontrado(s) no PATH: {', '.join(unavailable)}.", err=True)


@app.command()
def setup(
    project: Path = typer.Argument(Path("."), help="Diretório do projeto a configurar; por padrão, o diretório atual."),
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
    ensure_gitignore(target)
    stack = configure_project(target)
    ensure_stack_gitignore(target, stack["languages"])
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


@draw_app.command("serve")
def draw_serve(
    port: int = typer.Option(8765, "--port", min=1, max=65535, help="Porta local do viewer."),
) -> None:
    """Serve o viewer Draw localmente para carregar JSONs por fetch.
    Vincula o servidor a 127.0.0.1 e mantém o processo ativo até interrupção.
    """
    serve_draw(project_root(), port=port)







if __name__ == "__main__":
    app()
