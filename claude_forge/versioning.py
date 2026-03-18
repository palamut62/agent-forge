"""Semantic versioning based on changes."""

import re
import subprocess
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

console = Console()

# Conventional commit patterns
MAJOR_PATTERNS = [r"BREAKING CHANGE", r"^feat!:", r"^fix!:", r"^refactor!:"]
MINOR_PATTERNS = [r"^feat:", r"^feat\("]
PATCH_PATTERNS = [r"^fix:", r"^fix\(", r"^perf:", r"^refactor:", r"^docs:", r"^style:", r"^chore:"]


def get_current_version(project_path: str) -> str | None:
    """Detect current version from project files."""
    path = Path(project_path)

    # Check package.json
    pkg = path / "package.json"
    if pkg.exists():
        import json
        data = json.loads(pkg.read_text(encoding="utf-8"))
        return data.get("version")

    # Check pyproject.toml
    pyp = path / "pyproject.toml"
    if pyp.exists():
        content = pyp.read_text(encoding="utf-8")
        m = re.search(r'version\s*=\s*"([^"]+)"', content)
        if m:
            return m.group(1)

    # Check setup.py
    setup = path / "setup.py"
    if setup.exists():
        content = setup.read_text(encoding="utf-8")
        m = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
        if m:
            return m.group(1)

    # Check Cargo.toml
    cargo = path / "Cargo.toml"
    if cargo.exists():
        content = cargo.read_text(encoding="utf-8")
        m = re.search(r'version\s*=\s*"([^"]+)"', content)
        if m:
            return m.group(1)

    return None


def parse_version(version: str) -> tuple[int, int, int]:
    """Parse semver string to tuple."""
    m = re.match(r"(\d+)\.(\d+)\.(\d+)", version)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    return 0, 0, 0


def bump_version(current: str, bump_type: str) -> str:
    """Bump version based on type."""
    major, minor, patch = parse_version(current)
    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    else:
        return f"{major}.{minor}.{patch + 1}"


def detect_bump_type(project_path: str, since_tag: str | None = None) -> str:
    """Analyze git commits to determine bump type."""
    try:
        cmd = ["git", "log", "--oneline", "--no-decorate"]
        if since_tag:
            cmd.append(f"{since_tag}..HEAD")
        else:
            cmd.append("-20")  # last 20 commits

        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=project_path
        )
        commits = result.stdout.strip().splitlines()
    except Exception:
        return "patch"

    if not commits:
        return "patch"

    # Check each commit message
    has_major = False
    has_minor = False

    for commit in commits:
        # Remove hash prefix
        msg = commit.split(" ", 1)[1] if " " in commit else commit

        for pattern in MAJOR_PATTERNS:
            if re.search(pattern, msg, re.IGNORECASE):
                has_major = True
                break

        for pattern in MINOR_PATTERNS:
            if re.search(pattern, msg, re.IGNORECASE):
                has_minor = True
                break

    if has_major:
        return "major"
    elif has_minor:
        return "minor"
    return "patch"


def update_version_in_files(project_path: str, old_version: str, new_version: str) -> list[str]:
    """Update version string in project files."""
    path = Path(project_path)
    updated = []

    version_files = [
        "package.json",
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "Cargo.toml",
        "__init__.py",
        "version.py",
    ]

    for fname in version_files:
        for fp in path.rglob(fname):
            # Skip node_modules, venv etc.
            if any(skip in str(fp) for skip in ["node_modules", ".venv", "venv", "__pycache__"]):
                continue
            try:
                content = fp.read_text(encoding="utf-8")
                if old_version in content:
                    new_content = content.replace(old_version, new_version)
                    fp.write_text(new_content, encoding="utf-8")
                    updated.append(str(fp.relative_to(path)))
            except Exception:
                continue

    return updated


def get_last_tag(project_path: str) -> str | None:
    """Get the latest git tag."""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True, text=True, cwd=project_path,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def show_version_info(project_path: str) -> None:
    """Display version information and suggested bump."""
    current = get_current_version(project_path)
    last_tag = get_last_tag(project_path)
    suggested = detect_bump_type(project_path, last_tag)

    console.print(Panel("Version Info", border_style="cyan"))
    console.print(f"  Current version: [bold]{current or 'not found'}[/bold]")
    console.print(f"  Last git tag: [dim]{last_tag or 'none'}[/dim]")
    console.print(f"  Suggested bump: [yellow]{suggested}[/yellow]")

    if current:
        new = bump_version(current, suggested)
        console.print(f"  Next version: [green]{new}[/green]")


def interactive_bump(project_path: str) -> str | None:
    """Interactive version bump."""
    current = get_current_version(project_path)
    if not current:
        console.print("[red]Could not detect current version.[/red]")
        return None

    last_tag = get_last_tag(project_path)
    suggested = detect_bump_type(project_path, last_tag)

    console.print(f"  Current: [bold]{current}[/bold]")
    console.print(f"  Suggested: [yellow]{suggested}[/yellow] -> [green]{bump_version(current, suggested)}[/green]")

    bump = Prompt.ask(
        "Bump type",
        choices=["major", "minor", "patch", "skip"],
        default=suggested,
    )

    if bump == "skip":
        return None

    new_version = bump_version(current, bump)
    updated = update_version_in_files(project_path, current, new_version)

    for f in updated:
        console.print(f"  [green][OK][/green] Updated: {f}")

    console.print(f"\n  [green]Version bumped: {current} -> {new_version}[/green]")
    return new_version
