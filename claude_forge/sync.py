"""Cross-project setup sync -- export, import, diff."""

import json
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt
from .targets import get_target_platform

console = Console()


def export_project(project_path: Path, target: str = "claude") -> dict:
    """Projenin .claude/ setup'ini JSON olarak disa aktar."""
    project_path = Path(project_path)
    target_platform = get_target_platform(target)
    result = {
        "exported_at": datetime.now().isoformat(),
        "source_project": project_path.name,
        "target": target_platform.key,
        "rules": [],
        "hooks": [],
        "memory_files": [],
    }

    rules_dir = project_path / target_platform.config_dir / "rules"
    if rules_dir.exists():
        for f in sorted(rules_dir.iterdir()):
            if f.is_file():
                result["rules"].append({
                    "name": f.name,
                    "content": f.read_text(encoding="utf-8", errors="ignore"),
                })

    hooks_dir = project_path / target_platform.config_dir / "hooks"
    if hooks_dir.exists():
        for f in sorted(hooks_dir.iterdir()):
            if f.is_file():
                result["hooks"].append({
                    "name": f.name,
                    "content": f.read_text(encoding="utf-8", errors="ignore"),
                })

    memory_dir = project_path / "memory"
    if memory_dir.exists():
        for f in sorted(memory_dir.iterdir()):
            if f.is_file():
                result["memory_files"].append({
                    "name": f.name,
                    "content": f.read_text(encoding="utf-8", errors="ignore"),
                })

    guide = project_path / target_platform.guide_file
    if guide.exists():
        result["guide_content"] = guide.read_text(encoding="utf-8", errors="ignore")

    sp = project_path / target_platform.config_dir / target_platform.skill_profile_file
    if sp.exists():
        try:
            result["skill_profile"] = json.loads(sp.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    return result


def import_project(
    project_path: Path,
    export_path: Path,
    interactive: bool = True,
    target: str | None = None,
) -> dict:
    """Export dosyasindan projeye setup al."""
    project_path = Path(project_path)
    data = json.loads(Path(export_path).read_text(encoding="utf-8"))
    target_platform = get_target_platform(target or data.get("target"))
    stats = {"rules_imported": 0, "hooks_imported": 0, "memory_imported": 0, "skipped": 0}

    rules_dir = project_path / target_platform.config_dir / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)
    for rule in data.get("rules", []):
        target = rules_dir / rule["name"]
        if _should_write(target, rule["content"], interactive):
            target.write_text(rule["content"], encoding="utf-8")
            stats["rules_imported"] += 1
            console.print(f"  [green][OK][/green] rule: {rule['name']}")
        else:
            stats["skipped"] += 1

    hooks_dir = project_path / target_platform.config_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    for hook in data.get("hooks", []):
        target = hooks_dir / hook["name"]
        if _should_write(target, hook["content"], interactive):
            with open(target, "w", encoding="utf-8", newline="\n") as f:
                f.write(hook["content"])
            try:
                target.chmod(0o755)
            except OSError:
                pass
            stats["hooks_imported"] += 1
            console.print(f"  [green][OK][/green] hook: {hook['name']}")
        else:
            stats["skipped"] += 1

    guide_content = data.get("guide_content")
    if guide_content:
        guide_file = project_path / target_platform.guide_file
        if _should_write(guide_file, guide_content, interactive):
            guide_file.write_text(guide_content, encoding="utf-8")
            console.print(f"  [green][OK][/green] guide: {target_platform.guide_file}")

    memory_dir = project_path / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    for mem in data.get("memory_files", []):
        target = memory_dir / mem["name"]
        if _should_write(target, mem["content"], interactive):
            target.write_text(mem["content"], encoding="utf-8")
            stats["memory_imported"] += 1
        else:
            stats["skipped"] += 1

    return stats


def _should_write(target: Path, new_content: str, interactive: bool) -> bool:
    if not target.exists():
        return True
    existing = target.read_text(encoding="utf-8", errors="ignore")
    if existing == new_content:
        return False
    if not interactive:
        return True
    console.print(f"\n[yellow]Cakisma: {target.name}[/yellow]")
    console.print(f"  Mevcut: {existing[:100]}...")
    console.print(f"  Yeni:   {new_content[:100]}...")
    choice = Prompt.ask("  [K]aynak / [H]edef / [A]tla", default="A")
    return choice.upper() == "K"


def diff_projects(path1: Path, path2: Path, target: str = "claude") -> dict:
    """Iki projenin .claude/ setup'ini karsilastir."""
    target_platform = get_target_platform(target)
    files1 = _collect_setup_files(path1, target_platform)
    files2 = _collect_setup_files(path2, target_platform)
    result = {"only_in_p1": [], "only_in_p2": [], "different": [], "same": []}

    all_names = set(files1.keys()) | set(files2.keys())
    for name in sorted(all_names):
        if name in files1 and name not in files2:
            result["only_in_p1"].append(name)
        elif name not in files1 and name in files2:
            result["only_in_p2"].append(name)
        elif files1[name] == files2[name]:
            result["same"].append(name)
        else:
            result["different"].append(name)
    return result


def _collect_setup_files(project_path: Path, target_platform) -> dict[str, str]:
    files = {}
    for subdir in [f"{target_platform.config_dir}/rules", f"{target_platform.config_dir}/hooks", "memory"]:
        d = Path(project_path) / subdir
        if d.exists():
            for f in d.iterdir():
                if f.is_file():
                    key = f"{subdir}/{f.name}"
                    files[key] = f.read_text(encoding="utf-8", errors="ignore")
    return files


def display_diff(diff: dict, name1: str, name2: str) -> None:
    if diff["only_in_p1"]:
        console.print(f"\n[cyan]Sadece {name1}:[/cyan]")
        for f in diff["only_in_p1"]:
            console.print(f"  + {f}")
    if diff["only_in_p2"]:
        console.print(f"\n[yellow]Sadece {name2}:[/yellow]")
        for f in diff["only_in_p2"]:
            console.print(f"  + {f}")
    if diff["different"]:
        console.print("\n[red]Farkli:[/red]")
        for f in diff["different"]:
            console.print(f"  ~ {f}")
    if diff["same"]:
        console.print(f"\n[green]Ayni: {len(diff['same'])} dosya[/green]")
