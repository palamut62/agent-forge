import pytest
from pathlib import Path
from claude_forge.mapper import generate_codemap, find_entry_points, analyze_python_imports


def test_generate_codemap(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "__init__.py").write_text("")
    (tmp_path / "src" / "main.py").write_text("from src.utils import helper\n\ndef main():\n    pass\n")
    (tmp_path / "src" / "utils.py").write_text("def helper():\n    pass\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_main.py").write_text("")

    codemap = generate_codemap(tmp_path)
    assert "src" in codemap
    assert "3 files" in codemap


def test_find_entry_points(tmp_path):
    (tmp_path / "main.py").write_text("if __name__")
    (tmp_path / "app.py").write_text("")
    entries = find_entry_points(tmp_path)
    assert "main.py" in entries


def test_analyze_python_imports(tmp_path):
    code = "from src.auth import login\nimport src.models\nfrom pathlib import Path\n"
    (tmp_path / "test.py").write_text(code)
    imports = analyze_python_imports(tmp_path / "test.py")
    assert "src.auth" in imports
    assert "src.models" in imports
    assert "pathlib" not in imports


def test_codemap_max_files(tmp_path):
    for i in range(10):
        d = tmp_path / f"pkg{i}"
        d.mkdir()
        for j in range(5):
            (d / f"f{j}.py").write_text("")
    codemap = generate_codemap(tmp_path)
    assert isinstance(codemap, str)
