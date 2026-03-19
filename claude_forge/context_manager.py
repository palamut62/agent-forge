"""Context and memory management for projects."""

from pathlib import Path
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from .targets import get_target_platform

console = Console()


def context_status(project_path: Path, target: str = "claude") -> dict:
    """Memory ve context durumunu raporla."""
    project_path = Path(project_path)
    memory_dir = project_path / "memory"
    codemap_path = project_path / "docs" / "CODEMAP.md"
    target_platform = get_target_platform(target)

    result = {
        "memory_files": 0,
        "total_lines": 0,
        "has_codemap": codemap_path.exists(),
        "target_label": target_platform.label,
        "guide_file": target_platform.guide_file,
        "has_claude_md": (project_path / target_platform.guide_file).exists(),
        "files": [],
    }

    if memory_dir.exists():
        for f in sorted(memory_dir.iterdir()):
            if f.is_file():
                content = f.read_text(encoding="utf-8", errors="ignore")
                lines = len(content.splitlines())
                result["memory_files"] += 1
                result["total_lines"] += lines
                result["files"].append({
                    "name": f.name,
                    "lines": lines,
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                })
    return result


def display_context_status(project_path: Path, target: str = "claude") -> None:
    """Context durumunu goster."""
    status = context_status(project_path, target=target)

    table = Table(title="Context Status")
    table.add_column("Item", style="cyan")
    table.add_column("Status")
    table.add_column("Detail", style="dim")

    table.add_row(
        status["guide_file"],
        "[green]OK[/green]" if status["has_claude_md"] else "[red]YOK[/red]",
        "",
    )
    table.add_row(
        "Codemap",
        "[green]OK[/green]" if status["has_codemap"] else "[yellow]YOK[/yellow]",
        "agent-forge map ile olustur" if not status["has_codemap"] else "",
    )
    table.add_row(
        "Memory dosyalari",
        str(status["memory_files"]),
        f"{status['total_lines']} satir toplam",
    )
    console.print(table)

    if status["files"]:
        console.print("\n[bold]Memory Dosyalari:[/bold]")
        for f in status["files"]:
            console.print(
                f"  {f['name']:30s} {f['lines']:>5d} satir  [dim]{f['modified'][:10]}[/dim]"
            )


def context_compact_preview(project_path: Path, days: int = 30) -> list[dict]:
    """Eski memory dosyalarini tespit et (silmez, sadece rapor)."""
    project_path = Path(project_path)
    memory_dir = project_path / "memory"
    threshold = datetime.now() - timedelta(days=days)
    stale = []

    if not memory_dir.exists():
        return stale

    for f in sorted(memory_dir.iterdir()):
        if f.is_file():
            mod_time = datetime.fromtimestamp(f.stat().st_mtime)
            if mod_time < threshold:
                stale.append({
                    "name": f.name,
                    "modified": mod_time.isoformat(),
                    "days_old": (datetime.now() - mod_time).days,
                })
    return stale


def display_compact_preview(project_path: Path) -> None:
    """Compact preview goster."""
    stale = context_compact_preview(project_path)
    if not stale:
        console.print("[green]Eski memory dosyasi yok.[/green]")
        return
    console.print(f"\n[yellow]Eski Memory Dosyalari ({len(stale)}):[/yellow]")
    for f in stale:
        console.print(
            f"  [yellow]![/yellow] {f['name']:30s} {f['days_old']} gun once guncellendi"
        )
    console.print("\n[dim]Bu dosyalari silmek icin manuel olarak kaldirin.[/dim]")
