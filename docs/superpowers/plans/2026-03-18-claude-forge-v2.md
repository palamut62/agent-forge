# Claude Forge v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** claude-forge'a 4 yeni modül ekle: Profile System, Skill Navigator, Big Project Module, Cross-Project Sync

**Architecture:** Mevcut click CLI'a yeni komut grupları eklenir. Her modül bağımsız bir Python dosyası. Profiller YAML, pydantic ile validate. Mevcut scanner.py ve learner.py genişletilir.

**Tech Stack:** Python 3.12, click, rich, httpx, PyYAML, pydantic

---

## Ön Hazırlık

### Task 0: Dependency Ekleme

**Files:**
- Modify: `pyproject.toml`
- Modify: `claude_forge/__init__.py`

- [ ] **Step 1: pyproject.toml'a pyyaml ve pydantic ekle**

```toml
dependencies = [
    "click>=8.1",
    "httpx>=0.27",
    "rich>=13.0",
    "pyyaml>=6.0",
    "pydantic>=2.0",
]
```

- [ ] **Step 2: Versiyonu 0.2.0 yap**

`pyproject.toml`'da `version = "0.2.0"`, `__init__.py`'da `__version__ = "0.2.0"`, `cli.py` BANNER'da `v0.2.0`

- [ ] **Step 3: Dependency'leri kur**

Run: `pip install -e "C:\Users\umuti\Desktop\deneembos\my_claude_code_setup[dev]"`

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml claude_forge/__init__.py claude_forge/cli.py
git commit -m "dep: pyyaml ve pydantic ekle, v0.2.0"
```

---

## Modül 1: Profile System

### Task 1: Profile Schema (pydantic model)

**Files:**
- Create: `claude_forge/profiles/__init__.py`
- Create: `claude_forge/profiles/schema.py`
- Create: `tests/test_profiles.py`

- [ ] **Step 1: Test yaz — ProfileSchema validasyonu**

```python
# tests/test_profiles.py
import pytest
from claude_forge.profiles.schema import ProfileSchema, HookEntry, RuleEntry, MemoryTemplate


def test_valid_profile():
    data = {
        "version": 1,
        "name": "test",
        "description": "Test profile",
        "languages": ["python"],
        "frameworks": ["fastapi"],
        "claude_md": {
            "tech_stack": "Python 3.12",
            "coding_standards": "- Type hints",
            "test_command": "pytest",
            "lint_command": "ruff check",
        },
        "hooks": [{"name": "format.sh", "event": "PostToolUse", "matcher": "Edit", "command": "ruff format"}],
        "rules": [{"name": "async-io.md", "content": "Use async"}],
        "skills_include": ["tdd-workflow"],
        "skills_exclude": ["threejs-*"],
        "memory_templates": [{"name": "arch.md", "content": "# Arch"}],
    }
    profile = ProfileSchema(**data)
    assert profile.name == "test"
    assert profile.version == 1


def test_minimal_profile():
    profile = ProfileSchema(name="min", description="Minimal")
    assert profile.languages == []
    assert profile.hooks == []


def test_invalid_profile_no_name():
    with pytest.raises(Exception):
        ProfileSchema(description="No name")


def test_invalid_profile_bad_version():
    with pytest.raises(Exception):
        ProfileSchema(name="x", description="x", version=99)
```

- [ ] **Step 2: Test fail ettiğini doğrula**

Run: `python -m pytest tests/test_profiles.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: Schema yaz**

```python
# claude_forge/profiles/__init__.py
"""Profile system for Claude Forge."""

# claude_forge/profiles/schema.py
"""Profile schema with pydantic validation."""

from pydantic import BaseModel, Field


class HookEntry(BaseModel):
    name: str
    event: str = "PostToolUse"
    matcher: str = "Edit|Write"
    command: str


class RuleEntry(BaseModel):
    name: str
    content: str


class MemoryTemplate(BaseModel):
    name: str
    content: str


class ClaudeMdConfig(BaseModel):
    tech_stack: str = ""
    coding_standards: str = ""
    test_command: str = ""
    lint_command: str = ""
    extra_sections: dict[str, str] = Field(default_factory=dict)


class ProfileSchema(BaseModel):
    version: int = Field(default=1, le=1, ge=1)
    name: str
    description: str
    extends: str | None = None
    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    claude_md: ClaudeMdConfig = Field(default_factory=ClaudeMdConfig)
    hooks: list[HookEntry] = Field(default_factory=list)
    rules: list[RuleEntry] = Field(default_factory=list)
    skills_include: list[str] = Field(default_factory=list)
    skills_exclude: list[str] = Field(default_factory=list)
    memory_templates: list[MemoryTemplate] = Field(default_factory=list)
```

- [ ] **Step 4: Test geçtiğini doğrula**

Run: `python -m pytest tests/test_profiles.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add claude_forge/profiles/ tests/test_profiles.py
git commit -m "feat: profil schema modeli ekle"
```

### Task 2: Profile Loader (YAML okuma + extends)

**Files:**
- Create: `claude_forge/profiles/loader.py`
- Modify: `tests/test_profiles.py`

- [ ] **Step 1: Test yaz — YAML yükleme ve extends**

```python
# tests/test_profiles.py'a ekle
from claude_forge.profiles.loader import load_profile, list_profiles, get_builtin_profiles_dir
from pathlib import Path
import tempfile
import yaml


def test_load_builtin_profile():
    """base.yaml yüklenebilmeli."""
    profile = load_profile("base")
    assert profile.name == "base"


def test_list_builtin_profiles():
    profiles = list_profiles()
    assert "base" in profiles


def test_extends_merging(tmp_path):
    """Child profil, parent'tan hook/rule devralmalı."""
    base = {
        "version": 1,
        "name": "parent",
        "description": "Parent",
        "rules": [{"name": "r1.md", "content": "rule 1"}],
    }
    child = {
        "version": 1,
        "name": "child",
        "description": "Child",
        "extends": "parent",
        "rules": [{"name": "r2.md", "content": "rule 2"}],
    }
    (tmp_path / "parent.yaml").write_text(yaml.dump(base))
    (tmp_path / "child.yaml").write_text(yaml.dump(child))

    profile = load_profile("child", extra_dirs=[tmp_path])
    assert len(profile.rules) == 2  # parent r1 + child r2


def test_load_nonexistent_profile():
    with pytest.raises(FileNotFoundError):
        load_profile("nonexistent_xyz_123")
```

- [ ] **Step 2: Test fail ettiğini doğrula**

Run: `python -m pytest tests/test_profiles.py::test_load_builtin_profile -v`
Expected: FAIL

- [ ] **Step 3: Loader yaz**

```python
# claude_forge/profiles/loader.py
"""Load and merge YAML profiles."""

import yaml
from pathlib import Path
from .schema import ProfileSchema

BUILTIN_DIR = Path(__file__).parent


def get_builtin_profiles_dir() -> Path:
    return BUILTIN_DIR


def list_profiles(extra_dirs: list[Path] | None = None) -> list[str]:
    """Mevcut profil isimlerini listele."""
    names = []
    dirs = [BUILTIN_DIR] + (extra_dirs or [])
    for d in dirs:
        for f in d.glob("*.yaml"):
            names.append(f.stem)
    return sorted(set(names))


def _find_profile_file(name: str, extra_dirs: list[Path] | None = None) -> Path:
    dirs = [BUILTIN_DIR] + (extra_dirs or [])
    for d in dirs:
        p = d / f"{name}.yaml"
        if p.exists():
            return p
    raise FileNotFoundError(f"Profil bulunamadı: {name}")


def load_profile(name: str, extra_dirs: list[Path] | None = None) -> ProfileSchema:
    """Profili yükle, extends varsa parent ile birleştir."""
    path = _find_profile_file(name, extra_dirs)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    extends = data.get("extends")
    if extends:
        parent = load_profile(extends, extra_dirs)
        data = _merge_profiles(parent.model_dump(), data)

    return ProfileSchema(**data)


def _merge_profiles(parent: dict, child: dict) -> dict:
    """Child, parent'ın üstüne yazılır. Listeler birleştirilir."""
    merged = dict(parent)
    for key, value in child.items():
        if key == "extends":
            continue
        if isinstance(value, list) and isinstance(merged.get(key), list):
            # Parent listenin üstüne child ekle (dedup name ile)
            existing_names = {item.get("name") if isinstance(item, dict) else item for item in value}
            parent_items = [item for item in merged[key]
                          if (item.get("name") if isinstance(item, dict) else item) not in existing_names]
            merged[key] = parent_items + value
        elif isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged
```

