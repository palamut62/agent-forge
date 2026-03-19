"""Agent Forge CLI -- multi-target AI assistant setup and management."""

import click
import os
import sys
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table
from rich.align import Align

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import json

from .config import CONFIG_DIR, load_config, save_config, get_api_key
from .models import fetch_models, filter_models, select_model
from .scanner import scan_project, scan_available_skills
from .analyzer import analyze_project, display_plan
from .generator import generate_project
from .learner import interactive_learn, list_lessons, apply_lessons_to_project, load_lessons
from .release import quality_gate, smart_push, create_release, build_exe
from .versioning import show_version_info, interactive_bump
from .profiles.loader import load_profile, list_profiles
from .profiles.applicator import apply_profile
from .profiles.extractor import extract_profile, save_profile_yaml
from .navigator import build_registry, match_skills, display_skill_analysis
from .mapper import write_codemap
from .context_manager import display_context_status, display_compact_preview
from .sync import export_project, import_project, diff_projects, display_diff
from .targets import TARGETS, get_target_home, get_target_platform, normalize_target
from .tui import MenuOption, fullscreen_menu

console = Console()

BANNER = r"""
   _____ _                 _        _____
  / ____| |               | |      |  ___|
 | |    | | __ _ _   _  __| | ___  | |_ ___  _ __ __ _  ___
 | |    | |/ _` | | | |/ _` |/ _ \ |  _/ _ \| '__/ _` |/ _ \
 | |____| | (_| | |_| | (_| |  __/ | || (_) | | | (_| |  __/
  \_____|_|\__,_|\__,_|\__,_|\___| \_| \___/|_|  \__, |\___|
                                                   __/ |
                                                  |___/  v0.2.0
"""

MAIN_MENU = [
    ("1", "New Project",        "Create a new project folder and set up an AI coding assistant"),
    ("2", "Init Existing",      "Set up an AI coding assistant in an existing project"),
    ("3", "Scan Project",       "Check a project for missing components"),
    ("4", "Release & Version",  "Version bump, quality check, push, release"),
    ("5", "Learning System",    "Record lessons, view & apply rules"),
    ("6", "Build Executable",   "Build project as .exe (PyInstaller)"),
    ("7", "Skills & Models",    "View skill inventory, change AI model"),
    ("8", "Profiles",           "Manage project profiles"),
    ("9", "Map & Context",      "Codemap, memory management"),
    ("s", "Sync",               "Cross-project setup sync"),
    ("t", "Target Platform",    "Choose Claude, Codex, or Antigravity"),
    ("0", "Settings",           "API key, default model, config"),
    ("h", "Help",               "Show usage guide and examples"),
    ("q", "Quit",               "Exit Agent Forge"),
]

HOME_MENU = [
    ("1", "New Project",        "Create a new project and bootstrap assistant setup"),
    ("2", "Init Existing",      "Add assistant setup to an existing project"),
    ("t", "Choose Target",      "Switch between Claude Code, Codex, and Antigravity"),
    ("0", "Settings",           "Set API key, default model, and defaults"),
    ("a", "All Tools",          "Open advanced tools"),
    ("h", "Help",               "See usage examples and project structure"),
    ("q", "Quit",               "Exit Agent Forge"),
]

INTRO_MENU = [
    ("c", "Continue", "Open quick start"),
    ("t", "Change Target", "Pick Claude Code, Codex, or Antigravity"),
    ("h", "Help", "Open usage guide"),
    ("q", "Quit", "Exit Agent Forge"),
]

