"""Generate Claude Code project structure from AI plan."""

import json
from pathlib import Path
from rich.console import Console
from rich.prompt import Confirm
from .targets import get_target_platform

console = Console()


def generate_project(
    project_path: str,
    plan: dict,
    target: str = "claude",
    target_home: str | None = None,
) -> None:
    """Generate project structure from AI plan."""
    path = Path(project_path)
    project_name = path.name
    target_platform = get_target_platform(plan.get("target", target))
    config_dir = target_platform.config_dir

    # Fallback: use defaults if AI returned empty fields
    if not plan.get("guide_content") and plan.get("claude_md"):
        plan["guide_content"] = plan["claude_md"]

    if not plan.get("guide_content"):
        plan["guide_content"] = _default_guide(project_name, plan, target_platform.label)
        console.print(f"  [yellow][!] {target_platform.guide_file} not returned by AI, using defaults[/yellow]")

    if not plan.get("settings_json"):
        plan["settings_json"] = _default_settings_json(plan, target_platform)
        console.print("  [yellow][!] settings.json not returned by AI, using defaults[/yellow]")

    if not plan.get("hooks"):
        plan["hooks"] = _default_hooks()
        console.print("  [yellow][!] Hooks not returned by AI, using defaults[/yellow]")

    # Create directories
    dirs = [
        f"{config_dir}/hooks",
        f"{config_dir}/rules",
        f"{config_dir}/skills",
        "memory",
    ]
    for d in dirs:
        (path / d).mkdir(parents=True, exist_ok=True)
        console.print(f"  [dim][D] {d}/[/dim]")

    guide_content = plan.get("guide_content", "")
    if guide_content:
        _write_file(path / target_platform.guide_file, guide_content)

    # settings.json
    settings = plan.get("settings_json")
    if settings:
        _write_file(
            path / config_dir / target_platform.settings_file,
            json.dumps(settings, indent=2, ensure_ascii=False),
        )

    # Hooks
    for hook in plan.get("hooks", []):
        hook_path = path / config_dir / "hooks" / hook["name"]
        # Sanitize hook content for Windows bash compatibility
        hook_content = _sanitize_hook(hook["content"])
        _write_file(hook_path, hook_content, newline="\n")  # Force LF
        try:
            hook_path.chmod(0o755)
        except Exception:
            pass

    # Rules
    for rule in plan.get("rules", []):
        _write_file(
            path / config_dir / "rules" / rule["name"],
            rule["content"],
        )

    # Memory files
    memory_files = plan.get("memory_files", [])
    if not memory_files:
        memory_files = [
            {"name": "MEMORY.md", "content": _default_memory_index()},
            {"name": "debugging.md", "content": "# Debugging Log\n\n_(No entries yet)_\n"},
            {"name": "patterns.md", "content": "# Codebase Patterns\n\n_(No entries yet)_\n"},
            {"name": "preferences.md", "content": "# Working Preferences\n\n_(No entries yet)_\n"},
        ]
    for mf in memory_files:
        _write_file(path / "memory" / mf["name"], mf["content"])

    copied_skills = _copy_recommended_skills(path, plan, target_platform, target_home)
    if copied_skills:
        console.print(f"  [green][OK][/green] Copied skills: {', '.join(copied_skills)}")

    # MCP servers
    from .mcp import write_mcp_config
    extra_mcp = plan.get("mcp_servers", {})
    mcp_path = write_mcp_config(target_platform, path, extra_mcp or None)
    if mcp_path:
        console.print(f"  [green][OK][/green] MCP config: {mcp_path.name}")

    # Update .gitignore
    _update_gitignore(path, target_platform)

    console.print("\n[green bold]Setup complete![/green bold]")
    console.print(f"[dim]Directory: {path.absolute()}[/dim]")


def _sanitize_hook(content: str) -> str:
    """Sanitize hook script for Windows bash compatibility."""
    # Replace smart quotes with regular quotes
    content = content.replace("\u2018", "'").replace("\u2019", "'")
    content = content.replace("\u201c", '"').replace("\u201d", '"')
    # Replace CRLF with LF
    content = content.replace("\r\n", "\n")
    # Ensure shebang
    if not content.startswith("#!"):
        content = "#!/bin/bash\n" + content
    # Ensure trailing newline
    if not content.endswith("\n"):
        content += "\n"
    # Add 2>/dev/null to git commands that might fail
    lines = []
    for line in content.splitlines():
        # Make git commands fail silently when no repo
        if "git " in line and "2>/dev/null" not in line and "echo" not in line:
            line = line.rstrip()
            if not line.endswith("\\"):
                line += " 2>/dev/null"
        lines.append(line)
    return "\n".join(lines) + "\n"


def _write_file(file_path: Path, content: str, newline: str | None = None) -> None:
    """Write file, ask if exists."""
    if file_path.exists():
        if not Confirm.ask(f"  [yellow]{file_path.name} already exists. Overwrite?[/yellow]", default=False):
            console.print(f"  [dim][>] {file_path.name} skipped[/dim]")
            return

    file_path.parent.mkdir(parents=True, exist_ok=True)
    if newline:
        with open(file_path, "w", encoding="utf-8", newline=newline) as f:
            f.write(content)
    else:
        file_path.write_text(content, encoding="utf-8")
    console.print(f"  [green][OK][/green] {file_path.as_posix()}")


