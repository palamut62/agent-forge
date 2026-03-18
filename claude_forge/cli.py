"""Claude Forge CLI -- AI-powered Claude Code project setup."""

import click
import os
import sys
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from .config import load_config, save_config, get_api_key
from .models import fetch_models, filter_models, select_model
from .scanner import scan_project, scan_available_skills
from .analyzer import analyze_project, display_plan
from .generator import generate_project
from .learner import interactive_learn, list_lessons, apply_lessons_to_project, load_lessons
from .release import quality_gate, smart_push, create_release, build_exe
from .versioning import show_version_info, interactive_bump

console = Console()

BANNER = r"""
   _____ _                 _        _____
  / ____| |               | |      |  ___|
 | |    | | __ _ _   _  __| | ___  | |_ ___  _ __ __ _  ___
 | |    | |/ _` | | | |/ _` |/ _ \ |  _/ _ \| '__/ _` |/ _ \
 | |____| | (_| | |_| | (_| |  __/ | || (_) | | | (_| |  __/
  \_____|_|\__,_|\__,_|\__,_|\___| \_| \___/|_|  \__, |\___|
                                                   __/ |
                                                  |___/  v0.1.0
"""

MAIN_MENU = [
    ("1", "New Project",        "Create a new project folder and set up Claude Code"),
    ("2", "Init Existing",      "Set up Claude Code in an existing project"),
    ("3", "Scan Project",       "Check a project for missing components"),
    ("4", "Release & Version",  "Version bump, quality check, push, release"),
    ("5", "Learning System",    "Record lessons, view & apply rules"),
    ("6", "Build Executable",   "Build project as .exe (PyInstaller)"),
    ("7", "Skills & Models",    "View skill inventory, change AI model"),
    ("8", "Settings",           "API key, default model, config"),
    ("h", "Help",               "Show usage guide and examples"),
    ("q", "Quit",               "Exit Claude Forge"),
]


def show_menu(items: list[tuple], title: str = "Main Menu") -> str:
    """Display a menu and return the choice."""
    console.print()
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold cyan", width=4)
    table.add_column(style="bold", width=20)
    table.add_column(style="dim")
    for key, name, desc in items:
        table.add_row(f"[{key}]", name, desc)
    console.print(table)
    console.print()
    return Prompt.ask("Select", default="q")


def ask_path(prompt_text: str, must_exist: bool = False) -> str:
    """Ask user for a path."""
    while True:
        raw = Prompt.ask(prompt_text)
        # Expand ~ and clean up
        path = Path(os.path.expanduser(raw)).resolve()
        if must_exist and not path.exists():
            console.print(f"  [red]Path does not exist: {path}[/red]")
            continue
        return str(path)


# --- Interactive Flows ---

def flow_new_project(config: dict) -> None:
    """Create a new project folder + Claude Code setup."""
    console.print(Panel("Create New Project", border_style="green"))

    # Step 1: Where?
    console.print("[bold]Step 1/4 -- Project location[/bold]")
    parent = ask_path("Parent directory (e.g. C:\\Users\\you\\projects)")
    if not Path(parent).exists():
        if Confirm.ask(f"  [yellow]{parent} does not exist. Create it?[/yellow]", default=True):
            Path(parent).mkdir(parents=True, exist_ok=True)
        else:
            return

    # Step 2: Name?
    console.print("\n[bold]Step 2/4 -- Project name[/bold]")
    name = Prompt.ask("Project name (folder name)")
    project_path = Path(parent) / name

    if project_path.exists():
        console.print(f"  [yellow]Folder already exists: {project_path}[/yellow]")
        if not Confirm.ask("  Continue with existing folder?", default=True):
            return
    else:
        project_path.mkdir(parents=True, exist_ok=True)
        console.print(f"  [green][OK] Created: {project_path}[/green]")

    # Step 3: Git init?
    console.print("\n[bold]Step 3/4 -- Git init[/bold]")
    if not (project_path / ".git").exists():
        if Confirm.ask("  Initialize git repository?", default=True):
            import subprocess
            subprocess.run(["git", "init"], cwd=str(project_path), capture_output=True)
            # Create .gitignore
            gitignore = project_path / ".gitignore"
            if not gitignore.exists():
                gitignore.write_text("node_modules/\n__pycache__/\n.venv/\nvenv/\ndist/\nbuild/\n*.pyc\n.env\n.claude/settings.local.json\n", encoding="utf-8")
            console.print("  [green][OK] Git initialized[/green]")
    else:
        console.print("  [dim]Git already initialized[/dim]")

    # Step 4: AI setup
    console.print("\n[bold]Step 4/4 -- Claude Code setup (AI-powered)[/bold]")
    _run_init(str(project_path), config)