def show_menu(
    items: list[tuple],
    title: str = "Main Menu",
    subtitle: str = "",
    cancel_value: str = "q",
    initial_key: str | None = None,
) -> str:
    """Display a menu and return the choice."""
    if sys.stdin.isatty() and sys.stdout.isatty():
        options = [
            MenuOption(
                key=key,
                title=name,
                description=desc,
                meta=f"Shortcut: {key}",
            )
            for key, name, desc in items
        ]
        result = fullscreen_menu(
            title=title,
            subtitle=subtitle or "Use arrow keys to move, Enter to select.",
            options=options,
            footer="Up/Down move  Type to filter  Ctrl+L clear  Enter select  Esc back",
            initial_key=initial_key,
        )
        return result or cancel_value

    console.print()
    if subtitle:
        console.print(Panel(subtitle, title=title, border_style="bright_blue"))
    else:
        console.print(Panel(Align.center(title), border_style="bright_blue"))
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold cyan", width=4)
    table.add_column(style="bold", width=20)
    table.add_column(style="dim")
    for key, name, desc in items:
        table.add_row(f"[{key}]", name, desc)
    console.print(table)
    console.print()
    return Prompt.ask("Select", default=cancel_value)

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


def render_target_table(config: dict) -> None:
    """Display supported target platforms."""
    default_target = normalize_target(config.get("default_target", "claude"))
    table = Table(title="Target Platforms", border_style="magenta")
    table.add_column("Key", style="bold cyan", width=14)
    table.add_column("Platform", style="bold")
    table.add_column("Guide File", style="green", width=18)
    table.add_column("Config Dir", style="yellow", width=18)
    table.add_column("Default", justify="center", width=10)

    for key in ("claude", "codex", "antigravity"):
        target = get_target_platform(key)
        table.add_row(
            key,
            target.label,
            target.guide_file,
            target.config_dir,
            "[green]YES[/green]" if key == default_target else "",
        )
    console.print(table)


def ask_target(config: dict, prompt_text: str = "Target assistant", allow_default: bool = True) -> str:
    """Ask which assistant platform to configure."""
    default_target = normalize_target(config.get("default_target", "claude"))
    if sys.stdin.isatty() and sys.stdout.isatty():
        options = []
        for key in ("claude", "codex", "antigravity"):
            target = get_target_platform(key)
            meta = f"Guide: {target.guide_file}  Config: {target.config_dir}"
            if key == default_target:
                meta += "  Default target"
            options.append(
                MenuOption(
                    key=key,
                    title=target.label,
                    description=f"Configure project output for {target.label}.",
                    meta=meta,
                )
            )
        result = fullscreen_menu(
            title="Target Platform",
            subtitle=prompt_text,
            options=options,
            footer="Up/Down move  Type to filter  Ctrl+L clear  Enter confirm  Esc back",
            initial_key=default_target if allow_default else "claude",
        )
        if result:
            return normalize_target(result)
        if allow_default:
            return default_target

    render_target_table(config)
    default_value = default_target if allow_default else None
    choice = Prompt.ask(
        prompt_text,
        choices=["claude", "codex", "antigravity"],
        default=default_value,
    )
    return normalize_target(choice)


def target_status_line(config: dict) -> str:
    """Short status line used in menus."""
    target = get_target_platform(config.get("default_target"))
    return (
        f"Active target: [cyan]{target.label}[/cyan]\n"
        f"Guide file: [green]{target.guide_file}[/green]\n"
        f"Config dir: [yellow]{target.config_dir}[/yellow]\n"
        f"Model: [cyan]{config.get('default_model', '(not set)')}[/cyan]"
    )


def home_subtitle(config: dict) -> str:
    """Landing screen copy shown before the full tool menu."""
    target = get_target_platform(config.get("default_target"))
    return (
        "Quick start for Claude Code, Codex, and Antigravity.\n"
        f"Current target: {target.label}  |  "
        f"Guide: {target.guide_file}  |  "
        f"Config: {target.config_dir}  |  "
        f"Model: {config.get('default_model', '(not set)')}\n"
        "Choose a starting action. Advanced tools are under All Tools."
    )


def intro_subtitle(config: dict) -> str:
    """Short product intro shown before quick-start menu."""
    target = get_target_platform(config.get("default_target"))
    return (
        "Set up and manage Claude Code, Codex, and Antigravity workflows.\n"
        f"Default target: {target.label}   Default model: {config.get('default_model', '(not set)')}"
    )


