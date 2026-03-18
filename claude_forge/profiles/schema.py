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
