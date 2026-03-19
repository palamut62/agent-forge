"""MCP server definitions and config generation per target."""

import json
from pathlib import Path
from .targets import TargetPlatform

# Default MCP servers included in every setup
DEFAULT_MCP_SERVERS: dict[str, dict] = {
    "freeweb": {
        "command": "npx",
        "args": ["-y", "github:xenitV1/freeweb"],
        "description": "Free web search/browse — no API keys needed",
    },
    "memory": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-memory"],
        "description": "Persistent memory for LLM sessions",
    },
}


def get_mcp_servers(extra: dict[str, dict] | None = None) -> dict[str, dict]:
    """Merge default MCP servers with any extras."""
    servers = dict(DEFAULT_MCP_SERVERS)
    if extra:
        servers.update(extra)
    return servers


def _server_entry(server: dict) -> dict:
    """Strip description from server dict for config output."""
    return {k: v for k, v in server.items() if k != "description"}


def generate_mcp_config(
    target: TargetPlatform,
    project_path: Path,
    extra_servers: dict[str, dict] | None = None,
) -> str | None:
    """Generate MCP config file content for the given target.

    Returns the file content as string, or None if no servers.
    """
    servers = get_mcp_servers(extra_servers)
    if not servers:
        return None

    if target.mcp_config_format == "toml":
        return _generate_toml(servers)
    elif target.key == "antigravity":
        return _generate_antigravity_json(servers)
    else:
        return _generate_claude_json(servers)


def _generate_claude_json(servers: dict[str, dict]) -> str:
    """Claude Code .mcp.json format."""
    config = {
        "mcpServers": {
            name: _server_entry(srv) for name, srv in servers.items()
        }
    }
    return json.dumps(config, indent=2, ensure_ascii=False)


def _generate_antigravity_json(servers: dict[str, dict]) -> str:
    """Antigravity: mcpServers inside settings.json (partial, to be merged)."""
    config = {
        "mcpServers": {
            name: _server_entry(srv) for name, srv in servers.items()
        }
    }
    return json.dumps(config, indent=2, ensure_ascii=False)


def _generate_toml(servers: dict[str, dict]) -> str:
    """Codex config.toml [mcp_servers.*] format."""
    lines: list[str] = []
    for name, srv in servers.items():
        lines.append(f"[mcp_servers.{name}]")
        lines.append(f'command = "{srv["command"]}"')
        args = ", ".join(f'"{a}"' for a in srv.get("args", []))
        lines.append(f"args = [{args}]")
        if "env" in srv:
            for k, v in srv["env"].items():
                lines.append(f'env.{k} = "{v}"')
        lines.append("")
    return "\n".join(lines)


def write_mcp_config(
    target: TargetPlatform,
    project_path: Path,
    extra_servers: dict[str, dict] | None = None,
) -> Path | None:
    """Write MCP config to the appropriate file for the target.

    Returns the written file path, or None.
    """
    content = generate_mcp_config(target, project_path, extra_servers)
    if not content:
        return None

    config_dir = project_path / target.config_dir

    if target.key == "claude":
        # Claude: .mcp.json at project root (project-scope MCP)
        out = project_path / target.mcp_config_file
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        return out

    elif target.key == "codex":
        # Codex: append [mcp_servers.*] sections to config.toml
        out = config_dir / target.mcp_config_file
        out.parent.mkdir(parents=True, exist_ok=True)
        existing = ""
        if out.exists():
            existing = out.read_text(encoding="utf-8")
        if "[mcp_servers." not in existing:
            with open(out, "a", encoding="utf-8") as f:
                f.write("\n" + content)
        return out

    elif target.key == "antigravity":
        # Antigravity: mcp_config.json inside .antigravity/
        out = config_dir / target.mcp_config_file
        out.parent.mkdir(parents=True, exist_ok=True)
        existing: dict = {}
        if out.exists():
            try:
                existing = json.loads(out.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        mcp_config = json.loads(content)
        existing.setdefault("mcpServers", {}).update(mcp_config["mcpServers"])
        out.write_text(
            json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return out

    return None
