"""AI-powered project analysis via OpenRouter."""

import json
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

console = Console()

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = """\
You are a Claude Code project setup expert. You will receive a project's file structure,
languages/frameworks used, and the user's existing Claude Code skill/plugin inventory.

Your tasks:
1. Analyze the project type and needs
2. Select relevant skills/plugins from the user's inventory
3. Create a detailed, project-specific CLAUDE.md (AT LEAST 30 lines)
4. Define necessary hooks, rules, and memory structure
5. Create settings.json that wires up the hooks

CRITICAL RULES:
- "claude_md" field is REQUIRED and must be detailed. Must include tech stack, coding standards, architecture, boundaries, and test commands.
- "settings_json" field is REQUIRED. Must wire hooks into .claude/settings.json.
- "memory_files" field is REQUIRED. Must include at least MEMORY.md, debugging.md, preferences.md.
- "hooks" must have at least 2: format + protect-env
- "rules" must have at least 2
- ALL fields must be filled, NO EMPTY FIELDS.
- ALL content must be in ENGLISH. Do NOT use any other language.

Respond with ONLY valid JSON. No explanations, no comments, no markdown code blocks.
"""

USER_PROMPT_TEMPLATE = """\
## Project Info
- Directory: {project_name}
- Languages: {languages}
- Frameworks: {frameworks}
- File count: {file_count}
- Has Git: {has_git}
- Existing Claude setup: {has_claude}

## File Tree (first 50)
{file_tree}

## Available Skill/Plugin Inventory

### Global Skills
{global_skills}

### Plugin Commands
{plugin_commands}

### Plugin Agents
{plugin_agents}

---

Respond in this JSON format (ALL FIELDS REQUIRED, DO NOT LEAVE EMPTY):
{{
  "project_type": "fastapi|react|fullstack|bot|threejs|general",
  "project_summary": "short project description",
  "recommended_skills": [
    {{"name": "skill-name", "source": "superpowers|everything-claude-code|global|plugin", "reason": "why needed"}}
  ],
  "claude_md": "# Project Name -- Claude Guide\\n\\n## Your Role\\nYou are a senior developer on this project.\\n\\n## Tech Stack\\n- ...\\n\\n## Coding Standards\\n- ...\\n\\n## Hard Boundaries (Never Do)\\n- Never edit .env files\\n- Never commit directly to main branch\\n\\n## Test Commands\\n- ...",
  "hooks": [
    {{"name": "format.sh", "description": "Auto-format code on save", "content": "#!/bin/bash\\nFILE_PATH=$(echo \\"$CLAUDE_TOOL_INPUT\\" | python3 -c \\"import json,sys; d=json.load(sys.stdin); print(d.get('path',''))\\" 2>/dev/null)\\n# format commands based on project type\\nexit 0"}},
    {{"name": "protect-env.sh", "description": "Prevent writing to .env files", "content": "#!/bin/bash\\nFILE_PATH=$(echo \\"$CLAUDE_TOOL_INPUT\\" | python3 -c \\"import json,sys; d=json.load(sys.stdin); print(d.get('path',''))\\" 2>/dev/null)\\nif [[ \\"$FILE_PATH\\" == *\\".env\\" ]] && [[ \\"$FILE_PATH\\" != *\\".env.example\\" ]]; then\\n  echo '{{\\\"block\\\": true, \\\"message\\\": \\\"BLOCKED: Writing to .env files is not allowed.\\\"}}' >&2\\n  exit 2\\nfi\\nexit 0"}}
  ],
  "rules": [
    {{"name": "code-quality.md", "content": "---\\ndescription: Apply when writing code\\n---\\n# Code Quality Rules\\n- ..."}},
    {{"name": "git-workflow.md", "content": "---\\ndescription: Apply during git operations\\n---\\n# Git Rules\\n- ..."}}
  ],
  "memory_files": [
    {{"name": "MEMORY.md", "content": "# Project Memory -- Routing\\n\\nLast updated: -\\n\\n## Critical Notes\\n- (none yet)\\n\\n## Detailed Info\\n- memory/debugging.md\\n- memory/preferences.md"}},
    {{"name": "debugging.md", "content": "# Debugging Log\\n\\n_(No entries yet)_"}},
    {{"name": "preferences.md", "content": "# Working Preferences\\n\\n_(No entries yet)_"}}
  ],
  "settings_json": {{
    "hooks": {{
      "PreToolUse": [
        {{"matcher": "Edit|Write", "hooks": [{{"type": "command", "command": "bash .claude/hooks/protect-env.sh", "timeout": 5}}]}}
      ],
      "PostToolUse": [
        {{"matcher": "Edit|Write", "hooks": [{{"type": "command", "command": "bash .claude/hooks/format.sh", "timeout": 10}}]}}
      ]
    }}
  }},
  "warnings": ["any warnings"]
}}
"""


