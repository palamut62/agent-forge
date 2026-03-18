"""Project and skills scanner."""

import os
from pathlib import Path

# Proje tipi algilama kurallari
DETECTORS = {
    "python": ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile"],
    "node": ["package.json"],
    "go": ["go.mod"],
    "rust": ["Cargo.toml"],
    "java": ["pom.xml", "build.gradle"],
    "dotnet": ["*.csproj", "*.sln"],
}

# Framework algilama (dosya icerigi tarama)
FRAMEWORK_PATTERNS = {
    "fastapi": {"files": ["*.py"], "pattern": "fastapi"},
    "django": {"files": ["manage.py"], "pattern": "django"},
    "flask": {"files": ["*.py"], "pattern": "flask"},
    "react": {"files": ["package.json"], "pattern": "react"},
    "nextjs": {"files": ["package.json"], "pattern": "next"},
    "vue": {"files": ["package.json"], "pattern": "vue"},
    "svelte": {"files": ["package.json"], "pattern": "svelte"},
    "telegram-bot": {"files": ["*.py"], "pattern": "telebot|python-telegram-bot|aiogram|pyrogram"},
    "discord-bot": {"files": ["*.py", "*.js"], "pattern": "discord\\.py|discord\\.js"},
    "threejs": {"files": ["package.json", "*.js", "*.ts"], "pattern": "three"},
}


def scan_project(project_path: str) -> dict:
    """Proje klasorunu tara ve bilgi topla."""
    path = Path(project_path)
    result = {
        "path": str(path.absolute()),
        "name": path.name,
        "languages": [],
        "frameworks": [],
        "has_git": (path / ".git").exists(),
        "has_claude": (path / ".claude").exists(),
        "has_claude_md": (path / "CLAUDE.md").exists(),
        "has_memory": (path / "memory").exists(),
        "file_count": 0,
        "file_tree": [],
        "existing_skills": [],
        "existing_hooks": [],
        "existing_rules": [],
    }

    # Dil algilama
    for lang, markers in DETECTORS.items():
        for marker in markers:
            if "*" in marker:
                if list(path.glob(marker)):
                    result["languages"].append(lang)
                    break
            elif (path / marker).exists():
                result["languages"].append(lang)
                break

    # Framework algilama
    import re
    for fw, config in FRAMEWORK_PATTERNS.items():
        for file_pattern in config["files"]:
            for fp in path.glob(file_pattern):
                try:
                    content = fp.read_text(encoding="utf-8", errors="ignore")
                    if re.search(config["pattern"], content, re.IGNORECASE):
                        result["frameworks"].append(fw)
                        break
                except Exception:
                    continue
            if fw in result["frameworks"]:
                break

    # Dosya agaci (max 100 dosya, onemli olanlari)
    skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", ".next", "dist", "build"}
    count = 0
    for item in sorted(path.rglob("*")):
        if any(sd in item.parts for sd in skip_dirs):
            continue
        if item.is_file():
            count += 1
            if count <= 100:
                result["file_tree"].append(str(item.relative_to(path)))
    result["file_count"] = count

    # Mevcut Claude yapisini tara
    claude_dir = path / ".claude"
    if claude_dir.exists():
        skills_dir = claude_dir / "skills"
        if skills_dir.exists():
            result["existing_skills"] = [
                d.name for d in skills_dir.iterdir() if d.is_dir()
            ]
        hooks_dir = claude_dir / "hooks"
        if hooks_dir.exists():
            result["existing_hooks"] = [f.name for f in hooks_dir.iterdir() if f.is_file()]
        rules_dir = claude_dir / "rules"
        if rules_dir.exists():
            result["existing_rules"] = [f.name for f in rules_dir.iterdir() if f.is_file()]

    return result


def scan_available_skills(claude_home: str | None = None) -> dict:
    """Kullanicinin mevcut tum skill ve pluginlerini tara."""
    home = Path(claude_home or Path.home() / ".claude")
    result = {
        "global_skills": [],
        "plugin_skills": [],
        "plugin_agents": [],
        "plugin_commands": [],
    }

    # Global skills
    skills_dir = home / "skills"
    if skills_dir.exists():
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir():
                skill_md = skill_dir / "SKILL.md"
                if skill_md.exists():
                    desc = _extract_description(skill_md)
                    result["global_skills"].append({
                        "name": skill_dir.name,
                        "description": desc,
                        "path": str(skill_dir),
                    })
                else:
                    # Sadece isim olarak ekle
                    result["global_skills"].append({
                        "name": skill_dir.name,
                        "description": "",
                        "path": str(skill_dir),
                    })

    # Plugin cache
    cache_dir = home / "plugins" / "cache"
    if cache_dir.exists():
        for org_dir in cache_dir.iterdir():
            if not org_dir.is_dir():
                continue
            for plugin_dir in org_dir.iterdir():
                if not plugin_dir.is_dir():
                    continue
                # Her versiyon klasoru
                for ver_dir in plugin_dir.iterdir():
                    if not ver_dir.is_dir():
                        continue
                    # commands/ ve agents/ tara
                    for subdir_name, target_list_key in [
                        ("commands", "plugin_commands"),
                        ("agents", "plugin_agents"),
                    ]:
                        # Dogrudan altinda
                        subdir = ver_dir / subdir_name
                        if subdir.exists():
                            for md in subdir.glob("*.md"):
                                desc = _extract_description(md)
                                result[target_list_key].append({
                                    "name": md.stem,
                                    "plugin": plugin_dir.name,
                                    "org": org_dir.name,
                                    "description": desc,
                                })
                        # .claude/ altinda
                        subdir2 = ver_dir / ".claude" / subdir_name
                        if subdir2.exists():
                            for md in subdir2.glob("*.md"):
                                desc = _extract_description(md)
                                result[target_list_key].append({
                                    "name": md.stem,
                                    "plugin": plugin_dir.name,
                                    "org": org_dir.name,
                                    "description": desc,
                                })

    return result


def _extract_description(md_path: Path) -> str:
    """Markdown dosyasindan description satirini cek."""
    try:
        content = md_path.read_text(encoding="utf-8", errors="ignore")
        in_frontmatter = False
        for line in content.splitlines():
            if line.strip() == "---":
                in_frontmatter = not in_frontmatter
                continue
            if in_frontmatter and line.startswith("description:"):
                return line.split(":", 1)[1].strip().strip('"').strip("'")
        # Frontmatter yoksa ilk satiri al
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("---") and not line.startswith("#"):
                return line[:100]
    except Exception:
        pass
    return ""