# --- Interactive Flows ---

def flow_new_project(config: dict) -> None:
    """Create a new project folder + target assistant setup."""
    console.print(Panel("Create New Project", border_style="green"))
    target = ask_target(config, prompt_text="Select target platform")
    target_platform = get_target_platform(target)

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
                gitignore.write_text(
                    f"node_modules/\n__pycache__/\n.venv/\nvenv/\ndist/\nbuild/\n*.pyc\n.env\n{target_platform.config_dir}/{target_platform.local_settings_file}\n",
                    encoding="utf-8",
                )
            console.print("  [green][OK] Git initialized[/green]")
    else:
        console.print("  [dim]Git already initialized[/dim]")

    # Step 4: AI setup
    console.print(f"\n[bold]Step 4/4 -- {target_platform.label} setup (AI-powered)[/bold]")
    _run_init(str(project_path), config, target=target)


def flow_init_existing(config: dict) -> None:
    """Set up a target assistant in an existing project."""
    console.print(Panel("Init Existing Project", border_style="cyan"))
    project_path = ask_path("Project path", must_exist=True)
    target = ask_target(config, prompt_text="Select target platform")
    _run_init(project_path, config, target=target)


def flow_target_platform(config: dict) -> None:
    """Choose the active target platform."""
    console.print(Panel("Target Platform", border_style="magenta"))
    selected = ask_target(config, prompt_text="Set default target platform")
    config["default_target"] = selected
    save_config(config)
    console.print(f"[green]Default target set to: {get_target_platform(selected).label}[/green]")


def _run_init(project_path: str, config: dict, target: str | None = None) -> None:
    """Shared init logic."""
    resolved_target = normalize_target(target or config.get("default_target"))
    target_platform = get_target_platform(resolved_target)
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

    console.print(f"\n  Target: [cyan]{target_platform.label}[/cyan]")
    console.print(f"  Model: [cyan]{use_model}[/cyan]")

    # 1. Scan
    console.print("\n[bold]1/4 -- Scanning project...[/bold]")
    project_info = scan_project(project_path, target=resolved_target)
    console.print(f"  Languages: {', '.join(project_info['languages']) or 'unknown'}")
    console.print(f"  Frameworks: {', '.join(project_info['frameworks']) or 'unknown'}")
    console.print(f"  Files: {project_info['file_count']}")

    # 2. Skills
    console.print("\n[bold]2/4 -- Scanning skill inventory...[/bold]")
    skills_info = scan_available_skills(get_target_home(config, resolved_target), target=resolved_target)
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
    generate_project(
        project_path,
        plan,
        target=resolved_target,
        target_home=get_target_home(config, resolved_target),
    )

    # Apply lessons
    if load_lessons():
        console.print("\n[bold]Applying learned lessons...[/bold]")
        count = apply_lessons_to_project(project_path, target=resolved_target)
        if count:
            console.print(f"  [green]{count} lesson rules applied.[/green]")

    console.print(f"\n  [green bold]Done![/green bold] Project ready at: [bold]{project_path}[/bold]")


