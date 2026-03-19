# Agent Forge

Automated project setup tool for AI coding assistants (Claude Code, Codex, Antigravity).

When you create a new project or want to add an AI assistant to an existing one, Agent Forge automatically generates everything: CLAUDE.md, hooks, rules, memory structure, skill matching, and more.

## Features

### Core
- **Multi-target**: Claude Code, Codex, and Antigravity support
- **AI-powered analysis**: Analyzes your project via OpenRouter API and generates a custom setup plan
- **19 built-in profiles**: Python, JavaScript, Go, Rust, Swift, Kotlin, Flutter, and more
- **Auto tech stack detection**: pyproject.toml, package.json, go.mod, Cargo.toml, pubspec.yaml...

### Hook System (Maestro-inspired)
| Hook | Event | What It Does |
|------|-------|--------------|
| `protect-env.sh` | PreToolUse | Blocks .env file editing |
| `brain-sync.sh` | PostToolUse | Automatic memory logging after every tool use |
| `format.sh` | PostToolUse | Code formatting (ruff/eslint/gofmt...) |
| `session-start.sh` | SessionStart | Tech stack detection + brain summary |
| `pre-compact.sh` | PreCompact | Prevents context loss during compaction |
| `qa-gate.sh` | Stop | Quality checks (tests, TODOs, uncommitted changes) |

### Brain System
`memory/brain.jsonl` is automatically maintained by hooks:
- Errors and exceptions
- File changes (Edit/Write operations)
- Executed commands
- Context compaction summaries
- QA gate warnings

