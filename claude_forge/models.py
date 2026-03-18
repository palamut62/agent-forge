"""OpenRouter model fetching and selection."""

import httpx
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

console = Console()

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"


def fetch_models(api_key: str | None = None) -> list[dict]:
    """OpenRouter'dan tum modelleri cek."""
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    with httpx.Client(timeout=15) as client:
        resp = client.get(OPENROUTER_MODELS_URL, headers=headers)
        resp.raise_for_status()
        return resp.json()["data"]


def filter_models(
    models: list[dict],
    free_only: bool = False,
    search: str | None = None,
) -> list[dict]:
    """Modelleri filtrele."""
    result = models

    if free_only:
        result = [
            m for m in result
            if m.get("pricing", {}).get("prompt", "0") == "0"
        ]

    if search:
        s = search.lower()
        result = [
            m for m in result
            if s in m["id"].lower() or s in m.get("name", "").lower()
        ]

    # Sirala: context length buyukten kucuge
    result.sort(key=lambda m: m.get("context_length", 0), reverse=True)
    return result


def display_models(models: list[dict], page_size: int = 20, start: int = 0) -> None:
    """Modelleri tablo olarak goster."""
    table = Table(title=f"OpenRouter Models ({len(models)} total)", show_lines=False)
    table.add_column("#", style="dim", width=4)
    table.add_column("Model ID", style="cyan", max_width=45)
    table.add_column("Context", justify="right", style="green", width=10)
    table.add_column("Prompt $", justify="right", style="yellow", width=12)
    table.add_column("Free?", justify="center", width=5)

    end = min(start + page_size, len(models))
    for i in range(start, end):
        m = models[i]
        ctx = f"{m.get('context_length', 0):,}"
        price = m.get("pricing", {}).get("prompt", "?")
        is_free = "[OK]" if price == "0" else ""
        table.add_row(str(i + 1), m["id"], ctx, str(price), is_free)

    console.print(table)
    if end < len(models):
        console.print(f"  [dim]({end}/{len(models)} shown -- 'n' for next page)[/dim]")


def select_model(models: list[dict]) -> str | None:
    """Interaktif model secimi."""
    page = 0
    page_size = 20

    while True:
        display_models(models, page_size=page_size, start=page * page_size)
        console.print()

        choice = Prompt.ask(
            "[bold]Select model[/bold] (number / 'n' next / 'p' prev / 'f' filter / 'q' quit)",
            default="q",
        )

        if choice.lower() == "q":
            return None
        elif choice.lower() == "n":
            if (page + 1) * page_size < len(models):
                page += 1
            else:
                console.print("[yellow]Last page.[/yellow]")
        elif choice.lower() == "p":
            if page > 0:
                page -= 1
            else:
                console.print("[yellow]First page.[/yellow]")
        elif choice.lower() == "f":
            search = Prompt.ask("Search (model name)", default="")
            free = Prompt.ask("Free only?", choices=["y", "n"], default="n")
            filtered = filter_models(models, free_only=(free == "y"), search=search or None)
            if not filtered:
                console.print("[red]No results found.[/red]")
                continue
            result = select_model(filtered)
            if result:
                return result
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(models):
                selected = models[idx]
                console.print(f"[green]Selected: {selected['id']}[/green]")
                return selected["id"]
            else:
                console.print("[red]Invalid number.[/red]")
