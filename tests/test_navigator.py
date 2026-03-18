import pytest
from claude_forge.navigator import build_registry, match_skills


def test_build_registry():
    registry = build_registry()
    assert isinstance(registry, dict)
    assert len(registry) > 0


def test_registry_entry_structure():
    registry = build_registry()
    for name, entry in registry.items():
        assert "description" in entry
        assert "tags" in entry
        assert isinstance(entry["tags"], list)


def test_match_skills_python():
    registry = build_registry()
    result = match_skills(registry, languages=["python"], frameworks=["fastapi"])
    assert "recommended" in result
    assert "optional" in result
    assert "irrelevant" in result
    assert len(result["recommended"]) >= 1


def test_match_skills_empty():
    result = match_skills({}, languages=["python"], frameworks=[])
    assert result["recommended"] == []