def flow_init_existing(config: dict) -> None:
    """Set up Claude Code in an existing project."""
    console.print(Panel("Init Existing Project", border_style="cyan"))
    project_path = ask_path("Project path", must_exist=True)
    _run_init(project_path, config)


def _run_init(project_path: str, config: dict) -> None:
    """Shared init logic."""
    api_key = get_api_key(config)
    if not api_key:
        console.print("[red]API key not set. Go to Settings first.[/red]")
        return

    use_model = config.get("default_model", "")
    if not use_model:
        console.print("[yellow]No default model. Select one:[/yellow]")
        try:
            models = fetch_models(api_key)
            use_model = select_model(models)
            if not use_model:
                return
            config["default_model"] = use_model
            save_config(config)
        except Exception as e:
            console.print(f"[red]Failed: {e}[/red]")
            return

    console.print(f"\n  Model: [cyan]{use_model}[/cyan]")

    # 1. Scan
    console.print("\n[bold]1/4 -- Scanning project...[/bold]")
    project_info = scan_project(project_path)
    console.print(f"  Languages: {', '.join(project_info['languages']) or 'unknown'}")
    console.print(f"  Frameworks: {', '.join(project_info['frameworks']) or 'unknown'}")
    console.print(f"  Files: {project_info['file_count']}")

    # 2. Skills
    console.print("\n[bold]2/4 -- Scanning skill inventory...[/bold]")
    skills_info = scan_available_skills(config.get("claude_home"))
    total = len(skills_info["global_skills"]) + len(skills_info["plugin_commands"]) + len(skills_info["plugin_agents"])
    console.print(f"  [green]Total: {total} skills/agents/commands[/green]")

    # 3. AI
    console.print(f"\n[bold]3/4 -- AI analyzing ({use_model})...[/bold]")
    plan = analyze_project(project_info, skills_info, use_model, api_key)
    if not plan:
        console.print("[red]AI analysis failed.[/red]")
        return

    display_plan(plan)

    if not Confirm.ask("[bold]Apply this plan?[/bold]", default=True):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    # 4. Generate
    console.print("\n[bold]4/4 -- Generating files...[/bold]")
    generate_project(project_path, plan)

    # Apply lessons
    if load_lessons():
        console.print("\n[bold]Applying learned lessons...[/bold]")
        count = apply_lessons_to_project(project_path)
        if count:
            console.print(f"  [green]{count} lesson rules applied.[/green]")

    console.print(f"\n  [green bold]Done![/green bold] Project ready at: [bold]{project_path}[/bold]")


def flow_scan() -> None:
    """Scan project for missing components."""
    console.print(Panel("Scan Project", border_style="cyan"))
    project_path = ask_path("Project path", must_exist=True)
    project_info = scan_project(project_path)

    console.print(f"\n  Project: [bold]{project_info['name']}[/bold]")
    console.print(f"  Languages: {', '.join(project_info['languages']) or 'unknown'}")
    console.print(f"  Frameworks: {', '.join(project_info['frameworks']) or 'unknown'}")
    console.print(f"  Files: {project_info['file_count']}")

    console.print("\n[bold]Claude Code Status:[/bold]")
    checks = [
        ("CLAUDE.md", project_info["has_claude_md"]),
        (".claude/ directory", project_info["has_claude"]),
        ("memory/ directory", project_info["has_memory"]),
        ("Git repo", project_info["has_git"]),
    ]
    for name, ok in checks:
        icon = "[green][+][/green]" if ok else "[red][-][/red]"
        console.print(f"  {icon} {name}")

    if project_info["existing_skills"]:
        console.print(f"\n  Skills: {', '.join(project_info['existing_skills'])}")
    if project_info["existing_hooks"]:
        console.print(f"  Hooks: {', '.join(project_info['existing_hooks'])}")
    if project_info["existing_rules"]:
        console.print(f"  Rules: {', '.join(project_info['existing_rules'])}")