def flow_scan() -> None:
    """Scan project for missing components."""
    console.print(Panel("Scan Project", border_style="cyan"))
    project_path = ask_path("Project path", must_exist=True)
    target = ask_target(load_config(), prompt_text="Which target should be checked")
    project_info = scan_project(project_path, target=target)

    console.print(f"\n  Project: [bold]{project_info['name']}[/bold]")
    console.print(f"  Languages: {', '.join(project_info['languages']) or 'unknown'}")
    console.print(f"  Frameworks: {', '.join(project_info['frameworks']) or 'unknown'}")
    console.print(f"  Files: {project_info['file_count']}")

    console.print(f"\n[bold]{project_info['target_label']} Status:[/bold]")
    checks = [
        (project_info["guide_file"], project_info["has_guide"]),
        (f"{project_info['config_dir']}/ directory", project_info["has_agent_dir"]),
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
        choice = show_menu(RELEASE_MENU, "Release Menu", cancel_value="b")

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
        choice = show_menu(LEARN_MENU, "Learning Menu", cancel_value="b")

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
        ("2", "Skill Navigator",  "Analyze project and recommend skills"),
        ("3", "Change Model",     "Select a different AI model"),
        ("b", "Back",             "Return to main menu"),
    ]

    while True:
        console.print(Panel("Skills & Models", border_style="magenta"))
        choice = show_menu(SM_MENU, "Skills & Models", cancel_value="b")

        if choice == "b":
            break
        elif choice == "1":
            target = ask_target(config, prompt_text="Select target platform")
            skills_info = scan_available_skills(get_target_home(config, target), target=target)
            console.print(Panel("Skill Inventory", border_style="cyan"))
            if skills_info["global_skills"]:
                console.print("\n[bold]Global Skills:[/bold]")
                for s in skills_info["global_skills"]:
                    console.print(f"  [cyan]{s['name']}[/cyan] -- {s['description'] or '(no description)'}")
            console.print(f"\n  [dim]{len(skills_info['plugin_commands'])} plugin commands, {len(skills_info['plugin_agents'])} plugin agents[/dim]")
        elif choice == "2":
            project_path_input = ask_path("Project path", must_exist=True)
            target = ask_target(config, prompt_text="Select target platform")
            project_info = scan_project(project_path_input, target=target)
            registry = build_registry(get_target_home(config, target), target=target)
            result = match_skills(registry, project_info["languages"], project_info["frameworks"])
            display_skill_analysis(result, project_info["name"])
        elif choice == "3":
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


def flow_profiles(config: dict) -> None:
    """Profile management submenu."""
    PROFILE_MENU = [
        ("1", "List Profiles",    "Show available profiles"),
        ("2", "Apply to Project", "Apply a profile to a project"),
        ("3", "Create from Project", "Extract profile from existing project"),
        ("b", "Back",             "Return to main menu"),
    ]
    while True:
        console.print(Panel("Profile Management", border_style="magenta"))
        choice = show_menu(PROFILE_MENU, "Profiles", cancel_value="b")

        if choice == "b":
            break
        elif choice == "1":
            names = list_profiles()
            console.print("\n[bold]Available Profiles:[/bold]")
            for name in names:
                try:
                    p = load_profile(name)
                    console.print(f"  [cyan]{name}[/cyan] -- {p.description}")
                except Exception:
                    console.print(f"  [cyan]{name}[/cyan] -- [dim](error loading)[/dim]")
        elif choice == "2":
            names = list_profiles()
            console.print("Profiles: " + ", ".join(f"[cyan]{n}[/cyan]" for n in names))
            profile_name = Prompt.ask("Profile name")
            project_path = ask_path("Project path", must_exist=True)
            target = ask_target(config, prompt_text="Apply profile for which target")
            try:
                profile = load_profile(profile_name)
                apply_profile(
                    profile,
                    Path(project_path),
                    target=target,
                    target_home=get_target_home(config, target),
                )
            except FileNotFoundError as e:
                console.print(f"[red]{e}[/red]")
        elif choice == "3":
            project_path = ask_path("Project path", must_exist=True)
            name = Prompt.ask("Profile name")
            target = ask_target(config, prompt_text="Extract profile from which target")
            profile = extract_profile(Path(project_path), name, target=target)
            out_dir = CONFIG_DIR / "profiles"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / f"{name}.yaml"
            save_profile_yaml(profile, out_file)
            console.print(f"[green]Profile saved: {out_file}[/green]")

        console.print("\n[dim]Press Enter to continue...[/dim]")
        input()


