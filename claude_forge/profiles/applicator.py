"""Apply a profile to a project directory."""

import json
import shutil
from pathlib import Path
from datetime import date
from rich.console import Console
from rich.prompt import Confirm
from .schema import ProfileSchema
from ..targets import get_target_platform

console = Console()


def apply_profile(
    profile: ProfileSchema,
    project_path: Path,
    interactive: bool = True,
    target: str = "claude",
    target_home: str | None = None,
) -> None:
    """Profili projeye uygula -- dosya yapisi olustur."""
    project_path = Path(project_path)
    target_platform = get_target_platform(target)
    config_dir = target_platform.config_dir

    for d in [f"{config_dir}/hooks", f"{config_dir}/rules", f"{config_dir}/skills", "memory"]:
        (project_path / d).mkdir(parents=True, exist_ok=True)

    guide_md = _render_guide(profile, project_path.name, target_platform.label)
    _safe_write(project_path / target_platform.guide_file, guide_md, interactive)

    # Hooks
    bundled_hooks_dir = Path(__file__).parent.parent / "hooks"
    for hook in profile.hooks:
        hook_path = project_path / config_dir / "hooks" / hook.name
        if hook.bundled and (bundled_hooks_dir / hook.name).exists():
            # Bundled hook: dosyayi olduğu gibi kopyala
            hook_content = (bundled_hooks_dir / hook.name).read_text(encoding="utf-8")
        else:
            hook_content = _render_hook_script(hook.name, hook.command, hook.event)
        _safe_write(hook_path, hook_content, interactive, newline="\n")
        try:
            hook_path.chmod(0o755)
        except OSError:
            pass

    # settings.json
    settings = _render_settings(profile, target_platform)
    _safe_write(
        project_path / config_dir / target_platform.settings_file,
        json.dumps(settings, indent=2, ensure_ascii=False),
        interactive,
    )

    # Rules
    for rule in profile.rules:
        _safe_write(
            project_path / config_dir / "rules" / rule.name, rule.content, interactive
        )

    # Memory
    for mem in profile.memory_templates:
        _safe_write(project_path / "memory" / mem.name, mem.content, interactive)

    # Skill profile
    skill_profile = {
        "generated_by": "agent-forge",
        "generated_at": str(date.today()),
        "profile": profile.name,
        "active_skills": profile.skills_include,
        "excluded_patterns": profile.skills_exclude,
    }
    _safe_write(
        project_path / config_dir / target_platform.skill_profile_file,
        json.dumps(skill_profile, indent=2, ensure_ascii=False),
        interactive,
    )
    copied = _copy_profile_skills(
        project_path,
        target_platform,
        profile.skills_include,
        target_home=target_home,
    )
    if copied:
        console.print(f"  [green][OK][/green] Copied skills: {', '.join(copied)}")

    console.print(f"\n[green bold]Profil '{profile.name}' uygulandi![/green bold]")


def _render_guide(profile: ProfileSchema, project_name: str, target_label: str) -> str:
    sections = [f"# {project_name}\n"]

    # Compact single-line fields
    meta_parts = []
    if profile.claude_md.role:
        meta_parts.append(profile.claude_md.role.strip())
    if profile.claude_md.tech_stack:
        meta_parts.append(f"**Stack:** {profile.claude_md.tech_stack.strip()}")
    if meta_parts:
        sections.append("\n".join(meta_parts) + "\n")

    if profile.claude_md.architecture:
        sections.append(f"## Architecture\n{profile.claude_md.architecture}")

    if profile.claude_md.coding_standards:
        sections.append(f"## Standards\n{profile.claude_md.coding_standards}")

    if profile.claude_md.hard_boundaries:
        sections.append(f"## NEVER\n{profile.claude_md.hard_boundaries}")
    else:
        sections.append(
            "## NEVER\n"
            "- Edit .env files\n"
            "- Push directly to main/master\n"
            "- Add features without tests\n"
            "- Hardcode secrets\n"
        )

    if profile.claude_md.error_handling:
        sections.append(f"## Error Handling\n{profile.claude_md.error_handling}")

    # Commands on one line each
    cmds = []
    if profile.claude_md.test_command:
        cmds.append(f"**Test:** `{profile.claude_md.test_command.strip()}`")
    if profile.claude_md.lint_command:
        cmds.append(f"**Lint:** `{profile.claude_md.lint_command.strip()}`")
    if cmds:
        sections.append("## Commands\n" + "\n".join(cmds) + "\n")

    sections.append("## Memory\nRead `memory/MEMORY.md` at session start. `memory/brain.jsonl` is auto-maintained.\n"
    )

    for key, value in profile.claude_md.extra_sections.items():
        sections.append(f"## {key}\n{value}\n")

    return "\n".join(sections)


def _render_hook_script(name: str, command: str, event: str = "") -> str:
    lines = ["#!/bin/bash", f"# Hook: {name}"]
    # PreToolUse/PostToolUse hook'lari FILE_PATH'e ihtiyac duyar
    # SessionStart/PreCompact/Stop hook'lari duymaz
    tool_events = {"PreToolUse", "PostToolUse"}
    if event in tool_events:
        lines.append(
            'FILE_PATH=$(echo "$CLAUDE_TOOL_INPUT" | python3 -c '
            '"import json,sys; d=json.load(sys.stdin); print(d.get(\'path\',\'\'))" '
            '2>/dev/null)'
        )
    lines.append(command)
    lines.append("exit 0")
    return "\n".join(lines) + "\n"


def _render_settings(profile: ProfileSchema, target_platform) -> dict:
    settings: dict = {"hooks": {}}
    for hook in profile.hooks:
        event = hook.event
        if event not in settings["hooks"]:
            settings["hooks"][event] = []
        entry: dict = {
            "hooks": [
                {
                    "type": "command",
                    "command": f"bash {target_platform.config_dir}/hooks/{hook.name}",
                    "timeout": 10,
                }
            ],
        }
        if hook.matcher:
            entry["matcher"] = hook.matcher
        settings["hooks"][event].append(entry)
    return settings


def _safe_write(
    path: Path, content: str, interactive: bool, newline: str | None = None
) -> None:
    if path.exists() and interactive:
        if not Confirm.ask(
            f"  [yellow]{path.name} zaten var. Uzerine yaz?[/yellow]", default=False
        ):
            console.print(f"  [dim][>] {path.name} atlandi[/dim]")
            return
    path.parent.mkdir(parents=True, exist_ok=True)
    if newline:
        with open(path, "w", encoding="utf-8", newline=newline) as f:
            f.write(content)
    else:
        path.write_text(content, encoding="utf-8")
    console.print(f"  [green][OK][/green] {path.name}")


def _copy_profile_skills(
    project_path: Path,
    target_platform,
    skill_names: list[str],
    target_home: str | None = None,
) -> list[str]:
    """Copy selected profile skills from target home to project."""
    if not skill_names:
        return []

    source_home = Path(target_home) if target_home else Path.home() / target_platform.default_home_dir
    source_skills = source_home / "skills"
    if not source_skills.exists():
        return []

    dest_skills = project_path / target_platform.config_dir / "skills"
    copied: list[str] = []
    for name in skill_names:
        src = source_skills / name
        if not src.is_dir():
            continue
        dst = dest_skills / name
        shutil.copytree(src, dst, dirs_exist_ok=True)
        copied.append(name)
    return copied
