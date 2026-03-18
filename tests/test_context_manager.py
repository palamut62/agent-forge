import pytest
from pathlib import Path
from claude_forge.context_manager import context_status, context_compact_preview


def test_context_status_empty(tmp_path):
    status = context_status(tmp_path)
    assert status["memory_files"] == 0
    assert status["has_codemap"] is False


def test_context_status_with_memory(tmp_path):
    mem_dir = tmp_path / "memory"
    mem_dir.mkdir()
    (mem_dir / "MEMORY.md").write_text("# Memory")
    (mem_dir / "debug.md").write_text("# Debug\nsome content")

    status = context_status(tmp_path)
    assert status["memory_files"] == 2
    assert status["total_lines"] > 0


def test_context_compact_preview(tmp_path):
    mem_dir = tmp_path / "memory"
    mem_dir.mkdir()
    (mem_dir / "old.md").write_text("# Old\nstale content")

    preview = context_compact_preview(tmp_path)
    assert isinstance(preview, list)