def flow_map_context() -> None:
    """Map & Context submenu."""
    MAP_MENU = [
        ("1", "Generate Codemap",   "Proje haritasi uret (docs/CODEMAP.md)"),
        ("2", "Context Status",     "Memory ve context durumu"),
        ("3", "Compact Preview",    "Eski memory dosyalarini goster"),
        ("b", "Back",               "Return to main menu"),
    ]
    while True:
        console.print(Panel("Map & Context", border_style="blue"))
        choice = show_menu(MAP_MENU, "Map & Context", cancel_value="b")

        if choice == "b":
            break
        elif choice == "1":
            project_path = ask_path("Project path", must_exist=True)
            write_codemap(Path(project_path))
        elif choice == "2":
            project_path = ask_path("Project path", must_exist=True)
            target = ask_target(load_config(), prompt_text="Show context for which target")
            display_context_status(Path(project_path), target=target)
        elif choice == "3":
            project_path = ask_path("Project path", must_exist=True)
            display_compact_preview(Path(project_path))

        console.print("\n[dim]Press Enter to continue...[/dim]")
        input()


def flow_sync() -> None:
    """Cross-project sync submenu."""
    SYNC_MENU = [
        ("1", "Export",  "Mevcut projenin setup'ini disa aktar"),
        ("2", "Import",  "Baska projeden setup al"),
        ("3", "Diff",    "Iki projenin setup'ini karsilastir"),
        ("b", "Back",    "Return to main menu"),
    ]
    while True:
        console.print(Panel("Cross-Project Sync", border_style="green"))
        choice = show_menu(SYNC_MENU, "Sync", cancel_value="b")

        if choice == "b":
            break
        elif choice == "1":
            project_path = ask_path("Project path", must_exist=True)
            target = ask_target(load_config(), prompt_text="Export setup for which target")
            data = export_project(Path(project_path), target=target)
            out = Path(project_path) / "agent-forge-export.json"
            out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            console.print(f"[green]Exported: {out}[/green]")
        elif choice == "2":
            project_path = ask_path("Target project path", must_exist=True)
            export_file = ask_path("Export JSON file path", must_exist=True)
            target = ask_target(load_config(), prompt_text="Import setup for which target")
            stats = import_project(Path(project_path), Path(export_file), target=target)
            console.print(f"\n[green]Imported: {stats['rules_imported']} rules, {stats['hooks_imported']} hooks[/green]")
            if stats["skipped"]:
                console.print(f"[dim]Skipped: {stats['skipped']}[/dim]")
        elif choice == "3":
            p1 = ask_path("Project 1 path", must_exist=True)
            p2 = ask_path("Project 2 path", must_exist=True)
            target = ask_target(load_config(), prompt_text="Compare which target setup")
            diff = diff_projects(Path(p1), Path(p2), target=target)
            display_diff(diff, Path(p1).name, Path(p2).name)

        console.print("\n[dim]Press Enter to continue...[/dim]")
        input()


def flow_settings(config: dict) -> None:
    """Settings flow."""
    console.print(Panel("Settings", border_style="cyan"))

    current_key = config.get("openrouter_api_key", "")
    current_model = config.get("default_model", "")
    current_target = get_target_platform(config.get("default_target"))
    masked = f"...{current_key[-8:]}" if len(current_key) > 8 else "(none)"

    console.print(f"  API key: [dim]{masked}[/dim]")
    console.print(f"  Default model: [cyan]{current_model or '(none)'}[/cyan]")
    console.print(f"  Default target: [cyan]{current_target.label}[/cyan]")
    for key in TARGETS:
        console.print(f"  {key} home: [dim]{get_target_home(config, key)}[/dim]")
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

    if Confirm.ask("Change default target?", default=False):
        config["default_target"] = ask_target(config, prompt_text="Set default target platform")

    save_config(config)
    console.print("[green]Settings saved![/green]")


