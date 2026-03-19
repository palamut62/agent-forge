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


def _get_skills_dest(project_path: Path, config_dir: str) -> Path:
    """Return the correct skills destination directory for the target.

    Codex uses .agents/skills/ per the official skill spec.
    Antigravity uses .agent/skills/ (singular) per Google docs.
    Claude uses .claude/skills/.
    """
    if config_dir == ".codex":
        return project_path / ".agents" / "skills"
    if config_dir == ".antigravity":
        return project_path / ".agent" / "skills"
    return project_path / config_dir / "skills"


def _convert_skill_for_codex(src_dir: Path, dst_dir: Path) -> None:
    """Copy a skill to Codex format: <skill>/SKILL.md + optional subdirs.

    ECC skills already have SKILL.md with frontmatter. This function ensures
    the directory structure matches Codex conventions:
      <skill-name>/
        SKILL.md          (required - instructions + frontmatter)
        scripts/           (optional - copied if exists)
        references/        (optional - copied if exists)
        assets/            (optional - copied if exists)
    """
    dst_dir.mkdir(parents=True, exist_ok=True)

    # Find the main skill markdown file
    skill_md = src_dir / "SKILL.md"
    if not skill_md.exists():
        # Some ECC skills might use different names — find the first .md
        md_files = list(src_dir.glob("*.md"))
        if not md_files:
            return
        skill_md = md_files[0]

    # Read content and ensure proper frontmatter
    content = skill_md.read_text(encoding="utf-8", errors="ignore")
    if not content.startswith("---"):
        # Add frontmatter from directory name
        name = src_dir.name
        content = f"---\nname: {name}\ndescription: {name} skill\n---\n\n{content}"

    (dst_dir / "SKILL.md").write_text(content, encoding="utf-8")

    # Copy optional subdirectories (Codex: references/, Antigravity: resources/)
    for subdir in ("scripts", "references", "resources", "assets", "examples"):
        src_sub = src_dir / subdir
        if src_sub.is_dir():
            shutil.copytree(src_sub, dst_dir / subdir, dirs_exist_ok=True)


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

    dest_skills = _get_skills_dest(project_path, config_dir)
    dest_skills.mkdir(parents=True, exist_ok=True)
    use_skill_md_format = config_dir in (".codex", ".antigravity")

    copied: list[str] = []
    for name in skill_names:
        src = source_skills / name
        if not src.is_dir():
            continue
        dst = dest_skills / name
        if use_skill_md_format:
            _convert_skill_for_codex(src, dst)
        else:
            shutil.copytree(src, dst, dirs_exist_ok=True)
        copied.append(name)

    return copied


def list_cached_skills() -> list[str]:
    """List all cached ECC skill names."""
    if not CACHE_SKILLS_DIR.exists():
        return []
    return sorted(d.name for d in CACHE_SKILLS_DIR.iterdir() if d.is_dir())
