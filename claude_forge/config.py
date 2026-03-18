"""Configuration management."""

import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".claude-forge"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULTS = {
    "openrouter_api_key": "",
    "default_model": "",
    "claude_home": str(Path.home() / ".claude"),
}


def load_config() -> dict:
    """Config dosyasini oku."""
    if CONFIG_FILE.exists():
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return {**DEFAULTS, **data}
    return dict(DEFAULTS)


def save_config(config: dict) -> None:
    """Config dosyasini yaz."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(
        json.dumps(config, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def get_api_key(config: dict) -> str:
    """API key al -- config'den veya env'den."""
    import os
    return config.get("openrouter_api_key") or os.environ.get("OPENROUTER_API_KEY", "")
