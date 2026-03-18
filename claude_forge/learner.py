"""Learning system - learns from mistakes and adds rules automatically."""

import json
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

console = Console()

LESSONS_FILE = Path.home() / ".claude-forge" / "lessons.json"


def load_lessons() -> list[dict]:
    """Load learned lessons."""
    if LESSONS_FILE.exists():
        return json.loads(LESSONS_FILE.read_text(encoding="utf-8"))
    return []


def save_lessons(lessons: list[dict]) -> None:
    """Save lessons to disk."""
    LESSONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    LESSONS_FILE.write_text(
        json.dumps(lessons, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def add_lesson(category: str, mistake: str, fix: str, rule: str) -> None:
    """Add a new lesson learned."""
    lessons = load_lessons()
    lesson = {
        "id": len(lessons) + 1,
        "date": datetime.now().isoformat(),
        "category": category,
        "mistake": mistake,
        "fix": fix,
        "rule": rule,
        "applied_count": 0,
    }
    lessons.append(lesson)
    save_lessons(lessons)
    console.print(f"  [green][OK][/green] Lesson #{lesson['id']} saved: {rule[:60]}")


def list_lessons(category: str | None = None) -> None:
    """Display all lessons."""
    lessons = load_lessons()
    if category:
        lessons = [l for l in lessons if l["category"] == category]

    if not lessons:
        console.print("[dim]No lessons recorded yet.[/dim]")
        return

    console.print(Panel(f"Learned Lessons ({len(lessons)})", border_style="cyan"))
    for l in lessons:
        console.print(
            f"  [dim]#{l['id']}[/dim] [{l['category']}] {l['rule']}\n"
            f"      [dim]Mistake: {l['mistake'][:80]}[/dim]\n"
            f"      [dim]Applied: {l['applied_count']}x[/dim]"
        )


def apply_lessons_to_project(project_path: str) -> int:
    """Apply learned lessons as rules to a project."""
    lessons = load_lessons()
    if not lessons:
        return 0

    path = Path(project_path)
    rules_dir = path / ".claude" / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)

    applied = 0
    for lesson in lessons:
        rule_file = rules_dir / f"lesson-{lesson['id']}.md"
        if rule_file.exists():
            continue

        content = f"""---
description: Auto-learned rule from past mistake. Apply always.
---

# Lesson #{lesson['id']} -- {lesson['category']}

## Rule
{lesson['rule']}

## Context
- Mistake: {lesson['mistake']}
- Fix: {lesson['fix']}
- Learned: {lesson['date'][:10]}
"""
        rule_file.write_text(content, encoding="utf-8")
        lesson["applied_count"] += 1
        applied += 1
        console.print(f"  [green][OK][/green] Rule applied: lesson-{lesson['id']}.md")

    save_lessons(lessons)
    return applied


def interactive_learn() -> None:
    """Interactive lesson recording."""
    console.print(Panel("Record a New Lesson", border_style="yellow"))

    categories = ["code-quality", "git", "security", "testing", "deployment", "performance", "other"]
    console.print("Categories: " + ", ".join(f"[cyan]{c}[/cyan]" for c in categories))
    category = Prompt.ask("Category", default="code-quality")

    mistake = Prompt.ask("What was the mistake?")
    fix = Prompt.ask("How was it fixed?")
    rule = Prompt.ask("What rule should prevent this?")

    add_lesson(category, mistake, fix, rule)

    if Confirm.ask("Apply this lesson to current project?", default=True):
        apply_lessons_to_project(".")