- [ ] **Step 4: base.yaml oluştur**

```yaml
# claude_forge/profiles/base.yaml
version: 1
name: base
description: "Tüm projelere ortak temel kurallar"
languages: []
frameworks: []

claude_md:
  coding_standards: |
    - Type hints zorunlu
    - Fonksiyonlar max 30 satir
    - console.log/print birakma, logger kullan
  test_command: ""
  lint_command: ""

hooks:
  - name: protect-env.sh
    event: PreToolUse
    matcher: "Edit|Write"
    command: "bash .claude/hooks/protect-env.sh"

rules:
  - name: no-env-edit.md
    content: |
      ---
      description: .env dosyalarini asla duzenleme
      ---
      .env dosyalarini asla duzenleme. Sadece .env.example duzenlenebilir.
  - name: git-safety.md
    content: |
      ---
      description: Git guvenlik kurallari
      ---
      - main/master branch'e direkt push yapma
      - Force push kullanma
      - Commit oncesi lint ve test calistir

skills_include: []
skills_exclude: []

memory_templates:
  - name: MEMORY.md
    content: |
      # Project Memory -- Routing
      Last updated: -
      ## Critical Notes
      - (none yet)
  - name: debugging.md
    content: |
      # Debugging Log
      _(No entries yet)_
  - name: preferences.md
    content: |
      # Working Preferences
      _(No entries yet)_
```

- [ ] **Step 5: Test geçtiğini doğrula**

Run: `python -m pytest tests/test_profiles.py -v`
Expected: 8 passed

- [ ] **Step 6: Commit**

```bash
git add claude_forge/profiles/ tests/test_profiles.py
git commit -m "feat: profil loader ve base.yaml ekle"
```

### Task 3: Hazır Profiller (fastapi, react, telegram_bot, cli_tool)

**Files:**
- Create: `claude_forge/profiles/fastapi.yaml`
- Create: `claude_forge/profiles/react.yaml`
- Create: `claude_forge/profiles/telegram_bot.yaml`
- Create: `claude_forge/profiles/cli_tool.yaml`
- Create: `claude_forge/profiles/data_pipeline.yaml`
- Create: `claude_forge/profiles/fullstack.yaml`

- [ ] **Step 1: fastapi.yaml**

```yaml
version: 1
name: fastapi
description: "FastAPI + Python async projesi"
extends: base
languages: [python]
frameworks: [fastapi]

claude_md:
  tech_stack: "Python 3.12, FastAPI, httpx, pydantic, SQLAlchemy, alembic"
  coding_standards: |
    - Type hints zorunlu
    - async/await tercih et (I/O-bound islemler)
    - Pydantic model kullan (raw dict degil)
    - httpx.AsyncClient kullan (requests degil)
    - Router'lari routes/ altinda topla
    - Business logic services/ altinda
  test_command: "pytest tests/ -v"
  lint_command: "ruff check --fix && ruff format"

hooks:
  - name: format.sh
    event: PostToolUse
    matcher: "Edit|Write"
    command: "bash .claude/hooks/format.sh"

rules:
  - name: async-io.md
    content: |
      ---
      description: I/O islemlerinde async kullan
      ---
      I/O islemlerinde her zaman async/await kullan.
      requests yerine httpx.AsyncClient.
      time.sleep yerine asyncio.sleep.
  - name: pydantic-models.md
    content: |
      ---
      description: API modelleri icin pydantic kullan
      ---
      API request/response icin Pydantic model kullan.
      Raw dict donme, her zaman tipli model kullan.

skills_include:
  - tdd-workflow
  - security-review
  - api-design
  - python-review
  - python-patterns
  - python-testing
  - postgres-patterns
  - docker-patterns

skills_exclude:
  - "threejs-*"
  - "kotlin-*"
  - "swift-*"
  - "golang-*"
  - "perl-*"
  - "springboot-*"
  - "jpa-*"

memory_templates:
  - name: architecture.md
    content: |
      # Mimari Kararlar
      _(Buraya ekle)_
  - name: api-contracts.md
    content: |
      # API Sozlesmeleri
      _(Buraya ekle)_
```

- [ ] **Step 2: react.yaml**

```yaml
version: 1
name: react
description: "React + TypeScript projesi"
extends: base
languages: [node]
frameworks: [react]

claude_md:
  tech_stack: "React 18+, TypeScript, Vite/Next.js"
  coding_standards: |
    - TypeScript strict mode
    - No any type
    - Functional components + hooks
    - CSS Modules veya Tailwind
  test_command: "npm test"
  lint_command: "npx eslint --fix . && npx prettier --write ."

rules:
  - name: no-any.md
    content: |
      ---
      description: any type kullanma
      ---
      TypeScript'te asla `any` type kullanma. `unknown` veya spesifik tip kullan.

skills_include:
  - frontend-patterns
  - vercel-react-best-practices
  - web-design-guidelines
  - tdd-workflow
  - security-review

skills_exclude:
  - "python-*"
  - "django-*"
  - "fastapi-*"
  - "golang-*"
  - "kotlin-*"
  - "swift-*"
  - "perl-*"
  - "springboot-*"
```

- [ ] **Step 3: telegram_bot.yaml**

```yaml
version: 1
name: telegram_bot
description: "Python Telegram bot projesi"
extends: base
languages: [python]
frameworks: [telegram-bot]

claude_md:
  tech_stack: "Python 3.12, python-telegram-bot/aiogram, httpx, loguru"
  coding_standards: |
    - async handler'lar kullan
    - Komut handler'larini ayri dosyalarda tut
    - Conversation state'leri duzgun yonet
    - Hata mesajlarini kullaniciya Turkce goster
  test_command: "pytest tests/ -v"
  lint_command: "ruff check --fix && ruff format"

skills_include:
  - python-review
  - python-patterns
  - tdd-workflow
  - security-review

skills_exclude:
  - "threejs-*"
  - "kotlin-*"
  - "swift-*"
  - "golang-*"
  - "frontend-*"
  - "react-*"
  - "springboot-*"
```

- [ ] **Step 4: cli_tool.yaml**

```yaml
version: 1
name: cli_tool
description: "Python CLI uygulamasi (click/typer)"
extends: base
languages: [python]
frameworks: []

claude_md:
  tech_stack: "Python 3.12, click/typer, rich"
  coding_standards: |
    - Her komut icin --help dokumantasyonu
    - Exit code'lari duzgun kullan (0=ok, 1=error)
    - Rich ile guzel cikti
  test_command: "pytest tests/ -v"
  lint_command: "ruff check --fix && ruff format"

skills_include:
  - python-review
  - python-patterns
  - tdd-workflow

skills_exclude:
  - "threejs-*"
  - "kotlin-*"
  - "swift-*"
  - "golang-*"
  - "frontend-*"
  - "springboot-*"
```

- [ ] **Step 5: data_pipeline.yaml ve fullstack.yaml**

```yaml
# data_pipeline.yaml
version: 1
name: data_pipeline
description: "Veri pipeline'i (ETL, batch processing)"
extends: base
languages: [python]
frameworks: []

claude_md:
  tech_stack: "Python 3.12, pandas/polars, httpx, SQLAlchemy"
  coding_standards: |
    - Idempotent islemler
    - Her adim loglama
    - Retry mekanizmasi
  test_command: "pytest tests/ -v"
  lint_command: "ruff check --fix && ruff format"

skills_include:
  - python-review
  - python-patterns
  - postgres-patterns
  - tdd-workflow

skills_exclude:
  - "threejs-*"
  - "kotlin-*"
  - "swift-*"
  - "frontend-*"
  - "springboot-*"
```