def analyze_project(
    project_info: dict,
    skills_info: dict,
    model: str,
    api_key: str,
) -> dict | None:
    """Analyze project with AI and create setup plan."""

    global_skills_text = "\n".join(
        f"- {s['name']}: {s['description']}" for s in skills_info["global_skills"]
    ) or "- (none)"

    plugin_commands_text = "\n".join(
        f"- {s['plugin']}/{s['name']}: {s['description']}"
        for s in skills_info["plugin_commands"][:50]
    ) or "- (none)"

    plugin_agents_text = "\n".join(
        f"- {s['plugin']}/{s['name']}: {s['description']}"
        for s in skills_info["plugin_agents"][:50]
    ) or "- (none)"

    file_tree_text = "\n".join(project_info["file_tree"][:50])

    user_prompt = USER_PROMPT_TEMPLATE.format(
        project_name=project_info["name"],
        languages=", ".join(project_info["languages"]) or "unknown",
        frameworks=", ".join(project_info["frameworks"]) or "unknown",
        file_count=project_info["file_count"],
        has_git=project_info["has_git"],
        has_claude=project_info["has_claude"],
        file_tree=file_tree_text or "(empty directory)",
        global_skills=global_skills_text,
        plugin_commands=plugin_commands_text,
        plugin_agents=plugin_agents_text,
    )

    console.print("[dim]AI analyzing...[/dim]")

    try:
        with httpx.Client(timeout=60) as client:
            resp = client.post(
                OPENROUTER_CHAT_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 8192,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]

            # JSON parse -- sometimes wrapped in markdown code block
            content = content.strip()
            if content.startswith("```"):
                lines = content.splitlines()
                start = 1 if lines[0].startswith("```") else 0
                end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
                content = "\n".join(lines[start:end])

            return json.loads(content)

    except httpx.HTTPStatusError as e:
        console.print(f"[red]API error: {e.response.status_code} -- {e.response.text[:200]}[/red]")
        return None
    except json.JSONDecodeError as e:
        console.print(f"[red]JSON parse error: {e}[/red]")
        console.print(f"[dim]Raw response: {content[:500]}[/dim]")
        return None
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return None


def display_plan(plan: dict) -> None:
    """Display the AI-generated plan."""
    console.print()
    console.print(Panel(
        f"[bold]{plan.get('project_type', '?').upper()}[/bold] -- {plan.get('project_summary', '')}",
        title="Project Analysis",
        border_style="cyan",
    ))

    skills = plan.get("recommended_skills", [])
    if skills:
        console.print("\n[bold]Recommended Skills:[/bold]")
        for s in skills:
            console.print(f"  [green][OK][/green] {s['source']}:{s['name']} -- [dim]{s['reason']}[/dim]")

    hooks = plan.get("hooks", [])
    if hooks:
        console.print(f"\n[bold]Hooks:[/bold] ({len(hooks)})")
        for h in hooks:
            console.print(f"  [yellow][!][/yellow] {h['name']} -- {h['description']}")

    rules = plan.get("rules", [])
    if rules:
        console.print(f"\n[bold]Rules:[/bold] ({len(rules)})")
        for r in rules:
            console.print(f"  [blue][R][/blue] {r['name']}")

    warnings = plan.get("warnings", [])
    if warnings:
        console.print("\n[bold red]Warnings:[/bold red]")
        for w in warnings:
            console.print(f"  [red][!][/red]  {w}")

    console.print()
