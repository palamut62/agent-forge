"""Generate Claude Code project structure from AI plan."""

import json
from pathlib import Path
from rich.console import Console
from rich.prompt import Confirm

console = Console()


def generate_project(project_path: str, plan: dict) -> None:
    """Generate project structure from AI plan."""
    path = Path(project_path)
    project_name = path.name

    # Fallback: use defaults if AI returned empty fields
    if not plan.get("claude_md"):
        plan["claude_md"] = _default_claude_md(project_name, plan)
        console.print("  [yellow][!] CLAUDE.md not returned by AI, using defaults[/yellow]")

    if not plan.get("settings_json"):
        plan["settings_json"] = _default_settings_json(plan)
        console.print("  [yellow][!] settings.json not returned by AI, using defaults[/yellow]")

    if not plan.get("hooks"):
        plan["hooks"] = _default_hooks()
        console.print("  [yellow][!] Hooks not returned by AI, using defaults[/yellow]")

    # Create directories
    dirs = [
        ".claude/hooks",
        ".claude/rules",
        ".claude/skills",
        "memory",
    ]
    for d in dirs:
        (path / d).mkdir(parents=True, exist_ok=True)
        console.print(f"  [dim][D] {d}/[/dim]")

    # CLAUDE.md
    claude_md = plan.get("claude_md", "")
    if claude_md:
        _write_file(path / "CLAUDE.md", claude_md)

    # settings.json
    settings = plan.get("settings_json")
    if settings:
        _write_file(
            path / ".claude" / "settings.json",
            json.dumps(settings, indent=2, ensure_ascii=False),
        )

    # Hooks
    for hook in plan.get("hooks", []):
        hook_path = path / ".claude" / "hooks" / hook["name"]
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
            path / ".claude" / "rules" / rule["name"],
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

    # Update .gitignore
    _update_gitignore(path)

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
    console.print(f"  [green][OK][/green] {file_path.relative_to(file_path.parent.parent.parent) if len(file_path.parts) > 3 else file_path.name}")


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


def _default_claude_md(project_name: str, plan: dict) -> str:
    ptype = plan.get("project_type", "general")
    summary = plan.get("project_summary", "")
    skills = plan.get("recommended_skills", [])
    skills_text = "\n".join(f"- {s['source']}:{s['name']}" for s in skills) if skills else "- (not yet determined)"

    return f"""# {project_name} -- Claude Guide

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


def _default_settings_json(plan: dict) -> dict:
    hooks_config = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Edit|Write",
                    "hooks": [{"type": "command", "command": "bash .claude/hooks/protect-env.sh", "timeout": 5}]
                }
            ],
        }
    }
    hook_names = [h.get("name", "") for h in plan.get("hooks", [])]
    if any("format" in n for n in hook_names):
        hooks_config["hooks"]["PostToolUse"] = [
            {
                "matcher": "Edit|Write",
                "hooks": [{"type": "command", "command": "bash .claude/hooks/format.sh", "timeout": 10}]
            }
        ]
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


def _update_gitignore(project_path: Path) -> None:
    """Add necessary entries to .gitignore."""
    gitignore = project_path / ".gitignore"
    entries_to_add = [
        "# Claude Code",
        ".claude/settings.local.json",
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