```yaml
# fullstack.yaml
version: 1
name: fullstack
description: "Fullstack proje (Python backend + React frontend)"
extends: base
languages: [python, node]
frameworks: [fastapi, react]

claude_md:
  tech_stack: "FastAPI + React + TypeScript + PostgreSQL"
  coding_standards: |
    - Backend: Python type hints, async/await
    - Frontend: TypeScript strict, no any
    - API: OpenAPI schema driven
  test_command: "pytest tests/ -v && cd frontend && npm test"
  lint_command: "ruff check --fix && cd frontend && npx eslint --fix ."

skills_include:
  - tdd-workflow
  - security-review
  - api-design
  - python-review
  - frontend-patterns
  - postgres-patterns
  - docker-patterns

skills_exclude:
  - "threejs-*"
  - "kotlin-*"
  - "swift-*"
  - "golang-*"
  - "perl-*"
  - "springboot-*"
```

- [ ] **Step 6: Test — tüm profiller yüklenebilmeli**

```python
# tests/test_profiles.py'a ekle
@pytest.mark.parametrize("name", ["base", "fastapi", "react", "telegram_bot", "cli_tool", "data_pipeline", "fullstack"])
def test_all_builtin_profiles_load(name):
    profile = load_profile(name)
    assert profile.name == name
    assert profile.description
```

- [ ] **Step 7: Test geçtiğini doğrula**

Run: `python -m pytest tests/test_profiles.py -v`
Expected: All passed

- [ ] **Step 8: Commit**

```bash
git add claude_forge/profiles/*.yaml tests/test_profiles.py
git commit -m "feat: hazir profiller ekle (fastapi, react, bot, cli, pipeline, fullstack)"
```

### Task 4: Profile Applicator (profili projeye uygula)

**Files:**
- Create: `claude_forge/profiles/applicator.py`
- Modify: `tests/test_profiles.py`

- [ ] **Step 1: Test yaz**

```python
# tests/test_profiles.py'a ekle
from claude_forge.profiles.applicator import apply_profile


def test_apply_profile_creates_structure(tmp_path):
    profile = load_profile("fastapi")
    apply_profile(profile, tmp_path, interactive=False)

    assert (tmp_path / "CLAUDE.md").exists()
    assert (tmp_path / ".claude" / "settings.json").exists()
    assert (tmp_path / ".claude" / "hooks" / "protect-env.sh").exists()
    assert (tmp_path / ".claude" / "rules" / "async-io.md").exists()
    assert (tmp_path / "memory" / "MEMORY.md").exists()

    claude_md = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert "FastAPI" in claude_md
    assert "tdd-workflow" in claude_md


def test_apply_profile_writes_skill_profile(tmp_path):
    profile = load_profile("fastapi")
    apply_profile(profile, tmp_path, interactive=False)

    import json
    sp = json.loads((tmp_path / ".claude" / "skill-profile.json").read_text())
    assert "tdd-workflow" in sp["active_skills"]
    assert "threejs-*" in sp["excluded_patterns"]
```

- [ ] **Step 2: Test fail ettiğini doğrula**

Run: `python -m pytest tests/test_profiles.py::test_apply_profile_creates_structure -v`

- [ ] **Step 3: Applicator yaz**

```python
# claude_forge/profiles/applicator.py
"""Apply a profile to a project directory."""

import json
from pathlib import Path
from datetime import date
from rich.console import Console
from rich.prompt import Confirm
from .schema import ProfileSchema

console = Console()


def apply_profile(profile: ProfileSchema, project_path: Path, interactive: bool = True) -> None:
    """Profili projeye uygula — dosya yapısı oluştur."""
    project_path = Path(project_path)

    # Dizinler
    for d in [".claude/hooks", ".claude/rules", ".claude/skills", "memory"]:
        (project_path / d).mkdir(parents=True, exist_ok=True)

    # CLAUDE.md
    claude_md = _render_claude_md(profile, project_path.name)
    _safe_write(project_path / "CLAUDE.md", claude_md, interactive)

    # Hooks
    for hook in profile.hooks:
        hook_content = _render_hook_script(hook.name, hook.command)
        hook_path = project_path / ".claude" / "hooks" / hook.name
        _safe_write(hook_path, hook_content, interactive, newline="\n")
        try:
            hook_path.chmod(0o755)
        except OSError:
            pass

    # settings.json
    settings = _render_settings(profile)
    _safe_write(
        project_path / ".claude" / "settings.json",
        json.dumps(settings, indent=2, ensure_ascii=False),
        interactive,
    )

    # Rules
    for rule in profile.rules:
        _safe_write(project_path / ".claude" / "rules" / rule.name, rule.content, interactive)

    # Memory
    for mem in profile.memory_templates:
        _safe_write(project_path / "memory" / mem.name, mem.content, interactive)

    # Skill profile
    skill_profile = {
        "generated_by": "claude-forge",
        "generated_at": str(date.today()),
        "profile": profile.name,
        "active_skills": profile.skills_include,
        "excluded_patterns": profile.skills_exclude,
    }
    _safe_write(
        project_path / ".claude" / "skill-profile.json",
        json.dumps(skill_profile, indent=2, ensure_ascii=False),
        interactive,
    )

    console.print(f"\n[green bold]Profil '{profile.name}' uygulandı![/green bold]")


def _render_claude_md(profile: ProfileSchema, project_name: str) -> str:
    sections = [f"# {project_name} — Claude Guide\n"]

    if profile.claude_md.tech_stack:
        sections.append(f"## Tech Stack\n{profile.claude_md.tech_stack}\n")

    if profile.claude_md.coding_standards:
        sections.append(f"## Coding Standards\n{profile.claude_md.coding_standards}\n")

    sections.append("## Hard Boundaries\n- Never edit .env files\n- Never commit directly to main/master\n- Never add features without tests\n")

    if profile.claude_md.test_command:
        sections.append(f"## Test Commands\n```bash\n{profile.claude_md.test_command}\n```\n")

    if profile.claude_md.lint_command:
        sections.append(f"## Lint Commands\n```bash\n{profile.claude_md.lint_command}\n```\n")

    if profile.skills_include:
        skills_text = "\n".join(f"- {s}" for s in profile.skills_include)
        sections.append(f"## Recommended Skills\n{skills_text}\n")

    sections.append("## Memory System\nRead `memory/MEMORY.md` at the start of every session.\nUpdate relevant memory files when discovering important findings.\n")

    for key, value in profile.claude_md.extra_sections.items():
        sections.append(f"## {key}\n{value}\n")

    return "\n".join(sections)


def _render_hook_script(name: str, command: str) -> str:
    return f"""#!/bin/bash
# Hook: {name}
FILE_PATH=$(echo "$CLAUDE_TOOL_INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('path',''))" 2>/dev/null)
{command}
exit 0
"""


def _render_settings(profile: ProfileSchema) -> dict:
    settings: dict = {"hooks": {}}
    for hook in profile.hooks:
        event = hook.event
        if event not in settings["hooks"]:
            settings["hooks"][event] = []
        settings["hooks"][event].append({
            "matcher": hook.matcher,
            "hooks": [{"type": "command", "command": f"bash .claude/hooks/{hook.name}", "timeout": 10}],
        })
    return settings


def _safe_write(path: Path, content: str, interactive: bool, newline: str | None = None) -> None:
    if path.exists() and interactive:
        if not Confirm.ask(f"  [yellow]{path.name} zaten var. Üzerine yaz?[/yellow]", default=False):
            console.print(f"  [dim][>] {path.name} atlandı[/dim]")
            return
    path.parent.mkdir(parents=True, exist_ok=True)
    if newline:
        with open(path, "w", encoding="utf-8", newline=newline) as f:
            f.write(content)
    else:
        path.write_text(content, encoding="utf-8")
    console.print(f"  [green][OK][/green] {path.name}")
```