def flow_help() -> None:
    """Show help page with usage guide and examples."""
    console.print(Panel("Agent Forge -- Help & Usage Guide", border_style="cyan"))

    console.print("""
[bold cyan]== HIZLI BASLANGIC ==[/bold cyan]
  1. [cyan]agent-forge[/cyan] ile acilis menusu
  2. [cyan]Continue[/cyan] -> [cyan]New Project[/cyan] veya [cyan]Init Existing[/cyan]
  3. Hedef platformu [cyan]Change Target[/cyan] ile sec (Claude Code / Codex / Antigravity)

[bold cyan]== KOMUT KULLANIMI ==[/bold cyan]
  [cyan]agent-forge[/cyan]
    Interaktif mod (TUI/menu)

  [cyan]agent-forge C:\\path\\to\\project[/cyan]
    Proje yoluyla hizli kurulum akisi

  [cyan]agent-forge C:\\path\\to\\project -t codex[/cyan]
    Dogrudan Codex hedefiyle kurulum

  [cyan]agent-forge --flow settings[/cyan]
    Belirli bir akis ekranini direkt ac

[bold cyan]== TUI KISAYOLLAR ==[/bold cyan]
  [cyan]Up/Down[/cyan]       Menu gez
  [cyan]Enter[/cyan]         Secili islemi calistir
  [cyan]Type[/cyan]          Listeyi filtrele
  [cyan]/[/cyan]             Global hizli komut paleti (ornek: /settings, /scan)
  [cyan]Esc / Sol[/cyan]     Geri don
  [cyan]Backspace[/cyan]     Filtreyi sil, bossa geri don
  [cyan]Ctrl+L[/cyan]        Filtre temizle
  [cyan]?[/cyan]             Kisayol yardimi
  [cyan]Ctrl+C[/cyan]        Cikis

[bold cyan]== ANA MENULER ==[/bold cyan]
  [cyan]Quick Start[/cyan]      Yeni proje, mevcut projeye kurulum, ayarlar
  [cyan]All Tools[/cyan]        Scan, Release, Learning, Build, Profiles, Sync
  [cyan]Target Platform[/cyan]  Varsayilan hedef platform degisimi

[bold cyan]== URETILEN DOSYALAR ==[/bold cyan]
  Rehber dosyasi: [cyan]CLAUDE.md / AGENTS.md / ANTIGRAVITY.md[/cyan]
  Konfigurasyon: [cyan].claude/[/cyan] [cyan].codex/[/cyan] [cyan].antigravity/[/cyan]
  Ayrica: rules/, skills/, tests/, .env.example

[bold cyan]== KONFIGURASYON ==[/bold cyan]
  [cyan]~/.agent-forge/config.json[/cyan]   API key, default model, default target
  [cyan]~/.agent-forge/lessons.json[/cyan]  Ogrenme sistemi kurallari

[bold cyan]== NOT ==[/bold cyan]
  Windows'ta Python ve npm ikisi de yukluysa, npm surumu icin gerekirse
  [cyan]agent-forge.cmd[/cyan] komutunu kullanin.
  Geriye uyumluluk icin [cyan]claude-forge[/cyan] alias'i da calismaya devam eder.
  Python CLI'yi dogrudan acmak icin [cyan]agent-forge-py[/cyan] kullanin.
""")


# --- Main Entry Point ---


def run_flow(flow: str, config: dict) -> bool:
    """Run a single named flow and return True if handled."""
    handlers = {
        "new-project": lambda: flow_new_project(config),
        "init-existing": lambda: flow_init_existing(config),
        "scan-project": flow_scan,
        "release": flow_release,
        "learning": flow_learning,
        "build": flow_build,
        "skills-models": lambda: flow_skills_models(config),
        "profiles": lambda: flow_profiles(config),
        "map-context": flow_map_context,
        "sync": flow_sync,
        "target-platform": lambda: flow_target_platform(config),
        "settings": lambda: flow_settings(config),
        "help": flow_help,
    }
    fn = handlers.get(flow)
    if not fn:
        return False
    fn()
    return True

