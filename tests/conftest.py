import pytest
from pathlib import Path


@pytest.fixture
def sample_project(tmp_path):
    """Basit bir test projesi olustur."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "__init__.py").write_text("")
    (tmp_path / "src" / "main.py").write_text(
        "from fastapi import FastAPI\napp = FastAPI()\n"
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "test"\nversion = "0.1.0"\n'
    )
    (tmp_path / "tests").mkdir()
    return tmp_path


@pytest.fixture
def sample_project_with_claude(sample_project):
    """Claude Code setup'li test projesi."""
    (sample_project / ".claude" / "hooks").mkdir(parents=True)
    (sample_project / ".claude" / "rules").mkdir(parents=True)
    (sample_project / "memory").mkdir()
    (sample_project / "CLAUDE.md").write_text("# Test Project\n")
    (sample_project / "memory" / "MEMORY.md").write_text("# Memory\n")
    return sample_project