- [ ] **Step 4: Test geçtiğini doğrula**

Run: `python -m pytest tests/test_profiles.py -v`
Expected: All passed

- [ ] **Step 5: Commit**

```bash
git add claude_forge/profiles/applicator.py tests/test_profiles.py
git commit -m "feat: profil applicator ekle"
```

### Task 5: Profile Extractor (mevcut projeden profil çıkar)

**Files:**
- Create: `claude_forge/profiles/extractor.py`
- Modify: `tests/test_profiles.py`

- [ ] **Step 1: Test yaz**

```python
# tests/test_profiles.py'a ekle
from claude_forge.profiles.extractor import extract_profile


def test_extract_profile_from_project(tmp_path):
    """apply sonrası extract yapınca aynı profili geri alabilmeli."""
    profile = load_profile("fastapi")
    apply_profile(profile, tmp_path, interactive=False)

    extracted = extract_profile(tmp_path, name="my-fastapi")
    assert extracted.name == "my-fastapi"
    assert len(extracted.rules) >= 1
    assert len(extracted.hooks) >= 1


def test_extract_empty_project(tmp_path):
    extracted = extract_profile(tmp_path, name="empty")
    assert extracted.name == "empty"
    assert extracted.rules == []
```

- [ ] **Step 2: Test fail ettiğini doğrula**

- [ ] **Step 3: Extractor yaz**

```python
# claude_forge/profiles/extractor.py
"""Extract a profile from an existing project's .claude/ structure."""

import json
import yaml
from pathlib import Path
from .schema import ProfileSchema, HookEntry, RuleEntry, MemoryTemplate


def extract_profile(project_path: Path, name: str) -> ProfileSchema:
    """Mevcut projedeki .claude/ yapısından profil çıkar."""
    project_path = Path(project_path)
    hooks = _extract_hooks(project_path)
    rules = _extract_rules(project_path)
    memory = _extract_memory(project_path)
    skills_include, skills_exclude = _extract_skill_profile(project_path)

    return ProfileSchema(
        name=name,
        description=f"Extracted from {project_path.name}",
        hooks=hooks,
        rules=rules,
        memory_templates=memory,
        skills_include=skills_include,
        skills_exclude=skills_exclude,
    )


def save_profile_yaml(profile: ProfileSchema, output_path: Path) -> None:
    """Profili YAML olarak kaydet."""
    data = profile.model_dump(exclude_defaults=True)
    data["version"] = 1
    output_path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _extract_hooks(project_path: Path) -> list[HookEntry]:
    hooks_dir = project_path / ".claude" / "hooks"
    settings_path = project_path / ".claude" / "settings.json"
    hooks = []

    if not hooks_dir.exists():
        return hooks

    # settings.json'dan event/matcher bilgisi al
    event_map: dict[str, tuple[str, str]] = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            for event, entries in settings.get("hooks", {}).items():
                for entry in entries:
                    for h in entry.get("hooks", []):
                        cmd = h.get("command", "")
                        for hook_file in hooks_dir.iterdir():
                            if hook_file.name in cmd:
                                event_map[hook_file.name] = (event, entry.get("matcher", ""))
        except (json.JSONDecodeError, KeyError):
            pass

    for hook_file in hooks_dir.iterdir():
        if hook_file.is_file():
            event, matcher = event_map.get(hook_file.name, ("PostToolUse", "Edit|Write"))
            hooks.append(HookEntry(
                name=hook_file.name,
                event=event,
                matcher=matcher,
                command=hook_file.read_text(encoding="utf-8", errors="ignore"),
            ))

    return hooks


def _extract_rules(project_path: Path) -> list[RuleEntry]:
    rules_dir = project_path / ".claude" / "rules"
    if not rules_dir.exists():
        return []
    return [
        RuleEntry(name=f.name, content=f.read_text(encoding="utf-8", errors="ignore"))
        for f in sorted(rules_dir.iterdir()) if f.is_file()
    ]


def _extract_memory(project_path: Path) -> list[MemoryTemplate]:
    memory_dir = project_path / "memory"
    if not memory_dir.exists():
        return []
    return [
        MemoryTemplate(name=f.name, content=f.read_text(encoding="utf-8", errors="ignore"))
        for f in sorted(memory_dir.iterdir()) if f.is_file()
    ]


def _extract_skill_profile(project_path: Path) -> tuple[list[str], list[str]]:
    sp_path = project_path / ".claude" / "skill-profile.json"
    if not sp_path.exists():
        return [], []
    try:
        data = json.loads(sp_path.read_text(encoding="utf-8"))
        return data.get("active_skills", []), data.get("excluded_patterns", [])
    except (json.JSONDecodeError, KeyError):
        return [], []
```

- [ ] **Step 4: Test geçtiğini doğrula**

Run: `python -m pytest tests/test_profiles.py -v`

- [ ] **Step 5: Commit**

```bash
git add claude_forge/profiles/extractor.py tests/test_profiles.py
git commit -m "feat: profil extractor ekle"
```

### Task 6: CLI'a Profil Komutlarını Ekle

**Files:**
- Modify: `claude_forge/cli.py`

- [ ] **Step 1: cli.py'a import ve yeni menü seçenekleri ekle**

`cli.py`'ın başına import ekle:
```python
from .profiles.loader import load_profile, list_profiles
from .profiles.applicator import apply_profile
from .profiles.extractor import extract_profile, save_profile_yaml
```

MAIN_MENU'ye ekle (mevcut "3" scan'dan önce):
```python
MAIN_MENU = [
    ("1", "New Project",        "Create a new project folder and set up Claude Code"),
    ("2", "Init Existing",      "Set up Claude Code in an existing project"),
    ("3", "Scan Project",       "Check a project for missing components"),
    ("4", "Release & Version",  "Version bump, quality check, push, release"),
    ("5", "Learning System",    "Record lessons, view & apply rules"),
    ("6", "Build Executable",   "Build project as .exe (PyInstaller)"),
    ("7", "Skills & Models",    "View skill inventory, change AI model"),
    ("8", "Profiles",           "Manage project profiles"),
    ("9", "Settings",           "API key, default model, config"),
    ("h", "Help",               "Show usage guide and examples"),
    ("q", "Quit",               "Exit Claude Forge"),
]
```

- [ ] **Step 2: flow_profiles ve `--profile` flag ekle**

```python
def flow_profiles(config: dict) -> None:
    """Profile management submenu."""
    PROFILE_MENU = [
        ("1", "List Profiles",    "Show available profiles"),
        ("2", "Apply to Project", "Apply a profile to a project"),
        ("3", "Create from Project", "Extract profile from existing project"),
        ("b", "Back",             "Return to main menu"),
    ]
    while True:
        console.print(Panel("Profile Management", border_style="magenta"))
        choice = show_menu(PROFILE_MENU, "Profiles")

        if choice == "b":
            break
        elif choice == "1":
            names = list_profiles()
            console.print("\n[bold]Available Profiles:[/bold]")
            for name in names:
                try:
                    p = load_profile(name)
                    console.print(f"  [cyan]{name}[/cyan] — {p.description}")
                except Exception:
                    console.print(f"  [cyan]{name}[/cyan] — [dim](error loading)[/dim]")
        elif choice == "2":
            names = list_profiles()
            console.print("Profiles: " + ", ".join(f"[cyan]{n}[/cyan]" for n in names))
            profile_name = Prompt.ask("Profile name")
            project_path = ask_path("Project path", must_exist=True)
            try:
                profile = load_profile(profile_name)
                apply_profile(profile, Path(project_path))
            except FileNotFoundError as e:
                console.print(f"[red]{e}[/red]")
        elif choice == "3":
            project_path = ask_path("Project path", must_exist=True)
            name = Prompt.ask("Profile name")
            profile = extract_profile(Path(project_path), name)
            out_dir = Path.home() / ".claude-forge" / "profiles"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / f"{name}.yaml"
            save_profile_yaml(profile, out_file)
            console.print(f"[green]Profile saved: {out_file}[/green]")

        console.print("\n[dim]Press Enter to continue...[/dim]")
        input()
```

