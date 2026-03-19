"""Fetch and cache skills from everything-claude-code GitHub repo."""

import shutil
import subprocess
import time
from pathlib import Path

from rich.console import Console

console = Console()

ECC_REPO = "https://github.com/affaan-m/everything-claude-code.git"
CACHE_DIR = Path.home() / ".agent-forge" / "ecc-skills-cache"
CACHE_SKILLS_DIR = CACHE_DIR / "skills"
CACHE_MAX_AGE_HOURS = 24


def _cache_age_hours() -> float:
    """Return cache age in hours, or inf if no cache."""
    marker = CACHE_DIR / ".last_fetch"
    if not marker.exists():
        return float("inf")
    age_seconds = time.time() - marker.stat().st_mtime
    return age_seconds / 3600


def _mark_fetched() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / ".last_fetch").write_text(str(time.time()), encoding="utf-8")


def fetch_ecc_skills(force: bool = False) -> Path:
    """Clone/pull ECC repo skills into local cache. Returns skills dir path."""
    age = _cache_age_hours()

    if not force and age < CACHE_MAX_AGE_HOURS and CACHE_SKILLS_DIR.exists():
        return CACHE_SKILLS_DIR

    console.print("[dim]Fetching skills from everything-claude-code...[/dim]")

    try:
        if (CACHE_DIR / ".git").exists():
            # Sparse pull — only update skills/
            subprocess.run(
                ["git", "pull", "--ff-only"],
                cwd=str(CACHE_DIR),
                capture_output=True,
                timeout=60,
            )
        else:
            # Fresh sparse clone — only skills/ directory
            if CACHE_DIR.exists():
                shutil.rmtree(CACHE_DIR)
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["git", "clone", "--depth=1", "--filter=blob:none", "--sparse", ECC_REPO, str(CACHE_DIR)],
                capture_output=True,
                timeout=120,
                check=True,
            )
            subprocess.run(
                ["git", "sparse-checkout", "set", "skills"],
                cwd=str(CACHE_DIR),
                capture_output=True,
                timeout=30,
                check=True,
            )

        _mark_fetched()
        skill_count = sum(1 for d in CACHE_SKILLS_DIR.iterdir() if d.is_dir()) if CACHE_SKILLS_DIR.exists() else 0
        console.print(f"  [green][OK][/green] {skill_count} skills cached")

    except subprocess.TimeoutExpired:
        console.print("  [yellow]Fetch timed out. Using cached skills if available.[/yellow]")
    except subprocess.CalledProcessError as e:
        console.print(f"  [yellow]Git error: {e}. Using cached skills if available.[/yellow]")
    except Exception as e:
        console.print(f"  [yellow]Fetch failed: {e}. Using cached skills if available.[/yellow]")

    return CACHE_SKILLS_DIR


def copy_skills_to_project(
    project_path: Path,
    config_dir: str,
    skill_names: list[str],
    force_fetch: bool = False,
) -> list[str]:
    """Fetch ECC skills and copy selected ones to project."""
    if not skill_names:
        return []

    source_skills = fetch_ecc_skills(force=force_fetch)
    if not source_skills.exists():
        console.print("  [yellow]No cached skills available.[/yellow]")
        return []

    dest_skills = project_path / config_dir / "skills"
    dest_skills.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    for name in skill_names:
        src = source_skills / name
        if not src.is_dir():
            continue
        dst = dest_skills / name
        shutil.copytree(src, dst, dirs_exist_ok=True)
        copied.append(name)

    return copied


def list_cached_skills() -> list[str]:
    """List all cached ECC skill names."""
    if not CACHE_SKILLS_DIR.exists():
        return []
    return sorted(d.name for d in CACHE_SKILLS_DIR.iterdir() if d.is_dir())
