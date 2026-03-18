import pytest
import json
from pathlib import Path
from claude_forge.sync import export_project, import_project, diff_projects


def test_export_project(tmp_path):
    (tmp_path / ".claude" / "rules").mkdir(parents=True)
    (tmp_path / ".claude" / "rules" / "r1.md").write_text("rule 1")
    (tmp_path / ".claude" / "hooks").mkdir(parents=True)
    (tmp_path / ".claude" / "hooks" / "format.sh").write_text("#!/bin/bash\nexit 0")
    (tmp_path / "memory").mkdir()
    (tmp_path / "memory" / "MEMORY.md").write_text("# Memory")

    result = export_project(tmp_path)
    assert result["source_project"] == tmp_path.name
    assert len(result["rules"]) == 1
    assert len(result["hooks"]) == 1
    assert len(result["memory_files"]) == 1


def test_export_import_roundtrip(tmp_path):
    src = tmp_path / "src_project"
    dst = tmp_path / "dst_project"
    src.mkdir()
    dst.mkdir()

    (src / ".claude" / "rules").mkdir(parents=True)
    (src / ".claude" / "rules" / "r1.md").write_text("rule 1")

    exported = export_project(src)
    export_path = tmp_path / "export.json"
    export_path.write_text(json.dumps(exported), encoding="utf-8")

    stats = import_project(dst, export_path, interactive=False)
    assert stats["rules_imported"] >= 1
    assert (dst / ".claude" / "rules" / "r1.md").exists()


def test_diff_projects(tmp_path):
    p1 = tmp_path / "p1"
    p2 = tmp_path / "p2"
    p1.mkdir()
    p2.mkdir()

    (p1 / ".claude" / "rules").mkdir(parents=True)
    (p1 / ".claude" / "rules" / "r1.md").write_text("rule 1")
    (p2 / ".claude" / "rules").mkdir(parents=True)
    (p2 / ".claude" / "rules" / "r1.md").write_text("rule 1 modified")
    (p2 / ".claude" / "rules" / "r2.md").write_text("rule 2")

    diff = diff_projects(p1, p2)
    assert len(diff["only_in_p2"]) >= 1
    assert len(diff["different"]) >= 1