`main()` click komutuna `--profile` option ekle ve _run_init'i güncelle:

```python
@click.command()
@click.argument("project_path", required=False, type=click.Path())
@click.option("--model", "-m", help="Override default model")
@click.option("--profile", "-p", help="Apply a profile instead of AI analysis")
def main(project_path, model, profile):
```

Quick mode'da profile desteği:
```python
if project_path:
    path = Path(project_path)
    if not path.exists():
        if Confirm.ask(f"[yellow]{path} does not exist. Create it?[/yellow]", default=True):
            path.mkdir(parents=True, exist_ok=True)
        else:
            raise SystemExit(0)
    if profile:
        try:
            prof = load_profile(profile)
            apply_profile(prof, path)
        except FileNotFoundError as e:
            console.print(f"[red]{e}[/red]")
        return
    if model:
        config["default_model"] = model
    _run_init(str(path.resolve()), config)
    return
```

while loop'taki menu handler'a `"8": flow_profiles(config)` ve `"9": flow_settings(config)` ekle.

- [ ] **Step 3: Test et**

Run: `claude-forge --help` ve `claude-forge C:\tmp\test-project -p fastapi` dene

- [ ] **Step 4: Commit**

```bash
git add claude_forge/cli.py
git commit -m "feat: CLI'a profil komutları ekle"
```

---

## Modül 2: Skill Navigator

### Task 7: Skill Registry Builder

**Files:**
- Create: `claude_forge/navigator.py`
- Create: `tests/test_navigator.py`

- [ ] **Step 1: Test yaz**

```python
# tests/test_navigator.py
import pytest
from claude_forge.navigator import build_registry, match_skills


def test_build_registry():
    """Registry oluşturulabilmeli."""
    registry = build_registry()
    assert isinstance(registry, dict)
    # En az birkaç skill olmalı
    assert len(registry) > 0


def test_registry_entry_structure():
    registry = build_registry()
    for name, entry in registry.items():
        assert "description" in entry
        assert "tags" in entry
        assert isinstance(entry["tags"], list)


def test_match_skills_python():
    registry = build_registry()
    result = match_skills(registry, languages=["python"], frameworks=["fastapi"])
    assert "recommended" in result
    assert "optional" in result
    assert "irrelevant" in result
    # python-review gibi skill'ler recommended'da olmalı
    rec_names = [s["name"] for s in result["recommended"]]
    # En az birkaç önerilen olmalı
    assert len(rec_names) >= 1


def test_match_skills_empty():
    result = match_skills({}, languages=["python"], frameworks=[])
    assert result["recommended"] == []
```

- [ ] **Step 2: Test fail ettiğini doğrula**

- [ ] **Step 3: Navigator yaz**

```python
# claude_forge/navigator.py
"""Skill Navigator — projeye uygun skill'leri filtrele ve öner."""

import json
import re
from pathlib import Path
from rich.console import Console
from rich.table import Table
from .scanner import scan_available_skills
from .config import load_config

console = Console()

CACHE_FILE = Path.home() / ".claude-forge" / "skill_registry.json"

# Keyword -> tag eşleme tablosu
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
    "three.js": ["threejs", "3d", "javascript"],
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


def build_registry(claude_home: str | None = None) -> dict:
    """Tüm skill'leri tara ve tag'li registry oluştur."""
    config = load_config()
    skills_info = scan_available_skills(claude_home or config.get("claude_home"))

    registry: dict = {}

    # Global skills
    for s in skills_info["global_skills"]:
        tags = _extract_tags(s["name"], s.get("description", ""))
        registry[s["name"]] = {
            "description": s.get("description", ""),
            "tags": tags,
            "source": "global",
        }

    # Plugin commands (skill olarak)
    for s in skills_info["plugin_commands"]:
        full_name = f"{s['plugin']}:{s['name']}" if s.get("plugin") else s["name"]
        tags = _extract_tags(s["name"], s.get("description", ""))
        registry[full_name] = {
            "description": s.get("description", ""),
            "tags": tags,
            "source": f"plugin:{s.get('org', '')}",
        }

    # Plugin agents
    for s in skills_info["plugin_agents"]:
        full_name = f"{s['plugin']}:{s['name']}"
        tags = _extract_tags(s["name"], s.get("description", ""))
        registry[full_name] = {
            "description": s.get("description", ""),
            "tags": tags,
            "source": f"agent:{s.get('org', '')}",
        }

    # Cache'e kaydet
    _save_cache(registry)
    return registry


def _extract_tags(name: str, description: str) -> list[str]:
    """İsim ve description'dan tag çıkar."""
    tags = set()
    text = f"{name} {description}".lower()

    for keyword, keyword_tags in KEYWORD_TAGS.items():
        if keyword in text:
            tags.update(keyword_tags)

    return sorted(tags)


def _save_cache(registry: dict) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")


def load_registry() -> dict:
    """Cache'ten yükle, yoksa oluştur."""
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    return build_registry()


def match_skills(
    registry: dict,
    languages: list[str],
    frameworks: list[str],
) -> dict[str, list]:
    """Projeye uygun skill'leri 3 gruba ayır."""
    project_tags = set()
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

        item = {"name": name, "description": entry["description"], "score": score, "tags": entry["tags"]}

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
    """Skill analiz sonucunu göster."""
    console.print(f"\n[bold]Skill Analizi: {project_name}[/bold]")

    if result["recommended"]:
        console.print(f"\n[green bold]Önerilen ({len(result['recommended'])}):[/green bold]")
        for s in result["recommended"]:
            console.print(f"  [green]+[/green] {s['name']:40s} {s['description'][:60]}")

    if result["optional"]:
        console.print(f"\n[yellow bold]Opsiyonel ({len(result['optional'])}):[/yellow bold]")
        for s in result["optional"][:10]:
            console.print(f"  [yellow]~[/yellow] {s['name']:40s} {s['description'][:60]}")

    console.print(f"\n[dim]İlgisiz: {len(result['irrelevant'])} skill[/dim]")
```

- [ ] **Step 4: Test geçtiğini doğrula**

Run: `python -m pytest tests/test_navigator.py -v`

- [ ] **Step 5: Commit**

```bash
git add claude_forge/navigator.py tests/test_navigator.py
git commit -m "feat: skill navigator ekle"
```

### Task 8: CLI'a Skill Navigator Ekle

**Files:**
- Modify: `claude_forge/cli.py`

- [ ] **Step 1: Import ve yeni menü ekle**

```python
from .navigator import build_registry, match_skills, display_skill_analysis, load_registry
```

Skills & Models submenu'ye skill analizi ekle:
```python
elif choice == "1":
    project_path_input = ask_path("Project path (or press Enter to skip)", must_exist=False)
    if project_path_input and Path(project_path_input).exists():
        from .scanner import scan_project
        project_info = scan_project(project_path_input)
        registry = build_registry(config.get("claude_home"))
        result = match_skills(registry, project_info["languages"], project_info["frameworks"])
        display_skill_analysis(result, project_info["name"])
    else:
        # Sadece envanter göster (mevcut davranış)
        skills_info = scan_available_skills(config.get("claude_home"))
        # ... mevcut kod
```

- [ ] **Step 2: Test et**

Run: `claude-forge` → 7 → 1 → proje yolu gir

- [ ] **Step 3: Commit**

```bash
git add claude_forge/cli.py
git commit -m "feat: CLI'a skill navigator entegrasyonu ekle"
```

---

## Modül 3: Big Project Module

### Task 9: Codemap Generator

**Files:**
- Create: `claude_forge/mapper.py`
- Create: `tests/test_mapper.py`

- [ ] **Step 1: Test yaz**