def flow_release() -> None:
    """Release & versioning submenu."""
    RELEASE_MENU = [
        ("1", "Version Info",     "Show current version and suggested bump"),
        ("2", "Bump Version",     "Bump major/minor/patch"),
        ("3", "Quality Check",    "Run quality gate (tests, git clean, TODOs)"),
        ("4", "Smart Push",       "Push with safety checks (blocks main)"),
        ("5", "Full Release",     "Quality gate -> bump -> tag -> push"),
        ("b", "Back",             "Return to main menu"),
    ]

    while True:
        console.print(Panel("Release & Versioning", border_style="green"))
        choice = show_menu(RELEASE_MENU, "Release Menu")

        if choice == "b":
            break

        project_path = ask_path("Project path", must_exist=True)

        if choice == "1":
            show_version_info(project_path)
        elif choice == "2":
            interactive_bump(project_path)
        elif choice == "3":
            quality_gate(project_path)
        elif choice == "4":
            smart_push(project_path)
        elif choice == "5":
            create_release(project_path)

        console.print("\n[dim]Press Enter to continue...[/dim]")
        input()


def flow_learning() -> None:
    """Learning system submenu."""
    LEARN_MENU = [
        ("1", "Record Lesson",    "Record a new mistake and rule"),
        ("2", "View Lessons",     "Show all learned lessons"),
        ("3", "Apply to Project", "Apply lessons as rules to a project"),
        ("b", "Back",             "Return to main menu"),
    ]

    while True:
        console.print(Panel("Learning System", border_style="yellow"))
        choice = show_menu(LEARN_MENU, "Learning Menu")

        if choice == "b":
            break
        elif choice == "1":
            interactive_learn()
        elif choice == "2":
            list_lessons()
        elif choice == "3":
            project_path = ask_path("Project path", must_exist=True)
            count = apply_lessons_to_project(project_path)
            if count:
                console.print(f"  [green]{count} new rules applied.[/green]")
            else:
                console.print("  [dim]No new lessons to apply.[/dim]")

        console.print("\n[dim]Press Enter to continue...[/dim]")
        input()


def flow_build() -> None:
    """Build executable."""
    console.print(Panel("Build Executable", border_style="cyan"))
    project_path = ask_path("Project path", must_exist=True)
    build_exe(project_path)


def flow_skills_models(config: dict) -> None:
    """Skills & models submenu."""
    SM_MENU = [
        ("1", "Skill Inventory",  "Show all available skills and plugins"),
        ("2", "Change Model",     "Select a different AI model"),
        ("b", "Back",             "Return to main menu"),
    ]

    while True:
        console.print(Panel("Skills & Models", border_style="magenta"))
        choice = show_menu(SM_MENU, "Skills & Models")

        if choice == "b":
            break
        elif choice == "1":
            skills_info = scan_available_skills(config.get("claude_home"))
            console.print(Panel("Skill Inventory", border_style="cyan"))
            if skills_info["global_skills"]:
                console.print("\n[bold]Global Skills:[/bold]")
                for s in skills_info["global_skills"]:
                    console.print(f"  [cyan]{s['name']}[/cyan] -- {s['description'] or '(no description)'}")
            console.print(f"\n  [dim]{len(skills_info['plugin_commands'])} plugin commands, {len(skills_info['plugin_agents'])} plugin agents[/dim]")
        elif choice == "2":
            api_key = get_api_key(config)
            if not api_key:
                console.print("[red]Set API key first.[/red]")
                continue
            models = fetch_models(api_key)
            console.print(f"[green]{len(models)} models found.[/green]\n")
            search = Prompt.ask("Search (leave empty for all)", default="")
            free_only = Confirm.ask("Free only?", default=False)
            filtered = filter_models(models, free_only=free_only, search=search or None)
            selected = select_model(filtered)
            if selected:
                config["default_model"] = selected
                save_config(config)
                console.print(f"[green]Default model set to: {selected}[/green]")

        console.print("\n[dim]Press Enter to continue...[/dim]")
        input()


