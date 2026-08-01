from pathlib import Path


EDITOR_ROOT = Path("draw-editor")


def test_empty_draw_editor_exposes_block_creation_action():
    """Mantém a ação de criar blocos disponível em desenhos vazios.
    Confirma que a aba inicial oferece o formulário de adição de blocos.
    """
    sidebar = (EDITOR_ROOT / "src/components/Sidebar.tsx").read_text(encoding="utf-8")

    assert "Adicionar Bloco" in sidebar
    assert "if (isEmptyDrawing) setActiveTab('info')" in sidebar


def test_draw_editor_removes_floating_canvas_hint():
    """Remove a dica flutuante do canto inferior esquerdo do viewer.
    Confirma que JSX e CSS não mantêm o componente de dica antigo.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    styles = (EDITOR_ROOT / "src/index.css").read_text(encoding="utf-8")

    assert "canvas-hint" not in app
    assert "canvas-hint" not in styles