### Skill System (everything-claude-code)
Skills are automatically fetched from [everything-claude-code](https://github.com/affaan-m/everything-claude-code) — 170+ skills covering Python, JS, Go, Rust, Swift, Kotlin, Django, React, and more. Each profile includes a curated `skills_include` list; only relevant skills are copied to your project.

### MCP Server Integration
Agent Forge supports MCP (Model Context Protocol) server configuration across all targets. Example: [FreeWeb](https://github.com/xenitV1/freeweb) — a free web search/browse MCP server with no API keys required.

MCP servers are automatically configured for each target:
| Target | Config Location |
|--------|----------------|
| Claude Code | `~/.claude/.mcp.json` |
| Codex CLI | `~/.codex/config.toml` (`[mcp_servers.*]`) |
| Gemini / Antigravity | `~/.gemini/settings.json` |

### Advanced Features
- **Learning System**: Learn from mistakes, auto-apply rules to new projects
- **Profile System**: Create, apply, and extract profiles
- **Skill Navigator**: Recommends relevant skills from 170+ available
- **Codemap Generator**: Creates project structure maps
- **Cross-project Sync**: Transfer and compare setups between projects
- **Release Manager**: Version management, quality gates, smart push

## Requirements

- **Node.js 18+** (for the interactive TUI)
- **Python 3.10+** (backend)
- **Git** (for skill fetching)

## Installation

```bash
# Clone the repo
git clone https://github.com/palamut62/agent-forge.git
cd agent-forge

# Install dependencies
npm install
pip install -e .
```

## Usage

### Interactive mode
```bash
npx agent-forge
```

### Quick setup
```bash
npx agent-forge /path/to/project
```

### With specific target
```bash
npx agent-forge /path/to/project -t codex
```

### With profile (skip AI analysis)
```bash
npx agent-forge /path/to/project -p fastapi
```

### Run a specific flow
```bash
npx agent-forge --flow settings
npx agent-forge --flow scan-project
npx agent-forge --flow release
```

### Keyboard shortcuts (TUI)
| Key | Action |
|-----|--------|
| `Up/Down` or `j/k` | Navigate menu |
| `Enter` | Select |
| `Type` | Filter items |
| `/` | Command palette |
| `Esc` | Go back |
| `?` | Toggle help |
| `Ctrl+C` | Quit |

## Profiles

### Web
| Profile | Description |
|---------|-------------|
| `react` | React + TypeScript + Vite |
| `nextjs` | Next.js 14+ App Router + Tailwind + Prisma |
| `vue` | Vue 3 Composition API + Pinia |
| `express_node` | Node.js + Express/Fastify + TypeScript |
| `fullstack` | FastAPI backend + React frontend |

### Backend
| Profile | Description |
|---------|-------------|
| `fastapi` | FastAPI + Python async + SQLAlchemy |
| `django` | Django 5+ DRF + PostgreSQL |
| `springboot` | Java/Kotlin + Spring Boot 3 + JPA |
| `golang` | Go 1.22+ + chi/gin/echo |
| `rust` | Rust + tokio/actix + Cargo |

### Mobile
| Profile | Description |
|---------|-------------|
| `react_native` | React Native / Expo + TypeScript |
| `flutter` | Flutter/Dart + BLoC/Riverpod |
| `kotlin_android` | Kotlin + Jetpack Compose + MVVM + Hilt |
| `swift_ios` | Swift 6 + SwiftUI + async/await |

### Other
| Profile | Description |
|---------|-------------|
| `electron` | Electron + React + TypeScript |
| `telegram_bot` | Python Telegram bot |
| `cli_tool` | Python CLI (click/typer + rich) |
| `data_pipeline` | ETL pipeline (pandas/polars) |
| `base` | Common rules for all profiles |

## Generated File Structure

```
project/
├── CLAUDE.md                    # AI assistant guide (or AGENTS.md / ANTIGRAVITY.md)
├── .claude/                     # (or .codex/ / .antigravity/)
│   ├── settings.json            # Hook configuration
│   ├── hooks/
│   │   ├── protect-env.sh       # .env protection
│   │   ├── brain-sync.sh        # Automatic memory
│   │   ├── format.sh            # Code formatting
│   │   ├── session-start.sh     # Session startup
│   │   ├── pre-compact.sh       # Context preservation
│   │   └── qa-gate.sh           # Quality gate
│   ├── rules/                   # AI behavior rules
│   │   ├── no-env-edit.md
│   │   ├── git-safety.md
│   │   ├── code-quality.md
│   │   ├── brain-usage.md
│   │   └── (profile-specific rules)
│   ├── skills/                  # Copied skills
│   └── skill-profile.json       # Active skill list
└── memory/
    ├── MEMORY.md                # Main memory index
    ├── brain.jsonl              # Automatic operation log (managed by hooks)
    ├── debugging.md             # Debugging notes
    ├── preferences.md           # Working preferences
    └── (profile-specific memory files)
```

## Architecture

```
claude_forge/
├── cli.py              # Main CLI + TUI menus (click + prompt-toolkit)
├── config.py            # Global config (~/.agent-forge/config.json)
├── scanner.py           # Project analysis (language, framework detection)
├── analyzer.py          # AI analysis (OpenRouter API)
├── generator.py         # Setup file generation
├── targets.py           # Platform definitions (Claude/Codex/Antigravity)
├── learner.py           # Learning system
├── navigator.py         # Skill matching
├── mapper.py            # Codemap generation
├── context_manager.py   # Memory/context status
├── skill_fetcher.py     # ECC skill fetching and caching
├── sync.py              # Cross-project sync
├── release.py           # Version/release management
├── versioning.py        # Semver detection and bumping
├── models.py            # OpenRouter model management
├── tui.py               # Terminal UI (fullscreen menu)
├── hooks/               # Bundled hook files
│   ├── brain-sync.sh
│   ├── session-start.sh
│   ├── pre-compact.sh
│   └── qa-gate.sh
└── profiles/            # Profile system
    ├── schema.py        # Pydantic models
    ├── loader.py        # YAML profile loading
    ├── applicator.py    # Profile application
    ├── extractor.py     # Profile extraction from projects
    └── *.yaml           # 19 profile templates
```

## Configuration

Global config: `~/.agent-forge/config.json`

```json
{
  "openrouter_api_key": "sk-or-...",
  "default_model": "google/gemini-2.5-flash",
  "default_target": "claude"
}
```

## Requirements

- Python 3.10+
- Node.js 18+ (optional, for TUI launcher)

## License

MIT