def flow_settings(config: dict) -> None:
    """Settings flow."""
    console.print(Panel("Settings", border_style="cyan"))

    current_key = config.get("openrouter_api_key", "")
    current_model = config.get("default_model", "")
    masked = f"...{current_key[-8:]}" if len(current_key) > 8 else "(none)"

    console.print(f"  API key: [dim]{masked}[/dim]")
    console.print(f"  Default model: [cyan]{current_model or '(none)'}[/cyan]")
    console.print(f"  Claude home: [dim]{config.get('claude_home', '')}[/dim]")
    console.print()

    if Confirm.ask("Change API key?", default=False):
        new_key = Prompt.ask("OpenRouter API key")
        if new_key:
            config["openrouter_api_key"] = new_key

    if Confirm.ask("Change default model?", default=False):
        api_key = get_api_key(config)
        if api_key:
            models = fetch_models(api_key)
            selected = select_model(models)
            if selected:
                config["default_model"] = selected

    save_config(config)
    console.print("[green]Settings saved![/green]")


def flow_help() -> None:
    """Show help page with usage guide and examples."""
    console.print(Panel("Claude Forge -- Help & Usage Guide", border_style="cyan"))

    console.print("""
[bold cyan]== HIZLI BASLANGIC ==[/bold cyan]
  1. [cyan]claude-forge[/cyan] ile interaktif menu ac
  2. [cyan][1] New Project[/cyan] ile sifirdan proje olustur
  3. [cyan][2] Init Existing[/cyan] ile mevcut projeye Claude Code ekle

[bold cyan]== HIZLI MOD ==[/bold cyan]
  [cyan]claude-forge C:\\path\\to\\project[/cyan]         Direkt init (menu atlar)
  [cyan]claude-forge C:\\path\\to\\project -m model[/cyan] Belirli model ile init

[bold cyan]== PROJE TEMPLATE'LERI ==[/bold cyan]
  Hazir sablonlardan hizli proje olustur:
  [cyan]python C:\\Users\\umuti\\Desktop\\pal_project\\templates\\create_project.py <sablon> <isim>[/cyan]

  Mevcut sablonlar:
    [green]fastapi-template[/green]  FastAPI + uvicorn + pydantic-settings + loguru
    [green]telegram-bot[/green]      python-telegram-bot + loguru
    [green]data-pipeline[/green]     ETL pipeline (extract/transform/load) + httpx
    [green]cli-tool[/green]          typer + rich CLI uygulamasi

  Ornek: [dim]python create_project.py fastapi-template my-api "API projem"[/dim]

[bold cyan]== OLUSTURULAN YAPILAR ==[/bold cyan]
  project/
  +-- CLAUDE.md                  Proje rehberi (AI tarafindan olusturulur)
  +-- .claude/
  |   +-- settings.json          Hook ve izin ayarlari
  |   +-- rules/                 Kod kalite kurallari
  |   +-- skills/                Ozel slash komutlari
  +-- tests/                     Test dosyalari
  +-- .env.example               Ortam degiskenleri sablonu

[bold cyan]== GLOBAL SISTEM (Her Terminalden Aktif) ==[/bold cyan]
  [bold]CLAUDE.md[/bold] (C:\\Users\\umuti\\CLAUDE.md)
    Tum projelerde gecerli global kurallar:
    - Kod standartlari (Python 3.12+, type hints, ruff)
    - Test kurallari (pytest, %80 coverage)
    - Mimari kararlar (FastAPI, httpx, pydantic-settings)
    - Git kurallari (Turkce commit, branch naming)

  [bold]Hooks[/bold] (~/.claude/settings.json)
    Otomatik tetiklenen islemler:
    [green]PreToolUse/Bash[/green]   git commit oncesi ruff check + format kontrolu
    [green]PostToolUse/Edit[/green]  .py dosyasi duzenlendikten sonra ruff auto-fix
    [green]Notification[/green]      Uzun islemler bitince bildirim

  [bold]MCP Sunuculari[/bold] (~/.claude/.mcp.json)
    [green]filesystem[/green]  deneembos, pal_project, .openclaw dizinlerine erisim
    [green]memory[/green]      Gelismis hafiza yonetimi
    [green]github[/green]      PR, issue, repo islemleri dogrudan Claude'dan

  [bold]Memory Sistemi[/bold] (~/.claude/projects/.../memory/)
    Farkli oturumlarda bilgi tasir:
    [green]user[/green]       Kullanici profili ve tercihleri
    [green]feedback[/green]   "Bunu yapma/yap" gibi geri bildirimler
    [green]project[/green]    Devam eden isler ve kararlar
    [green]reference[/green]  Harici kaynaklara referanslar

  [bold]Araclar[/bold]
    [green]ruff[/green]  Python linter + formatter (otomatik hook ile)
    [green]jq[/green]    JSON parser (hook'lar icin gerekli)

[bold cyan]== MENU REFERANSI ==[/bold cyan]
  [cyan][1][/cyan] New Project       Klasor + git init + AI setup
  [cyan][2][/cyan] Init Existing     Mevcut projeye Claude Code ekle
  [cyan][3][/cyan] Scan Project      Eksik bilesenleri kontrol et
  [cyan][4][/cyan] Release & Version Versiyon, kalite, push, release
  [cyan][5][/cyan] Learning System   Hata kaydet, kural olustur, uygula
  [cyan][6][/cyan] Build Executable  PyInstaller ile .exe olustur
  [cyan][7][/cyan] Skills & Models   Skill envanter, AI model degistir
  [cyan][8][/cyan] Settings          API key, model, config ayarlari

[bold cyan]== OGRENME SISTEMI ==[/bold cyan]
  1. Hata yaptin (main'e push, test unutma vs.)
  2. [cyan][5] > Record Lesson[/cyan] ile hatani ve kuralini kaydet
  3. Sonraki init'te kurallar otomatik uygulanir
  4. Dersler global: ~/.claude-forge/lessons.json

[bold cyan]== VERSIYON YONETIMI ==[/bold cyan]
  - pyproject.toml / package.json / Cargo.toml'dan okur
  - Git commit'lere gore onerilen bump:
       [dim]feat!: breaking  ->  MAJOR (1.0.0 -> 2.0.0)
       feat: feature    ->  MINOR (1.0.0 -> 1.1.0)
       fix: bug fix     ->  PATCH (1.0.0 -> 1.0.1)[/dim]

[bold cyan]== CONFIG DOSYALARI ==[/bold cyan]
  ~/.claude-forge/config.json      API key, default model
  ~/.claude-forge/lessons.json     Ogrenilen dersler (global)
  ~/.claude/settings.json          Hook'lar, izinler, pluginler
  ~/.claude/.mcp.json              MCP sunucu ayarlari
  C:\\Users\\umuti\\CLAUDE.md         Global proje kurallari
""")


