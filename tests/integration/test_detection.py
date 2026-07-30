from framework_cli.adapters.registry import detect_project


def test_detect_python_project(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    (tmp_path / "main.py").write_text("print('x')")
    result = detect_project(tmp_path)
    assert "python" in result["adapters"]
    assert "python" in result["applications"]["root"]["languages"]


def test_detect_monorepo_apps(tmp_path):
    (tmp_path / "apps/api").mkdir(parents=True)
    (tmp_path / "apps/api/pyproject.toml").write_text("[project]\nname='api'\n")
    (tmp_path / "apps/web").mkdir(parents=True)
    (tmp_path / "apps/web/package.json").write_text('{"name":"web"}')
    apps = detect_project(tmp_path)["applications"]
    assert {"api", "web"}.issubset(apps)