```python
# tests/test_mapper.py
import pytest
from pathlib import Path
from claude_forge.mapper import generate_codemap, find_entry_points, analyze_python_imports


def test_generate_codemap(tmp_path):
    """Basit proje için codemap üretebilmeli."""
    # Yapı oluştur
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "__init__.py").write_text("")
    (tmp_path / "src" / "main.py").write_text("from src.utils import helper\n\ndef main():\n    pass\n")
    (tmp_path / "src" / "utils.py").write_text("def helper():\n    pass\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_main.py").write_text("")

    codemap = generate_codemap(tmp_path)
    assert "src/" in codemap
    assert "main.py" in codemap


def test_find_entry_points(tmp_path):
    (tmp_path / "main.py").write_text("if __name__")
    (tmp_path / "app.py").write_text("")
    entries = find_entry_points(tmp_path)
    assert "main.py" in entries


def test_analyze_python_imports(tmp_path):
    code = "from src.auth import login\nimport src.models\nfrom pathlib import Path\n"
    (tmp_path / "test.py").write_text(code)
    imports = analyze_python_imports(tmp_path / "test.py")
    assert "src.auth" in imports
    assert "src.models" in imports
    # stdlib import'ları dahil etmemeli
    assert "pathlib" not in imports


def test_codemap_max_files(tmp_path):
    """500'den fazla dosya varsa sınırlamalı."""
    for i in range(10):
        d = tmp_path / f"pkg{i}"
        d.mkdir()
        for j in range(5):
            (d / f"f{j}.py").write_text("")

    codemap = generate_codemap(tmp_path)
    assert isinstance(codemap, str)
```

- [ ] **Step 2: Test fail**

- [ ] **Step 3: Mapper yaz**

```python
# claude_forge/mapper.py
"""Codemap generator — proje haritası çıkarır."""

import ast
import re
import sys
from pathlib import Path
from rich.console import Console

console = Console()

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".next",
             "dist", "build", ".tox", ".pytest_cache", ".mypy_cache", "egg-info"}

ENTRY_POINT_NAMES = {"main.py", "app.py", "cli.py", "__main__.py", "index.ts",
                     "index.js", "server.py", "server.ts", "manage.py"}

MAX_FILES = 500


def generate_codemap(project_path: Path) -> str:
    """Proje codemap'i üret (markdown formatında)."""
    project_path = Path(project_path)
    modules = _discover_modules(project_path)
    entries = find_entry_points(project_path)
    dep_graph = _build_dependency_graph(project_path)

    lines = [f"# {project_path.name} — Codemap\n"]
    lines.append(f"Generated by claude-forge\n")

    # Modüller
    lines.append("## Modules\n")
    for mod_path, files in sorted(modules.items()):
        rel = mod_path.relative_to(project_path) if mod_path != project_path else Path(".")
        lines.append(f"- `{rel}/` — {len(files)} files")

    # Entry points
    if entries:
        lines.append("\n## Entry Points\n")
        for ep in entries:
            lines.append(f"- `{ep}`")

    # Bağımlılık grafiği
    if dep_graph:
        lines.append("\n## Dependency Graph\n")
        lines.append("```")
        for src, targets in sorted(dep_graph.items()):
            for t in sorted(targets):
                lines.append(f"{src} -> {t}")
        lines.append("```")

    return "\n".join(lines) + "\n"