# --- Main Entry Point ---

@click.command()
@click.argument("project_path", required=False, type=click.Path())
@click.option("--model", "-m", help="Override default model")
def main(project_path, model):
    """Claude Forge -- AI-powered Claude Code project setup tool.

    Run without arguments for interactive mode.
    Run with a path for quick init: claude-forge C:\\path\\to\\project
    """
    config = load_config()

    # Quick mode: claude-forge <path>
    if project_path:
        path = Path(project_path)
        if not path.exists():
            if Confirm.ask(f"[yellow]{path} does not exist. Create it?[/yellow]", default=True):
                path.mkdir(parents=True, exist_ok=True)
            else:
                raise SystemExit(0)
        if model:
            config["default_model"] = model
        _run_init(str(path.resolve()), config)
        return

    # Interactive mode
    console.print(BANNER)
    console.print(f"  [dim]Model: {config.get('default_model', '(not set)')}[/dim]")
    console.print(f"  [dim]Lessons: {len(load_lessons())} learned[/dim]")

    while True:
        choice = show_menu(MAIN_MENU)

        try:
            if choice == "1":
                flow_new_project(config)
            elif choice == "2":
                flow_init_existing(config)
            elif choice == "3":
                flow_scan()
            elif choice == "4":
                flow_release()
            elif choice == "5":
                flow_learning()
            elif choice == "6":
                flow_build()
            elif choice == "7":
                flow_skills_models(config)
            elif choice == "8":
                flow_settings(config)
            elif choice == "h":
                flow_help()
            elif choice == "q":
                console.print("\n[dim]Bye![/dim]")
                break
            else:
                console.print("[yellow]Invalid choice.[/yellow]")
        except KeyboardInterrupt:
            console.print("\n[dim]Cancelled.[/dim]")
            continue
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            continue


if __name__ == "__main__":
    main()
