import json

from typer.testing import CliRunner

from stdd.cli import app
from stdd.draw import create_draw
from stdd.traceability import associate_node_reference, build_traceability_report, enrich_traceability, refresh_traceability


def _draw_with_traceable_node():
    """Monta um Draw mínimo com nó rastreável.
    Reutiliza o fixture nos contratos de associação e enriquecimento.
    """
    return {
        "version": 1,
        "id": "checkout",
        "title": "Checkout",
        "kind": "feature",
        "groups": [],
        "nodes": [{"id": 7, "label": "Autorizar pagamento", "questions": []}],
        "edges": [],
        "flows": [],
    }


runner = CliRunner()


def test_refresh_traceability_ignores_macos_appledouble_files(tmp_path):
    """Ignora metadados AppleDouble que possuem extensão JSON aparente.
    Evita que arquivos binários ._ gerados pelo macOS derrubem o teste global.
    """
    draws = tmp_path / ".stdd/draws"
    draws.mkdir(parents=True)
    (draws / "index.json").write_text("{}", encoding="utf-8")
    (draws / "._broken.json").write_bytes(b"AppleDouble\x00\xff")

    assert refresh_traceability(tmp_path, {"symbols": [], "dependencies": []}) == []


def test_traceability_maps_node_references_to_symbols_files_and_tests(tmp_path):
    """Mapeia uma referência explícita para código e testes relacionados.
    Fornece fatos determinísticos e verifica o relatório de impacto reproduzível.
    """
    source = tmp_path / "src" / "checkout.py"
    test_source = tmp_path / "tests" / "test_checkout.py"
    source.parent.mkdir()
    test_source.parent.mkdir()
    source.write_text("def authorize():\n    return True\n", encoding="utf-8")
    test_source.write_text("def test_authorize():\n    assert True\n", encoding="utf-8")
    node = {
        "id": 7,
        "label": "Autorizar pagamento",
        "code_refs": [{
            "symbol": "checkout.authorize",
            "identity": "authorize-v1",
            "source_dependencies": ["checkout.repository.save"],
        }],
    }
    facts = {
        "symbols": [{
            "qualified_name": "checkout.authorize",
            "identity": "authorize-v1",
            "file": "src/checkout.py",
        }, {
            "qualified_name": "checkout.repository.save",
            "identity": "save-v1",
            "file": "src/repository.py",
        }],
        "dependencies": [{
            "source": "tests.test_checkout.test_authorize",
            "target": "checkout.authorize",
            "kind": "test",
            "file": "tests/test_checkout.py",
        }],
    }

    report = build_traceability_report(tmp_path, node, facts)

    assert report["node_id"] == 7
    assert report["references"] == [{
        "symbol": "checkout.authorize",
        "identity": "authorize-v1",
        "status": "resolved",
        "file": "src/checkout.py",
    }]
    assert report["files"] == ["src/checkout.py", "src/repository.py", "tests/test_checkout.py"]
    assert report["tests"] == ["tests.test_checkout.test_authorize"]
    assert report["unresolved"] == []
    assert report["source_dependencies"] == ["checkout.repository.save"]


def test_traceability_marks_changed_symbol_as_drift(tmp_path):
    """Detecta quando uma referência deixou de apontar para o mesmo símbolo.
    Compara a identidade estrutural e evita produzir impacto como fato resolvido.
    """
    node = {
        "id": 8,
        "label": "Autorizar pagamento",
        "code_refs": [{"symbol": "checkout.authorize", "identity": "authorize-v1"}],
    }
    facts = {
        "symbols": [{
            "qualified_name": "checkout.authorize",
            "identity": "authorize-v2",
            "file": "src/checkout.py",
        }],
        "dependencies": [],
    }

    report = build_traceability_report(tmp_path, node, facts)

    assert report["references"][0]["status"] == "drift"
    assert report["references"][0]["file"] == "src/checkout.py"
    assert report["unresolved"] == ["checkout.authorize"]
    assert report["files"] == []