@click.command()
@click.argument("project_path", required=False, type=click.Path())
@click.option("--model", "-m", help="Override default model")
@click.option("--profile", "-p", help="Apply a profile instead of AI analysis")
@click.option("--target", "-t", help="Target assistant: claude, codex, antigravity")
@click.option(
    "--flow",
    type=click.Choice(
        [
            "new-project",
            "init-existing",
            "scan-project",
            "release",
            "learning",
            "build",
            "skills-models",
            "profiles",
            "map-context",
            "sync",
            "target-platform",
            "settings",
            "help",
        ],
        case_sensitive=False,
    ),
    help="Run a specific flow directly",
)
def main(project_path, model, profile, target, flow):
    """Agent Forge -- multi-target AI assistant setup and operations tool.

    Run without arguments for interactive mode.
    Run with a path for quick init: agent-forge C:\\path\\to\\project
    """
    config = load_config()
    resolved_target = normalize_target(target or config.get("default_target"))

    if model:
        config["default_model"] = model
        save_config(config)

    if target:
        config["default_target"] = resolved_target
        save_config(config)

    if flow:
        run_flow(flow.lower(), config)
        return

    # Quick mode: agent-forge <path>
    if project_path:
        path = Path(project_path)
        if not path.exists():
            if Confirm.ask(f"[yellow]{path} does not exist. Create it?[/yellow]", default=True):
                path.mkdir(parents=True, exist_ok=True)
            else:
                raise SystemExit(0)
        if not target:
            console.print(Panel("Select Target Platform", border_style="magenta"))
            resolved_target = ask_target(config, prompt_text="Which platform should be configured", allow_default=False)
        if profile:
            try:
                prof = load_profile(profile)
                apply_profile(
                    prof,
                    path,
                    target=resolved_target,
                    target_home=get_target_home(config, resolved_target),
                )
            except FileNotFoundError as e:
                console.print(f"[red]{e}[/red]")
            return
        _run_init(str(path.resolve()), config, target=resolved_target)
        return

    # Interactive mode
    console.print(Panel("Agent Forge", border_style="blue"))
    console.print(f"[dim]Target:[/dim] {get_target_platform(config.get('default_target')).label}")
    console.print(f"[dim]Model:[/dim] {config.get('default_model', '(not set)')}")
    console.print(f"[dim]Lessons:[/dim] {len(load_lessons())} learned")

    intro_choice = show_menu(
        INTRO_MENU,
        title="Agent Forge",
        subtitle=intro_subtitle(config),
        cancel_value="q",
        initial_key="c",
    )
    if intro_choice == "q":
        console.print("\n[dim]Bye![/dim]")
        return
    if intro_choice == "t":
        flow_target_platform(config)
    elif intro_choice == "h":
        flow_help()

    while True:
        choice = show_menu(
            HOME_MENU,
            title="Quick Start",
            subtitle=home_subtitle(config),
            cancel_value="q",
            initial_key="1",
        )

        try:
            if choice == "1":
                flow_new_project(config)
            elif choice == "2":
                flow_init_existing(config)
            elif choice == "t":
                flow_target_platform(config)
            elif choice == "0":
                flow_settings(config)
            elif choice == "a":
                full_choice = show_menu(
                    MAIN_MENU,
                    title="All Tools",
                    subtitle=target_status_line(config),
                    cancel_value="b",
                )
                if full_choice == "1":
                    flow_new_project(config)
                elif full_choice == "2":
                    flow_init_existing(config)
                elif full_choice == "3":
                    flow_scan()
                elif full_choice == "4":
                    flow_release()
                elif full_choice == "5":
                    flow_learning()
                elif full_choice == "6":
                    flow_build()
                elif full_choice == "7":
                    flow_skills_models(config)
                elif full_choice == "8":
                    flow_profiles(config)
                elif full_choice == "9":
                    flow_map_context()
                elif full_choice == "s":
                    flow_sync()
                elif full_choice == "t":
                    flow_target_platform(config)
                elif full_choice == "0":
                    flow_settings(config)
                elif full_choice == "h":
                    flow_help()
                elif full_choice == "b":
                    continue
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

