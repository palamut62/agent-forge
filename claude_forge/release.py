"""Release management - git workflow, quality gates, build & publish."""

import subprocess
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from .versioning import (
    get_current_version,
    interactive_bump,
    show_version_info,
    get_last_tag,
)
from .learner import load_lessons

console = Console()


def run_cmd(cmd: list[str], cwd: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return result."""
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if check and result.returncode != 0:
        console.print(f"  [red]Command failed: {' '.join(cmd)}[/red]")
        if result.stderr:
            console.print(f"  [dim]{result.stderr[:300]}[/dim]")
    return result


def quality_gate(project_path: str) -> dict:
    """Run quality checks before release."""
    path = Path(project_path)
    results = {
        "git_clean": False,
        "tests_pass": None,
        "no_todo_fixme": True,
        "version_set": False,
        "all_committed": False,
        "passed": False,
    }

    console.print(Panel("Quality Gate", border_style="yellow"))

    # 1. Git clean check
    r = run_cmd(["git", "status", "--porcelain"], cwd=project_path, check=False)
    results["git_clean"] = r.stdout.strip() == ""
    icon = "[green][+][/green]" if results["git_clean"] else "[red][-][/red]"
    console.print(f"  {icon} Working directory clean")
    if not results["git_clean"]:
        console.print(f"      [dim]Uncommitted changes: {len(r.stdout.splitlines())} files[/dim]")

    # 2. Tests
    test_cmds = _detect_test_command(path)
    if test_cmds:
        console.print(f"  [dim]Running: {' '.join(test_cmds)}...[/dim]")
        r = run_cmd(test_cmds, cwd=project_path, check=False)
        results["tests_pass"] = r.returncode == 0
        icon = "[green][+][/green]" if results["tests_pass"] else "[red][-][/red]"
        console.print(f"  {icon} Tests {'passed' if results['tests_pass'] else 'FAILED'}")
    else:
        console.print("  [dim][-] No test command detected, skipping[/dim]")
        results["tests_pass"] = None

    # 3. TODO/FIXME check
    r = run_cmd(
        ["git", "grep", "-n", "-i", "-E", "TODO|FIXME|HACK|XXX"],
        cwd=project_path, check=False,
    )
    todo_count = len(r.stdout.strip().splitlines()) if r.stdout.strip() else 0
    results["no_todo_fixme"] = todo_count < 5  # allow some
    icon = "[green][+][/green]" if results["no_todo_fixme"] else "[yellow][!][/yellow]"
    console.print(f"  {icon} TODO/FIXME items: {todo_count}")

    # 4. Version check
    version = get_current_version(project_path)
    results["version_set"] = version is not None
    icon = "[green][+][/green]" if results["version_set"] else "[red][-][/red]"
    console.print(f"  {icon} Version: {version or 'not found'}")

    # Overall
    critical = [results["git_clean"], results["tests_pass"] is not False]
    results["passed"] = all(critical)

    if results["passed"]:
        console.print("\n  [green]Quality gate PASSED[/green]")
    else:
        console.print("\n  [red]Quality gate FAILED -- fix issues before release[/red]")

    return results


def smart_push(project_path: str) -> bool:
    """Smart git push with safety checks."""
    console.print(Panel("Smart Push", border_style="cyan"))

    # Check current branch
    r = run_cmd(["git", "branch", "--show-current"], cwd=project_path, check=False)
    branch = r.stdout.strip()
    console.print(f"  Branch: [bold]{branch}[/bold]")

    # Block direct push to main/master
    if branch in ("main", "master"):
        console.print("  [red][-] Cannot push directly to {branch}. Create a feature branch first.[/red]")
        return False

    # Check if remote exists
    r = run_cmd(["git", "remote", "-v"], cwd=project_path, check=False)
    if not r.stdout.strip():
        console.print("  [yellow][!] No remote configured. Add one with 'git remote add origin <url>'[/yellow]")
        return False

    # Check for uncommitted changes
    r = run_cmd(["git", "status", "--porcelain"], cwd=project_path, check=False)
    if r.stdout.strip():
        console.print(f"  [yellow][!] {len(r.stdout.splitlines())} uncommitted changes[/yellow]")
        if not Confirm.ask("  Push anyway?", default=False):
            return False

    # Push
    console.print(f"  [dim]Pushing to origin/{branch}...[/dim]")
    r = run_cmd(["git", "push", "-u", "origin", branch], cwd=project_path, check=False)
    if r.returncode == 0:
        console.print(f"  [green][OK] Pushed to origin/{branch}[/green]")
        return True
    else:
        console.print(f"  [red]Push failed: {r.stderr[:200]}[/red]")
        return False


def create_release(project_path: str) -> bool:
    """Full release workflow: quality gate -> version bump -> tag -> push."""
    console.print(Panel("Release Workflow", border_style="green"))

    # Step 1: Quality gate
    gate = quality_gate(project_path)
    if not gate["passed"]:
        if not Confirm.ask("\n  [yellow]Quality gate failed. Continue anyway?[/yellow]", default=False):
            return False

    # Step 2: Version bump
    console.print(f"\n")
    show_version_info(project_path)
    new_version = interactive_bump(project_path)
    if not new_version:
        console.print("  [yellow]Version bump skipped.[/yellow]")
        return False

    # Step 3: Commit version bump
    run_cmd(["git", "add", "-A"], cwd=project_path)
    run_cmd(
        ["git", "commit", "-m", f"chore: bump version to {new_version}"],
        cwd=project_path,
    )
    console.print(f"  [green][OK] Version commit created[/green]")

    # Step 4: Tag
    tag = f"v{new_version}"
    run_cmd(["git", "tag", "-a", tag, "-m", f"Release {tag}"], cwd=project_path)
    console.print(f"  [green][OK] Tag created: {tag}[/green]")

    # Step 5: Push
    if Confirm.ask(f"\n  Push release {tag} to remote?", default=True):
        r = run_cmd(["git", "push", "--follow-tags"], cwd=project_path, check=False)
        if r.returncode == 0:
            console.print(f"  [green][OK] Release {tag} pushed![/green]")
        else:
            console.print(f"  [red]Push failed. Run manually: git push --follow-tags[/red]")

    return True


def build_exe(project_path: str) -> bool:
    """Build executable using PyInstaller."""
    path = Path(project_path)

    console.print(Panel("Build Executable", border_style="cyan"))

    # Find entry point
    entry_candidates = ["main.py", "app.py", "cli.py", "__main__.py"]
    entry = None
    for c in entry_candidates:
        if (path / c).exists():
            entry = c
            break
        # Check in src/
        if (path / "src" / c).exists():
            entry = f"src/{c}"
            break

    if not entry:
        entry = Prompt.ask("Entry point file", default="main.py")

    if not (path / entry).exists():
        console.print(f"  [red]Entry point not found: {entry}[/red]")
        return False

    # Check pyinstaller
    r = subprocess.run([sys.executable, "-m", "PyInstaller", "--version"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        console.print("  [yellow]PyInstaller not found. Installing...[/yellow]")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"],
                       capture_output=True)

    # Get project name
    name = path.name
    version = get_current_version(project_path) or "0.0.0"

    # Build
    console.print(f"  [dim]Building {name} v{version}...[/dim]")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", f"{name}-{version}",
        "--distpath", str(path / "dist"),
        "--workpath", str(path / "build"),
        "--specpath", str(path / "build"),
        str(path / entry),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=project_path)

    if r.returncode == 0:
        exe_name = f"{name}-{version}.exe" if sys.platform == "win32" else f"{name}-{version}"
        console.print(f"  [green][OK] Built: dist/{exe_name}[/green]")
        return True
    else:
        console.print(f"  [red]Build failed: {r.stderr[:300]}[/red]")
        return False


def _detect_test_command(path: Path) -> list[str] | None:
    """Auto-detect test command for the project."""
    # Python
    if (path / "pytest.ini").exists() or (path / "pyproject.toml").exists():
        return [sys.executable, "-m", "pytest", "--tb=short", "-q"]
    if (path / "setup.py").exists():
        return [sys.executable, "-m", "pytest", "--tb=short", "-q"]

    # Node
    pkg = path / "package.json"
    if pkg.exists():
        import json
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            if "test" in data.get("scripts", {}):
                # Detect package manager
                if (path / "bun.lockb").exists():
                    return ["bun", "test"]
                elif (path / "pnpm-lock.yaml").exists():
                    return ["pnpm", "test"]
                elif (path / "yarn.lock").exists():
                    return ["yarn", "test"]
                return ["npm", "test"]
        except Exception:
            pass

    # Go
    if (path / "go.mod").exists():
        return ["go", "test", "./..."]

    # Rust
    if (path / "Cargo.toml").exists():
        return ["cargo", "test"]

    return None