def test_traceability_keeps_explicit_reference_and_reports_inference_as_suggestion(tmp_path):
    """Preserva o vínculo explícito e separa inferência auxiliar.
    Oferece sugestão determinística sem substituir a referência declarada no nó.
    """
    node = {
        "id": 9,
        "label": "Pagamento",
        "code_refs": [{"symbol": "checkout.authorize", "identity": "authorize-v1"}],
    }
    facts = {
        "symbols": [{
            "qualified_name": "checkout.authorize",
            "identity": "authorize-v1",
            "file": "src/checkout.py",
        }, {
            "qualified_name": "checkout.capture",
            "identity": "capture-v1",
            "file": "src/checkout.py",
        }],
        "dependencies": [{
            "source": "checkout.authorize",
            "target": "checkout.capture",
            "kind": "calls",
            "file": "src/checkout.py",
        }],
    }

    report = build_traceability_report(tmp_path, node, facts)

    assert [item["symbol"] for item in report["references"]] == ["checkout.authorize"]
    assert report["suggestions"] == [{
        "symbol": "checkout.capture",
        "reason": "dependency",
    }]


def test_associate_node_reference_persists_only_minimal_cli_inputs(tmp_path):
    """Registra node, símbolo qualificado e dependências da CLI.
    Cria o Draw e confirma que a associação declarada fica no nó sem facts derivados.
    """
    create_draw(tmp_path, _draw_with_traceable_node())

    associate_node_reference(
        tmp_path,
        "checkout",
        7,
        "checkout.authorize",
        ["checkout.authorize"],
    )

    saved = json.loads((tmp_path / ".stdd/draws/checkout.json").read_text(encoding="utf-8"))
    assert saved["nodes"][0]["code_refs"] == [{
        "symbol": "checkout.authorize",
        "source_dependencies": ["checkout.authorize"],
    }]
    assert not list((tmp_path / ".stdd/draws").glob("*.facts.json"))


def test_enrich_traceability_recalculates_and_persists_separate_facts_file(tmp_path):
    """Reconstrói todos os facts fora do JSON lógico do desenho.
    Executa o enriquecimento com fatos de análise e verifica o documento separado versionado.
    """
    create_draw(tmp_path, _draw_with_traceable_node())
    associate_node_reference(tmp_path, "checkout", 7, "checkout.authorize", ["checkout.authorize"])
    analysis_facts = {
        "symbols": [{
            "qualified_name": "checkout.authorize",
            "identity": "authorize-v1",
            "file": "src/checkout.py",
        }],
        "dependencies": [],
    }

    facts_path = enrich_traceability(tmp_path, "checkout", analysis_facts)

    assert facts_path == tmp_path / ".stdd/draws/checkout.facts.json"
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    assert facts["version"] == 1
    assert facts["draw_id"] == "checkout"
    assert facts["nodes"]["7"]["references"][0]["status"] == "resolved"


def test_cli_associate_reference_accepts_one_node_contract(tmp_path, monkeypatch):
    """Expõe a associação mínima por comando CLI.
    Executa o comando com node, símbolo qualificado e dependência de origem.
    """
    monkeypatch.chdir(tmp_path)
    create_draw(tmp_path, _draw_with_traceable_node())

    result = runner.invoke(app, [
        "draw", "associate-reference",
        "--draw-id", "checkout",
        "--node-id", "7",
        "--qualified-name", "checkout.authorize",
        "--source-dependency", "checkout.authorize",
    ])

    assert result.exit_code == 0
    saved = json.loads((tmp_path / ".stdd/draws/checkout.json").read_text(encoding="utf-8"))
    assert saved["nodes"][0]["code_refs"][0]["symbol"] == "checkout.authorize"


def test_cli_associate_reference_accepts_batch_contract(tmp_path, monkeypatch):
    """Aceita várias associações em uma execução de lote.
    Envia duas entradas JSON e confirma que ambas ficam nos nós corretos.
    """
    monkeypatch.chdir(tmp_path)
    draw = _draw_with_traceable_node()
    draw["nodes"].append({"id": 8, "label": "Capturar pagamento", "questions": []})
    create_draw(tmp_path, draw)
    batch = json.dumps([
        {"node_id": 7, "qualified_name": "checkout.authorize", "source_dependencies": ["checkout.authorize"]},
        {"node_id": 8, "qualified_name": "checkout.capture", "source_dependencies": ["checkout.capture"]},
    ])

    result = runner.invoke(app, ["draw", "associate-reference", "--draw-id", "checkout", "--batch-json", batch])

    assert result.exit_code == 0
    saved = json.loads((tmp_path / ".stdd/draws/checkout.json").read_text(encoding="utf-8"))
    assert [node["code_refs"][0]["symbol"] for node in saved["nodes"]] == [
        "checkout.authorize",
        "checkout.capture",
    ]