def _discover_modules(project_path: Path) -> dict[Path, list[str]]:
    """Modül dizinlerini ve dosyalarını keşfet."""
    modules: dict[Path, list[str]] = {}
    count = 0

    for item in sorted(project_path.rglob("*")):
        if count >= MAX_FILES:
            break
        if any(sd in item.parts for sd in SKIP_DIRS):
            continue
        if item.is_file() and item.suffix in {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs"}:
            count += 1
            parent = item.parent
            if parent not in modules:
                modules[parent] = []
            modules[parent].append(item.name)

    return modules


def find_entry_points(project_path: Path) -> list[str]:
    """Entry point dosyalarını bul."""
    entries = []
    for item in project_path.iterdir():
        if item.is_file() and item.name in ENTRY_POINT_NAMES:
            entries.append(item.name)

    # package.json scripts
    pkg_json = project_path / "package.json"
    if pkg_json.exists():
        try:
            import json
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            main = data.get("main")
            if main:
                entries.append(f"package.json → {main}")
        except Exception:
            pass

    return sorted(set(entries))


def analyze_python_imports(file_path: Path) -> list[str]:
    """Python dosyasındaki local import'ları analiz et (ast ile)."""
    try:
        source = file_path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return []

    imports = []
    stdlib_modules = set(sys.stdlib_module_names) if hasattr(sys, "stdlib_module_names") else set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top not in stdlib_modules:
                    imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                top = node.module.split(".")[0]
                if top not in stdlib_modules:
                    imports.append(node.module)
            elif node.module and node.level > 0:
                imports.append(node.module)

    return imports


def _build_dependency_graph(project_path: Path) -> dict[str, set[str]]:
    """Modüller arası bağımlılık grafiği oluştur."""
    graph: dict[str, set[str]] = {}
    modules = _discover_modules(project_path)

    # Sadece Python dosyaları için (en güvenilir)
    for mod_path, files in modules.items():
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = mod_path / fname
            imports = analyze_python_imports(fpath)
            rel_mod = str(mod_path.relative_to(project_path)).replace("\\", "/").replace("/", ".")
            if rel_mod == ".":
                rel_mod = "root"

            for imp in imports:
                top = imp.split(".")[0]
                # Proje içi import mi?
                for other_mod_path in modules:
                    other_rel = str(other_mod_path.relative_to(project_path)).replace("\\", "/")
                    if top in other_rel or other_rel.startswith(top):
                        target = other_rel.replace("/", ".") or "root"
                        if target != rel_mod:
                            if rel_mod not in graph:
                                graph[rel_mod] = set()
                            graph[rel_mod].add(target)

    return graph


def write_codemap(project_path: Path, output_path: Path | None = None) -> Path:
    """Codemap üret ve dosyaya yaz."""
    project_path = Path(project_path)
    content = generate_codemap(project_path)

    if output_path is None:
        output_path = project_path / "docs" / "CODEMAP.md"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    console.print(f"[green][OK][/green] Codemap: {output_path}")
    return output_path
```

- [ ] **Step 4: Test geçtiğini doğrula**

Run: `python -m pytest tests/test_mapper.py -v`

- [ ] **Step 5: Commit**

```bash
git add claude_forge/mapper.py tests/test_mapper.py
git commit -m "feat: codemap generator ekle"
```

### Task 10: Context Manager

**Files:**
- Create: `claude_forge/context_manager.py`
- Create: `tests/test_context_manager.py`

- [ ] **Step 1: Test yaz**

```python
# tests/test_context_manager.py
import pytest
from pathlib import Path
from claude_forge.context_manager import context_status, context_compact_preview


def test_context_status_empty(tmp_path):
    status = context_status(tmp_path)
    assert status["memory_files"] == 0
    assert status["has_codemap"] is False


def test_context_status_with_memory(tmp_path):
    mem_dir = tmp_path / "memory"
    mem_dir.mkdir()
    (mem_dir / "MEMORY.md").write_text("# Memory")
    (mem_dir / "debug.md").write_text("# Debug\nsome content")

    status = context_status(tmp_path)
    assert status["memory_files"] == 2
    assert status["total_lines"] > 0


def test_context_compact_preview(tmp_path):
    mem_dir = tmp_path / "memory"
    mem_dir.mkdir()
    (mem_dir / "old.md").write_text("# Old\nstale content")

    preview = context_compact_preview(tmp_path)
    assert isinstance(preview, list)
```

- [ ] **Step 2: Test fail**

- [ ] **Step 3: Context Manager yaz**

```python
# claude_forge/context_manager.py
"""Context and memory management for projects."""

from pathlib import Path
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table

console = Console()


def context_status(project_path: Path) -> dict:
    """Memory ve context durumunu raporla."""
    project_path = Path(project_path)
    memory_dir = project_path / "memory"
    codemap_path = project_path / "docs" / "CODEMAP.md"

    result = {
        "memory_files": 0,
        "total_lines": 0,
        "has_codemap": codemap_path.exists(),
        "has_claude_md": (project_path / "CLAUDE.md").exists(),
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


def display_context_status(project_path: Path) -> None:
    """Context durumunu göster."""
    status = context_status(project_path)

    table = Table(title="Context Status")
    table.add_column("Item", style="cyan")
    table.add_column("Status")
    table.add_column("Detail", style="dim")

    table.add_row(
        "CLAUDE.md",
        "[green]OK[/green]" if status["has_claude_md"] else "[red]YOK[/red]",
        "",
    )
    table.add_row(
        "Codemap",
        "[green]OK[/green]" if status["has_codemap"] else "[yellow]YOK[/yellow]",
        "claude-forge map ile oluştur" if not status["has_codemap"] else "",
    )
    table.add_row(
        "Memory dosyaları",
        str(status["memory_files"]),
        f"{status['total_lines']} satır toplam",
    )

    console.print(table)

    if status["files"]:
        console.print("\n[bold]Memory Dosyaları:[/bold]")
        for f in status["files"]:
            console.print(f"  {f['name']:30s} {f['lines']:>5d} satır  [dim]{f['modified'][:10]}[/dim]")


def context_compact_preview(project_path: Path, days: int = 30) -> list[dict]:
    """Eski memory dosyalarını tespit et (silmez, sadece rapor)."""
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
    """Compact preview göster."""
    stale = context_compact_preview(project_path)
    if not stale:
        console.print("[green]Eski memory dosyası yok.[/green]")
        return

    console.print(f"\n[yellow]Eski Memory Dosyaları ({len(stale)}):[/yellow]")
    for f in stale:
        console.print(f"  [yellow]![/yellow] {f['name']:30s} {f['days_old']} gün önce güncellendi")
    console.print("\n[dim]Bu dosyaları silmek için manuel olarak kaldırın.[/dim]")
```

- [ ] **Step 4: Test geçtiğini doğrula**

Run: `python -m pytest tests/test_context_manager.py -v`

- [ ] **Step 5: Commit**

```bash
git add claude_forge/context_manager.py tests/test_context_manager.py
git commit -m "feat: context manager ekle"
```

### Task 11: CLI'a Map ve Context Komutları Ekle

**Files:**
- Modify: `claude_forge/cli.py`

- [ ] **Step 1: Import ekle**

```python
from .mapper import write_codemap, generate_codemap
from .context_manager import display_context_status, display_compact_preview
```

- [ ] **Step 2: Menüye "Map & Context" seçeneği ekle**

MAIN_MENU'ye `("m", "Map & Context", "Codemap, modüler CLAUDE.md, memory yönetimi")` ekle.

```python
def flow_map_context() -> None:
    """Map & Context submenu."""
    MAP_MENU = [
        ("1", "Generate Codemap",   "Proje haritası üret (docs/CODEMAP.md)"),
        ("2", "Context Status",     "Memory ve context durumu"),
        ("3", "Compact Preview",    "Eski memory dosyalarını göster"),
        ("b", "Back",               "Return to main menu"),
    ]
    while True:
        console.print(Panel("Map & Context", border_style="blue"))
        choice = show_menu(MAP_MENU, "Map & Context")

        if choice == "b":
            break
        elif choice == "1":
            project_path = ask_path("Project path", must_exist=True)
            write_codemap(Path(project_path))
        elif choice == "2":
            project_path = ask_path("Project path", must_exist=True)
            display_context_status(Path(project_path))
        elif choice == "3":
            project_path = ask_path("Project path", must_exist=True)
            display_compact_preview(Path(project_path))

        console.print("\n[dim]Press Enter to continue...[/dim]")
        input()
```

- [ ] **Step 3: Test et**

- [ ] **Step 4: Commit**

```bash
git add claude_forge/cli.py
git commit -m "feat: CLI'a map & context komutları ekle"
```

---

## Modül 4: Cross-Project Sync

### Task 12: Sync Export/Import

**Files:**
- Create: `claude_forge/sync.py`
- Create: `tests/test_sync.py`

- [ ] **Step 1: Test yaz**

```python
# tests/test_sync.py
import pytest
import json
from pathlib import Path
from claude_forge.sync import export_project, import_project, diff_projects


def test_export_project(tmp_path):
    """Proje export'u JSON üretmeli."""
    # Setup
    (tmp_path / ".claude" / "rules").mkdir(parents=True)
    (tmp_path / ".claude" / "rules" / "r1.md").write_text("rule 1")
    (tmp_path / ".claude" / "hooks").mkdir(parents=True)
    (tmp_path / ".claude" / "hooks" / "format.sh").write_text("#!/bin/bash\nexit 0")
    (tmp_path / "memory").mkdir()
    (tmp_path / "memory" / "MEMORY.md").write_text("# Memory")

    result = export_project(tmp_path)
    assert result["source_project"] == tmp_path.name
    assert len(result["rules"]) == 1
    assert len(result["hooks"]) == 1
    assert len(result["memory_files"]) == 1


def test_export_import_roundtrip(tmp_path):
    """Export → Import roundtrip çalışmalı."""
    src = tmp_path / "src_project"
    dst = tmp_path / "dst_project"
    src.mkdir()
    dst.mkdir()

    (src / ".claude" / "rules").mkdir(parents=True)
    (src / ".claude" / "rules" / "r1.md").write_text("rule 1")

    exported = export_project(src)
    export_path = tmp_path / "export.json"
    export_path.write_text(json.dumps(exported), encoding="utf-8")

    stats = import_project(dst, export_path, interactive=False)
    assert stats["rules_imported"] >= 1
    assert (dst / ".claude" / "rules" / "r1.md").exists()


def test_diff_projects(tmp_path):
    p1 = tmp_path / "p1"
    p2 = tmp_path / "p2"
    p1.mkdir()
    p2.mkdir()

    (p1 / ".claude" / "rules").mkdir(parents=True)
    (p1 / ".claude" / "rules" / "r1.md").write_text("rule 1")
    (p2 / ".claude" / "rules").mkdir(parents=True)
    (p2 / ".claude" / "rules" / "r1.md").write_text("rule 1 modified")
    (p2 / ".claude" / "rules" / "r2.md").write_text("rule 2")

    diff = diff_projects(p1, p2)
    assert len(diff["only_in_p2"]) >= 1  # r2.md
    assert len(diff["different"]) >= 1    # r1.md
```

- [ ] **Step 2: Test fail**

- [ ] **Step 3: Sync yaz**

```python
# claude_forge/sync.py
"""Cross-project setup sync — export, import, diff."""

import json
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt

console = Console()


def export_project(project_path: Path) -> dict:
    """Projenin .claude/ setup'ını JSON olarak dışa aktar."""
    project_path = Path(project_path)
    result = {
        "exported_at": datetime.now().isoformat(),
        "source_project": project_path.name,
        "rules": [],
        "hooks": [],
        "memory_files": [],
    }

    # Rules
    rules_dir = project_path / ".claude" / "rules"
    if rules_dir.exists():
        for f in sorted(rules_dir.iterdir()):
            if f.is_file():
                result["rules"].append({"name": f.name, "content": f.read_text(encoding="utf-8", errors="ignore")})

    # Hooks
    hooks_dir = project_path / ".claude" / "hooks"
    if hooks_dir.exists():
        for f in sorted(hooks_dir.iterdir()):
            if f.is_file():
                result["hooks"].append({"name": f.name, "content": f.read_text(encoding="utf-8", errors="ignore")})

    # Memory
    memory_dir = project_path / "memory"
    if memory_dir.exists():
        for f in sorted(memory_dir.iterdir()):
            if f.is_file():
                result["memory_files"].append({"name": f.name, "content": f.read_text(encoding="utf-8", errors="ignore")})

    # Skill profile
    sp = project_path / ".claude" / "skill-profile.json"
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
) -> dict:
    """Export dosyasından projeye setup al."""
    project_path = Path(project_path)
    data = json.loads(Path(export_path).read_text(encoding="utf-8"))
    stats = {"rules_imported": 0, "hooks_imported": 0, "memory_imported": 0, "skipped": 0}

    # Rules
    rules_dir = project_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)
    for rule in data.get("rules", []):
        target = rules_dir / rule["name"]
        if _should_write(target, rule["content"], interactive):
            target.write_text(rule["content"], encoding="utf-8")
            stats["rules_imported"] += 1
            console.print(f"  [green][OK][/green] rule: {rule['name']}")
        else:
            stats["skipped"] += 1

    # Hooks
    hooks_dir = project_path / ".claude" / "hooks"
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

    # Memory
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
    """Dosya yazılmalı mı?"""
    if not target.exists():
        return True
    existing = target.read_text(encoding="utf-8", errors="ignore")
    if existing == new_content:
        return False  # Aynı içerik
    if not interactive:
        return True
    console.print(f"\n[yellow]Çakışma: {target.name}[/yellow]")
    console.print(f"  Mevcut: {existing[:100]}...")
    console.print(f"  Yeni:   {new_content[:100]}...")
    choice = Prompt.ask("  [K]aynak / [H]edef / [A]tla", default="A")
    return choice.upper() == "K"


