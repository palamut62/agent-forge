"""Apply a profile to a project directory."""

import json
from pathlib import Path
from datetime import date
from rich.console import Console
from rich.prompt import Confirm
from .schema import ProfileSchema

console = Console()


def apply_profile(
    profile: ProfileSchema, project_path: Path, interactive: bool = True
) -> None:
    """Profili projeye uygula -- dosya yapisi olustur."""
    project_path = Path(project_path)

    for d in [".claude/hooks", ".claude/rules", ".claude/skills", "memory"]:
        (project_path / d).mkdir(parents=True, exist_ok=True)

    # CLAUDE.md
    claude_md = _render_claude_md(profile, project_path.name)
    _safe_write(project_path / "CLAUDE.md", claude_md, interactive)

    # Hooks
    for hook in profile.hooks:
        hook_content = _render_hook_script(hook.name, hook.command)
        hook_path = project_path / ".claude" / "hooks" / hook.name
        _safe_write(hook_path, hook_content, interactive, newline="\n")
        try:
            hook_path.chmod(0o755)
        except OSError:
            pass

    # settings.json
    settings = _render_settings(profile)
    _safe_write(
        project_path / ".claude" / "settings.json",
        json.dumps(settings, indent=2, ensure_ascii=False),
        interactive,
    )

    # Rules
    for rule in profile.rules:
        _safe_write(
            project_path / ".claude" / "rules" / rule.name, rule.content, interactive
        )

    # Memory
    for mem in profile.memory_templates:
        _safe_write(project_path / "memory" / mem.name, mem.content, interactive)

    # Skill profile
    skill_profile = {
        "generated_by": "claude-forge",
        "generated_at": str(date.today()),
        "profile": profile.name,
        "active_skills": profile.skills_include,
        "excluded_patterns": profile.skills_exclude,
    }
    _safe_write(
        project_path / ".claude" / "skill-profile.json",
        json.dumps(skill_profile, indent=2, ensure_ascii=False),
        interactive,
    )

    console.print(f"\n[green bold]Profil '{profile.name}' uygulandi![/green bold]")


def _render_claude_md(profile: ProfileSchema, project_name: str) -> str:
    sections = [f"# {project_name} -- Claude Guide\n"]

    if profile.claude_md.tech_stack:
        sections.append(f"## Tech Stack\n{profile.claude_md.tech_stack}\n")

    if profile.claude_md.coding_standards:
        sections.append(f"## Coding Standards\n{profile.claude_md.coding_standards}\n")

    sections.append(
        "## Hard Boundaries\n- Never edit .env files\n"
        "- Never commit directly to main/master\n"
        "- Never add features without tests\n"
    )

    if profile.claude_md.test_command:
        sections.append(
            f"## Test Commands\n```bash\n{profile.claude_md.test_command}\n```\n"
        )

    if profile.claude_md.lint_command:
        sections.append(
            f"## Lint Commands\n```bash\n{profile.claude_md.lint_command}\n```\n"
        )

    if profile.skills_include:
        skills_text = "\n".join(f"- {s}" for s in profile.skills_include)
        sections.append(f"## Recommended Skills\n{skills_text}\n")

    sections.append(
        "## Memory System\nRead `memory/MEMORY.md` at the start of every session.\n"
        "Update relevant memory files when discovering important findings.\n"
    )

    for key, value in profile.claude_md.extra_sections.items():
        sections.append(f"## {key}\n{value}\n")

    return "\n".join(sections)


def _render_hook_script(name: str, command: str) -> str:
    return (
        f"#!/bin/bash\n"
        f"# Hook: {name}\n"
        f'FILE_PATH=$(echo "$CLAUDE_TOOL_INPUT" | python3 -c '
        f'"import json,sys; d=json.load(sys.stdin); print(d.get(\'path\',\'\'))" '
        f"2>/dev/null)\n"
        f"{command}\n"
        f"exit 0\n"
    )


def _render_settings(profile: ProfileSchema) -> dict:
    settings: dict = {"hooks": {}}
    for hook in profile.hooks:
        event = hook.event
        if event not in settings["hooks"]:
            settings["hooks"][event] = []
        settings["hooks"][event].append(
            {
                "matcher": hook.matcher,
                "hooks": [
                    {
                        "type": "command",
                        "command": f"bash .claude/hooks/{hook.name}",
                        "timeout": 10,
                    }
                ],
            }
        )
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
