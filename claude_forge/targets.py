"""Target platform definitions for generated agent setups."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TargetPlatform:
    key: str
    label: str
    config_dir: str
    guide_file: str
    settings_file: str
    local_settings_file: str
    skill_profile_file: str
    default_home_dir: str
    mcp_config_file: str = ""
    mcp_config_format: str = "json"  # "json" or "toml"


TARGETS: dict[str, TargetPlatform] = {
    "claude": TargetPlatform(
        key="claude",
        label="Claude Code",
        config_dir=".claude",
        guide_file="CLAUDE.md",
        settings_file="settings.json",
        local_settings_file="settings.local.json",
        skill_profile_file="skill-profile.json",
        default_home_dir=".claude",
        mcp_config_file=".mcp.json",
        mcp_config_format="json",
    ),
    "codex": TargetPlatform(
        key="codex",
        label="Codex",
        config_dir=".codex",
        guide_file="AGENTS.md",
        settings_file="settings.json",
        local_settings_file="settings.local.json",
        skill_profile_file="skill-profile.json",
        default_home_dir=".codex",
        mcp_config_file="config.toml",
        mcp_config_format="toml",
    ),
    "antigravity": TargetPlatform(
        key="antigravity",
        label="Antigravity",
        config_dir=".antigravity",
        guide_file="GEMINI.md",
        settings_file="settings.json",
        local_settings_file="settings.local.json",
        skill_profile_file="skill-profile.json",
        default_home_dir=".gemini/antigravity",
        mcp_config_file="mcp_config.json",
        mcp_config_format="json",
    ),
}


def normalize_target(value: str | None) -> str:
    """Normalize user input to one of the supported target keys."""
    if not value:
        return "claude"

    normalized = value.strip().lower().replace(" ", "").replace("-", "")
    aliases = {
        "claude": "claude",
        "claudecode": "claude",
        "codex": "codex",
        "openaicodex": "codex",
        "antigravity": "antigravity",
        "antşgravşty": "antigravity",
        "antgravity": "antigravity",
    }
    return aliases.get(normalized, "claude")


def get_target_platform(value: str | None) -> TargetPlatform:
    """Return the resolved target platform config."""
    return TARGETS[normalize_target(value)]


def get_target_home(config: dict, value: str | None = None) -> str:
    """Resolve the selected target's home directory from config."""
    target = get_target_platform(value or config.get("default_target"))
    home_key = f"{target.key}_home"
    return config.get(home_key) or str(Path.home() / target.default_home_dir)
