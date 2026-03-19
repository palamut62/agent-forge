"""AI-powered project analysis via OpenRouter."""

import json
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

console = Console()

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = """\
You configure AI coding assistant workspaces. Generate a TOKEN-EFFICIENT setup.

CRITICAL: Every token in the output will be read by an AI assistant on EVERY session.
Eliminate redundancy ruthlessly. No filler, no verbose explanations, no repeated information.

## guide_content structure (40-60 lines, dense):
1. Role (1 line): what the AI acts as
2. Stack (1 line): bold, comma-separated
3. Architecture (ASCII tree, compact)
4. Standards (bullet list, actionable, no explanations — just rules)
5. NEVER (bullet list of hard prohibitions)
6. Error Handling (2-3 lines max)
7. Commands: **Test:** `cmd` / **Lint:** `cmd`
8. Memory: "Read memory/MEMORY.md at session start."

DO NOT include in guide_content:
- Code examples (put those in rules instead)
- Recommended skills list (already in skill-profile.json)
- Explanations of WHY a rule exists
- Placeholder text or "update this later" notes

## rules: 3-5 rules, each CONCISE (max 10 lines)
- Frontmatter: `description:` only
- Body: bullet points, no prose. Include 1 short code example only if critical.
- Do NOT repeat anything already in guide_content.

## memory_files: minimal headers only
- MEMORY.md: 3 lines max (## Decisions, ## Issues)
- No placeholder text like "_(none yet)_"

## Output rules:
- ALL content in ENGLISH
- NO empty fields, NO redundancy between guide/rules/memory
- Respond with ONLY valid JSON. No markdown, no explanation.
"""

USER_PROMPT_TEMPLATE = """\
## Project Info
- Directory: {project_name}
- Target platform: {target_label}
- Guide file: {guide_file}
- Config directory: {config_dir}
- Languages: {languages}
- Frameworks: {frameworks}
- File count: {file_count}
- Has Git: {has_git}
- Existing target setup: {has_target_setup}

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
  "guide_content": "# Project Name -- Workspace Guide\\n\\n## Your Role\\nYou are a senior developer on this project.\\n\\n## Tech Stack\\n- ...\\n\\n## Coding Standards\\n- ...\\n\\n## Hard Boundaries (Never Do)\\n- Never edit .env files\\n- Never commit directly to main branch\\n\\n## Test Commands\\n- ...",
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
        {{"matcher": "Edit|Write", "hooks": [{{"type": "command", "command": "bash {config_dir}/hooks/protect-env.sh", "timeout": 5}}]}}
      ],
      "PostToolUse": [
        {{"matcher": "Edit|Write", "hooks": [{{"type": "command", "command": "bash {config_dir}/hooks/format.sh", "timeout": 10}}]}}
      ]
    }}
  }},
  "warnings": ["any warnings"],
  "target": "{target_key}"
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
        target_key=project_info.get("target", "claude"),
        target_label=project_info.get("target_label", "Claude Code"),
        guide_file=project_info.get("guide_file", "CLAUDE.md"),
        config_dir=project_info.get("config_dir", ".claude"),
        languages=", ".join(project_info["languages"]) or "unknown",
        frameworks=", ".join(project_info["frameworks"]) or "unknown",
        file_count=project_info["file_count"],
        has_git=project_info["has_git"],
        has_target_setup=project_info.get("has_agent_dir", False),
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
