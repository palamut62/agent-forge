"""Skill Navigator -- projeye uygun skill'leri filtrele ve oner."""

import json
from pathlib import Path
from rich.console import Console
from .scanner import scan_available_skills
from .config import load_config, CONFIG_DIR, LEGACY_CONFIG_DIR
from .targets import get_target_home, normalize_target

console = Console()

CACHE_FILE = CONFIG_DIR / "skill_registry.json"
LEGACY_CACHE_FILE = LEGACY_CONFIG_DIR / "skill_registry.json"

KEYWORD_TAGS = {
    "python": ["python"],
    "go": ["go", "golang"],
    "golang": ["go", "golang"],
    "kotlin": ["kotlin", "android"],
    "swift": ["swift", "ios", "apple"],
    "java": ["java"],
    "react": ["react", "frontend", "javascript", "typescript"],
    "next.js": ["react", "nextjs", "frontend"],
    "vue": ["vue", "frontend", "javascript"],
    "threejs": ["threejs", "3d", "javascript"],
    "fastapi": ["python", "fastapi", "api", "backend"],
    "django": ["python", "django", "backend"],
    "flask": ["python", "flask", "backend"],
    "telegram": ["python", "bot", "telegram"],
    "discord": ["bot", "discord"],
    "docker": ["docker", "deployment"],
    "postgres": ["postgres", "database", "sql"],
    "sql": ["database", "sql"],
    "test": ["testing"],
    "tdd": ["testing", "tdd"],
    "security": ["security"],
    "api": ["api", "backend"],
    "frontend": ["frontend"],
    "backend": ["backend"],
    "perl": ["perl"],
    "rust": ["rust"],
    "spring": ["java", "springboot"],
    "android": ["kotlin", "android"],
    "ios": ["swift", "ios"],
    "compose": ["kotlin", "android", "compose"],
}


def build_registry(home_dir: str | None = None, target: str = "claude") -> dict:
    """Tum skill'leri tara ve tag'li registry olustur."""
    config = load_config()
    resolved_target = normalize_target(target or config.get("default_target"))
    skills_info = scan_available_skills(home_dir or get_target_home(config, resolved_target), target=resolved_target)
    registry: dict = {}

    for s in skills_info["global_skills"]:
        tags = _extract_tags(s["name"], s.get("description", ""))
        registry[s["name"]] = {
            "description": s.get("description", ""),
            "tags": tags,
            "source": "global",
        }

    for s in skills_info["plugin_commands"]:
        full_name = f"{s['plugin']}:{s['name']}" if s.get("plugin") else s["name"]
        tags = _extract_tags(s["name"], s.get("description", ""))
        registry[full_name] = {
            "description": s.get("description", ""),
            "tags": tags,
            "source": f"plugin:{s.get('org', '')}",
        }

    for s in skills_info["plugin_agents"]:
        full_name = f"{s['plugin']}:{s['name']}"
        tags = _extract_tags(s["name"], s.get("description", ""))
        registry[full_name] = {
            "description": s.get("description", ""),
            "tags": tags,
            "source": f"agent:{s.get('org', '')}",
        }

    _save_cache(registry)
    return registry


def _extract_tags(name: str, description: str) -> list[str]:
    """Isim ve description'dan tag cikar."""
    tags: set[str] = set()
    text = f"{name} {description}".lower()
    for keyword, keyword_tags in KEYWORD_TAGS.items():
        if keyword in text:
            tags.update(keyword_tags)
    return sorted(tags)


def _save_cache(registry: dict) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(
        json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def load_registry() -> dict:
    """Cache'ten yukle, yoksa olustur."""
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    if LEGACY_CACHE_FILE.exists():
        return json.loads(LEGACY_CACHE_FILE.read_text(encoding="utf-8"))
    return build_registry()


def match_skills(
    registry: dict,
    languages: list[str],
    frameworks: list[str],
) -> dict[str, list]:
    """Projeye uygun skill'leri 3 gruba ayir."""
    project_tags: set[str] = set()
    for lang in languages:
        project_tags.update(KEYWORD_TAGS.get(lang, [lang]))
    for fw in frameworks:
        project_tags.update(KEYWORD_TAGS.get(fw, [fw]))

    recommended = []
    optional = []
    irrelevant = []

    for name, entry in registry.items():
        skill_tags = set(entry.get("tags", []))
        overlap = skill_tags & project_tags
        score = len(overlap)
        item = {
            "name": name,
            "description": entry["description"],
            "score": score,
            "tags": entry["tags"],
        }
        if score >= 2:
            recommended.append(item)
        elif score == 1:
            optional.append(item)
        else:
            irrelevant.append(item)

    recommended.sort(key=lambda x: x["score"], reverse=True)
    optional.sort(key=lambda x: x["score"], reverse=True)
    return {"recommended": recommended, "optional": optional, "irrelevant": irrelevant}


def display_skill_analysis(result: dict, project_name: str = "") -> None:
    """Skill analiz sonucunu goster."""
    console.print(f"\n[bold]Skill Analizi: {project_name}[/bold]")

    if result["recommended"]:
        console.print(f"\n[green bold]Onerilen ({len(result['recommended'])}):[/green bold]")
        for s in result["recommended"]:
            console.print(f"  [green]+[/green] {s['name']:40s} {s['description'][:60]}")

    if result["optional"]:
        console.print(f"\n[yellow bold]Opsiyonel ({len(result['optional'])}):[/yellow bold]")
        for s in result["optional"][:10]:
            console.print(f"  [yellow]~[/yellow] {s['name']:40s} {s['description'][:60]}")

    console.print(f"\n[dim]Ilgisiz: {len(result['irrelevant'])} skill[/dim]")
