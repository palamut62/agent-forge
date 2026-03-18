import pytest
import yaml
from claude_forge.profiles.schema import ProfileSchema, HookEntry, RuleEntry, MemoryTemplate
from claude_forge.profiles.loader import load_profile, list_profiles
from claude_forge.profiles.applicator import apply_profile
from claude_forge.profiles.extractor import extract_profile


def test_valid_profile():
    data = {
        "version": 1,
        "name": "test",
        "description": "Test profile",
        "languages": ["python"],
        "frameworks": ["fastapi"],
        "claude_md": {
            "tech_stack": "Python 3.12",
            "coding_standards": "- Type hints",
            "test_command": "pytest",
            "lint_command": "ruff check",
        },
        "hooks": [
            {
                "name": "format.sh",
                "event": "PostToolUse",
                "matcher": "Edit",
                "command": "ruff format",
            }
        ],
        "rules": [{"name": "async-io.md", "content": "Use async"}],
        "skills_include": ["tdd-workflow"],
        "skills_exclude": ["threejs-*"],
        "memory_templates": [{"name": "arch.md", "content": "# Arch"}],
    }
    profile = ProfileSchema(**data)
    assert profile.name == "test"
    assert profile.version == 1


def test_minimal_profile():
    profile = ProfileSchema(name="min", description="Minimal")
    assert profile.languages == []
    assert profile.hooks == []


def test_invalid_profile_no_name():
    with pytest.raises(Exception):
        ProfileSchema(description="No name")


def test_invalid_profile_bad_version():
    with pytest.raises(Exception):
        ProfileSchema(name="x", description="x", version=99)


def test_load_builtin_profile():
    profile = load_profile("base")
    assert profile.name == "base"


def test_list_builtin_profiles():
    profiles = list_profiles()
    assert "base" in profiles
    assert "fastapi" in profiles


def test_extends_merging(tmp_path):
    base = {
        "version": 1,
        "name": "parent",
        "description": "Parent",
        "rules": [{"name": "r1.md", "content": "rule 1"}],
    }
    child = {
        "version": 1,
        "name": "child",
        "description": "Child",
        "extends": "parent",
        "rules": [{"name": "r2.md", "content": "rule 2"}],
    }
    (tmp_path / "parent.yaml").write_text(yaml.dump(base))
    (tmp_path / "child.yaml").write_text(yaml.dump(child))

    profile = load_profile("child", extra_dirs=[tmp_path])
    assert len(profile.rules) == 2


def test_load_nonexistent_profile():
    with pytest.raises(FileNotFoundError):
        load_profile("nonexistent_xyz_123")


@pytest.mark.parametrize(
    "name",
    ["base", "fastapi", "react", "telegram_bot", "cli_tool", "data_pipeline", "fullstack"],
)
def test_all_builtin_profiles_load(name):
    profile = load_profile(name)
    assert profile.name == name
    assert profile.description


def test_apply_profile_creates_structure(tmp_path):
    profile = load_profile("fastapi")
    apply_profile(profile, tmp_path, interactive=False)

    assert (tmp_path / "CLAUDE.md").exists()
    assert (tmp_path / ".claude" / "settings.json").exists()
    assert (tmp_path / ".claude" / "hooks" / "protect-env.sh").exists()
    assert (tmp_path / ".claude" / "rules" / "async-io.md").exists()
    assert (tmp_path / "memory" / "MEMORY.md").exists()

    claude_md = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert "FastAPI" in claude_md
    assert "tdd-workflow" in claude_md


def test_apply_profile_writes_skill_profile(tmp_path):
    import json

    profile = load_profile("fastapi")
    apply_profile(profile, tmp_path, interactive=False)

    sp = json.loads(
        (tmp_path / ".claude" / "skill-profile.json").read_text(encoding="utf-8")
    )
    assert "tdd-workflow" in sp["active_skills"]
    assert "threejs-*" in sp["excluded_patterns"]


def test_extract_profile_from_project(tmp_path):
    profile = load_profile("fastapi")
    apply_profile(profile, tmp_path, interactive=False)

    extracted = extract_profile(tmp_path, name="my-fastapi")
    assert extracted.name == "my-fastapi"
    assert len(extracted.rules) >= 1
    assert len(extracted.hooks) >= 1


def test_extract_empty_project(tmp_path):
    extracted = extract_profile(tmp_path, name="empty")
    assert extracted.name == "empty"
    assert extracted.rules == []
