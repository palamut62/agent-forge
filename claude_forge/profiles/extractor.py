"""Extract a profile from an existing project's .claude/ structure."""

import json
import yaml
from pathlib import Path
from .schema import ProfileSchema, HookEntry, RuleEntry, MemoryTemplate


def extract_profile(project_path: Path, name: str) -> ProfileSchema:
    """Mevcut projedeki .claude/ yapisindan profil cikar."""
    project_path = Path(project_path)
    hooks = _extract_hooks(project_path)
    rules = _extract_rules(project_path)
    memory = _extract_memory(project_path)
    skills_include, skills_exclude = _extract_skill_profile(project_path)

    return ProfileSchema(
        name=name,
        description=f"Extracted from {project_path.name}",
        hooks=hooks,
        rules=rules,
        memory_templates=memory,
        skills_include=skills_include,
        skills_exclude=skills_exclude,
    )


def save_profile_yaml(profile: ProfileSchema, output_path: Path) -> None:
    """Profili YAML olarak kaydet."""
    data = profile.model_dump(exclude_defaults=True)
    data["version"] = 1
    output_path.write_text(
        yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def _extract_hooks(project_path: Path) -> list[HookEntry]:
    hooks_dir = project_path / ".claude" / "hooks"
    settings_path = project_path / ".claude" / "settings.json"
    hooks = []

    if not hooks_dir.exists():
        return hooks

    event_map: dict[str, tuple[str, str]] = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            for event, entries in settings.get("hooks", {}).items():
                for entry in entries:
                    for h in entry.get("hooks", []):
                        cmd = h.get("command", "")
                        for hook_file in hooks_dir.iterdir():
                            if hook_file.name in cmd:
                                event_map[hook_file.name] = (
                                    event,
                                    entry.get("matcher", ""),
                                )
        except (json.JSONDecodeError, KeyError):
            pass

    for hook_file in sorted(hooks_dir.iterdir()):
        if hook_file.is_file():
            event, matcher = event_map.get(
                hook_file.name, ("PostToolUse", "Edit|Write")
            )
            hooks.append(
                HookEntry(
                    name=hook_file.name,
                    event=event,
                    matcher=matcher,
                    command=hook_file.read_text(encoding="utf-8", errors="ignore"),
                )
            )

    return hooks


def _extract_rules(project_path: Path) -> list[RuleEntry]:
    rules_dir = project_path / ".claude" / "rules"
    if not rules_dir.exists():
        return []
    return [
        RuleEntry(
            name=f.name, content=f.read_text(encoding="utf-8", errors="ignore")
        )
        for f in sorted(rules_dir.iterdir())
        if f.is_file()
    ]


def _extract_memory(project_path: Path) -> list[MemoryTemplate]:
    memory_dir = project_path / "memory"
    if not memory_dir.exists():
        return []
    return [
        MemoryTemplate(
            name=f.name, content=f.read_text(encoding="utf-8", errors="ignore")
        )
        for f in sorted(memory_dir.iterdir())
        if f.is_file()
    ]


def _extract_skill_profile(
    project_path: Path,
) -> tuple[list[str], list[str]]:
    sp_path = project_path / ".claude" / "skill-profile.json"
    if not sp_path.exists():
        return [], []
    try:
        data = json.loads(sp_path.read_text(encoding="utf-8"))
        return data.get("active_skills", []), data.get("excluded_patterns", [])
    except (json.JSONDecodeError, KeyError):
        return [], []