def diff_projects(path1: Path, path2: Path) -> dict:
    """İki projenin .claude/ setup'ını karşılaştır."""
    result = {"only_in_p1": [], "only_in_p2": [], "different": [], "same": []}

    files1 = _collect_setup_files(path1)
    files2 = _collect_setup_files(path2)

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


def _collect_setup_files(project_path: Path) -> dict[str, str]:
    """Projedeki setup dosyalarını topla."""
    files = {}
    for subdir in [".claude/rules", ".claude/hooks", "memory"]:
        d = project_path / subdir
        if d.exists():
            for f in d.iterdir():
                if f.is_file():
                    key = f"{subdir}/{f.name}"
                    files[key] = f.read_text(encoding="utf-8", errors="ignore")
    return files


def display_diff(diff: dict, name1: str, name2: str) -> None:
    """Diff sonucunu göster."""
    if diff["only_in_p1"]:
        console.print(f"\n[cyan]Sadece {name1}:[/cyan]")
        for f in diff["only_in_p1"]:
            console.print(f"  + {f}")

    if diff["only_in_p2"]:
        console.print(f"\n[yellow]Sadece {name2}:[/yellow]")
        for f in diff["only_in_p2"]:
            console.print(f"  + {f}")

    if diff["different"]:
        console.print(f"\n[red]Farklı:[/red]")
        for f in diff["different"]:
            console.print(f"  ~ {f}")

    if diff["same"]:
        console.print(f"\n[green]Aynı: {len(diff['same'])} dosya[/green]")
```

- [ ] **Step 4: Test geçtiğini doğrula**

Run: `python -m pytest tests/test_sync.py -v`

- [ ] **Step 5: Commit**

```bash
git add claude_forge/sync.py tests/test_sync.py
git commit -m "feat: cross-project sync modülü ekle"
```

### Task 13: CLI'a Sync Komutları Ekle

**Files:**
- Modify: `claude_forge/cli.py`

- [ ] **Step 1: Import ve menü**

```python
from .sync import export_project, import_project, diff_projects, display_diff
```

MAIN_MENU'ye `("s", "Sync", "Cross-project setup sync")` ekle.

```python
def flow_sync() -> None:
    SYNC_MENU = [
        ("1", "Export",  "Mevcut projenin setup'ını dışa aktar"),
        ("2", "Import",  "Başka projeden setup al"),
        ("3", "Diff",    "İki projenin setup'ını karşılaştır"),
        ("b", "Back",    "Return to main menu"),
    ]
    while True:
        console.print(Panel("Cross-Project Sync", border_style="green"))
        choice = show_menu(SYNC_MENU, "Sync")

        if choice == "b":
            break
        elif choice == "1":
            project_path = ask_path("Project path", must_exist=True)
            data = export_project(Path(project_path))
            out = Path(project_path) / "claude-forge-export.json"
            out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            console.print(f"[green]Exported: {out}[/green]")
        elif choice == "2":
            project_path = ask_path("Target project path", must_exist=True)
            export_file = ask_path("Export JSON file path", must_exist=True)
            stats = import_project(Path(project_path), Path(export_file))
            console.print(f"\n[green]Imported: {stats['rules_imported']} rules, {stats['hooks_imported']} hooks[/green]")
            if stats["skipped"]:
                console.print(f"[dim]Skipped: {stats['skipped']}[/dim]")
        elif choice == "3":
            p1 = ask_path("Project 1 path", must_exist=True)
            p2 = ask_path("Project 2 path", must_exist=True)
            diff = diff_projects(Path(p1), Path(p2))
            display_diff(diff, Path(p1).name, Path(p2).name)

        console.print("\n[dim]Press Enter to continue...[/dim]")
        input()
```

- [ ] **Step 2: json import ekle** (cli.py başına)

```python
import json
```

- [ ] **Step 3: Test et, commit**

```bash
git add claude_forge/cli.py
git commit -m "feat: CLI'a sync komutları ekle"
```

---

## Son Dokunuşlar

### Task 14: Learner Güçlendirme (project_type tag)

**Files:**
- Modify: `claude_forge/learner.py`
- Modify: `tests/test_profiles.py` (veya yeni test)

- [ ] **Step 1: add_lesson'a project_type parametresi ekle**

`learner.py`'daki `add_lesson` fonksiyonuna `project_type: str = ""` parametresi ekle. Lesson dict'e `"project_type": project_type` alanı ekle.

- [ ] **Step 2: apply_lessons_to_project'e project_type filtresi ekle**

```python
def apply_lessons_to_project(project_path: str, project_type: str = "") -> int:
    lessons = load_lessons()
    if not lessons:
        return 0
    # project_type filtresi
    if project_type:
        lessons = [l for l in lessons if not l.get("project_type") or l["project_type"] == project_type]
    # ... mevcut kod
```

- [ ] **Step 3: interactive_learn'e project_type sorusu ekle**

Categories'den sonra:
```python
project_type = Prompt.ask("Project type (or leave empty for all)", default="")
```

- [ ] **Step 4: Commit**

```bash
git add claude_forge/learner.py
git commit -m "feat: lesson'lara project_type filtresi ekle"
```

### Task 15: Conftest ve Final Test

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: conftest.py**

```python
# tests/conftest.py
import pytest
from pathlib import Path


@pytest.fixture
def sample_project(tmp_path):
    """Basit bir test projesi oluştur."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "__init__.py").write_text("")
    (tmp_path / "src" / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n")
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\nversion = "0.1.0"\n')
    (tmp_path / "tests").mkdir()
    return tmp_path


@pytest.fixture
def sample_project_with_claude(sample_project):
    """Claude Code setup'lı test projesi."""
    (sample_project / ".claude" / "hooks").mkdir(parents=True)
    (sample_project / ".claude" / "rules").mkdir(parents=True)
    (sample_project / "memory").mkdir()
    (sample_project / "CLAUDE.md").write_text("# Test Project\n")
    (sample_project / "memory" / "MEMORY.md").write_text("# Memory\n")
    return sample_project
```

- [ ] **Step 2: Tüm testleri çalıştır**

Run: `python -m pytest tests/ -v --tb=short`
Expected: All passed

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py tests/__init__.py
git commit -m "feat: test conftest ve fixtures ekle"
```

### Task 16: Final — Versiyon ve Temizlik

- [ ] **Step 1: Tüm testler geçiyor mu kontrol et**

Run: `python -m pytest tests/ -v`

- [ ] **Step 2: Ruff check**

Run: `ruff check claude_forge/ tests/ --fix && ruff format claude_forge/ tests/`

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat: claude-forge v0.2.0 — profiles, navigator, mapper, sync"
```