def _default_memory_index() -> str:
    return """# Project Memory -- Routing

Last updated: -

## Critical Notes
- _(none yet)_

## Detailed Info
- Bug fixes and solutions: `memory/debugging.md`
- Codebase patterns: `memory/patterns.md`
- Working preferences: `memory/preferences.md`
"""


def _default_guide(project_name: str, plan: dict, target_label: str) -> str:
    ptype = plan.get("project_type", "general")
    summary = plan.get("project_summary", "")
    skills = plan.get("recommended_skills", [])
    skills_text = "\n".join(f"- {s['source']}:{s['name']}" for s in skills) if skills else "- (not yet determined)"

    return f"""# {project_name} -- {target_label} Guide

## Your Role
You are a senior developer on this project. Write comments in English, write code in English.

## Project Summary
{summary}

## Tech Stack
- Type: {ptype}
- (Add project-specific details here)

## Coding Standards
- Use type hints / TypeScript strict mode
- No `any` type allowed
- No console.log/print left behind, use logger
- Functions max 30 lines

## Hard Boundaries (Never Do)
- Never edit .env files, only read them
- Never commit directly to main/master branch
- Never add features without writing tests

## Recommended Skills
{skills_text}

## Memory System
Read `memory/MEMORY.md` at the start of every session.
Update relevant memory files when discovering important findings, bugs, or decisions.

## Test Commands
- (Add project-specific commands here)
"""


def _default_settings_json(plan: dict, target_platform) -> dict:
    cd = target_platform.config_dir
    hooks_config: dict = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Edit|Write",
                    "hooks": [{"type": "command", "command": f"bash {cd}/hooks/protect-env.sh", "timeout": 5}],
                }
            ],
            "PostToolUse": [
                {
                    "hooks": [{"type": "command", "command": f"bash {cd}/hooks/brain-sync.sh", "timeout": 10}],
                }
            ],
            "SessionStart": [
                {
                    "hooks": [{"type": "command", "command": f"bash {cd}/hooks/session-start.sh", "timeout": 15}],
                }
            ],
            "PreCompact": [
                {
                    "hooks": [{"type": "command", "command": f"bash {cd}/hooks/pre-compact.sh", "timeout": 10}],
                }
            ],
            "Stop": [
                {
                    "hooks": [{"type": "command", "command": f"bash {cd}/hooks/qa-gate.sh", "timeout": 30}],
                }
            ],
        }
    }
    hook_names = [h.get("name", "") for h in plan.get("hooks", [])]
    if any("format" in n for n in hook_names):
        hooks_config["hooks"]["PostToolUse"].insert(0, {
            "matcher": "Edit|Write",
            "hooks": [{"type": "command", "command": f"bash {cd}/hooks/format.sh", "timeout": 10}],
        })
    return hooks_config


def _default_hooks() -> list:
    return [
        {
            "name": "protect-env.sh",
            "description": "Prevent writing to .env files",
            "content": '#!/bin/bash\nFILE_PATH=$(echo "$CLAUDE_TOOL_INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get(\'path\',\'\'))" 2>/dev/null)\nif [[ "$FILE_PATH" == *".env" ]] && [[ "$FILE_PATH" != *".env.example" ]]; then\n  echo \'{"block": true, "message": "BLOCKED: Writing to .env files is not allowed."}\' >&2\n  exit 2\nfi\nexit 0\n',
        },
        {
            "name": "dangerous-check.sh",
            "description": "Block dangerous commands",
            "content": '#!/bin/bash\nCOMMAND=$(echo "$CLAUDE_TOOL_INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get(\'command\',\'\'))" 2>/dev/null)\nif echo "$COMMAND" | grep -qE "rm\\s+-rf\\s+/|rm\\s+-rf\\s+~"; then\n  echo \'{"block": true, "message": "BLOCKED: Root directory deletion not allowed."}\' >&2\n  exit 2\nfi\nif echo "$COMMAND" | grep -qE "git\\s+push\\s+--force\\s+origin\\s+main"; then\n  echo \'{"block": true, "message": "BLOCKED: Force push to main branch not allowed."}\' >&2\n  exit 2\nfi\nexit 0\n',
        },
    ]


def _copy_recommended_skills(
    project_path: Path,
    plan: dict,
    target_platform,
    target_home: str | None,
) -> list[str]:
    """Copy recommended skills from ECC cache into project."""
    from .skill_fetcher import copy_skills_to_project

    raw = plan.get("recommended_skills", [])
    names: list[str] = []
    for entry in raw:
        if isinstance(entry, dict):
            name = str(entry.get("name", "")).strip()
        else:
            name = str(entry).strip()
        if name:
            # Normalize plugin:name and org/name formats
            clean = name.split(":")[-1].split("/")[-1].strip()
            if clean and clean not in names:
                names.append(clean)

    return copy_skills_to_project(
        project_path,
        target_platform.config_dir,
        names,
    )


def _update_gitignore(project_path: Path, target_platform) -> None:
    """Add necessary entries to .gitignore."""
    gitignore = project_path / ".gitignore"
    entries_to_add = [
        f"# {target_platform.label}",
        f"{target_platform.config_dir}/{target_platform.local_settings_file}",
    ]

    existing = ""
    if gitignore.exists():
        existing = gitignore.read_text(encoding="utf-8", errors="ignore")

    lines_to_write = []
    for entry in entries_to_add:
        if entry not in existing:
            lines_to_write.append(entry)

    if lines_to_write:
        with open(gitignore, "a", encoding="utf-8") as f:
            f.write("\n" + "\n".join(lines_to_write) + "\n")
        console.print("  [green][OK][/green] .gitignore updated")
