#!/usr/bin/env node

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import React, { useEffect, useMemo, useState } from "react";
import { render, Box, Text, useApp, useInput, useStdout, useStdin } from "ink";

const h = React.createElement;
const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const PACKAGE_ROOT = path.resolve(SCRIPT_DIR, "..");

const TARGET_LABELS = {
  claude: "Claude Code",
  codex: "Codex",
  antigravity: "Antigravity",
};

const MENUS = {
  intro: {
    title: "Agent Forge",
    subtitle: "Set up and manage Claude Code, Codex, and Antigravity workflows.",
    items: [
      { id: "continue", title: "Continue", description: "Open quick start menu", type: "menu", to: "quick" },
      { id: "change-target", title: "Change Target", description: "Choose Claude Code, Codex, or Antigravity", type: "menu", to: "target" },
      { id: "help", title: "Help", description: "Open usage guide", type: "menu", to: "help" },
      { id: "quit", title: "Quit", description: "Exit Agent Forge", type: "quit" },
    ],
  },
  quick: {
    title: "Quick Start",
    subtitle: "Choose the first action.",
    items: [
      { id: "new-project", title: "New Project", description: "Create a project and bootstrap setup", type: "flow", flow: "new-project" },
      { id: "init-existing", title: "Init Existing", description: "Set up assistant in an existing project", type: "flow", flow: "init-existing" },
      { id: "settings", title: "Settings", description: "Edit API key, model, target defaults", type: "flow", flow: "settings" },
      { id: "all-tools", title: "All Tools", description: "Open advanced tools", type: "menu", to: "tools" },
      { id: "back", title: "Back", description: "Return to previous menu", type: "back" },
    ],
  },
  tools: {
    title: "All Tools",
    subtitle: "Direct access to flows.",
    items: [
      { id: "scan-project", title: "Scan Project", description: "Check missing setup components", type: "flow", flow: "scan-project" },
      { id: "release", title: "Release & Version", description: "Versioning, quality, release helpers", type: "flow", flow: "release" },
      { id: "learning", title: "Learning System", description: "Record and apply lessons", type: "flow", flow: "learning" },
      { id: "build", title: "Build Executable", description: "Build executable with PyInstaller", type: "flow", flow: "build" },
      { id: "skills-models", title: "Skills & Models", description: "Skill inventory and model selection", type: "flow", flow: "skills-models" },
      { id: "profiles", title: "Profiles", description: "List/apply/create profiles", type: "flow", flow: "profiles" },
      { id: "map-context", title: "Map & Context", description: "Codemap and memory context tools", type: "flow", flow: "map-context" },
      { id: "sync", title: "Sync", description: "Cross-project setup sync", type: "flow", flow: "sync" },
      { id: "back", title: "Back", description: "Return to previous menu", type: "back" },
    ],
  },
  target: {
    title: "Target Platform",
    subtitle: "Set default target for generated assistant files.",
    items: [
      { id: "target-claude", title: "Claude Code", description: "Use CLAUDE.md and .claude/", type: "target", target: "claude" },
      { id: "target-codex", title: "Codex", description: "Use AGENTS.md and .codex/", type: "target", target: "codex" },
      { id: "target-antigravity", title: "Antigravity", description: "Use ANTIGRAVITY.md and .antigravity/", type: "target", target: "antigravity" },
      { id: "back", title: "Back", description: "Return to previous menu", type: "back" },
    ],
  },
  help: {
    title: "Help",
    subtitle: "Built-in usage guide. Press Esc to return.",
    pageLines: [
      "Quick Start:",
      "  Continue -> New Project / Init Existing",
      "  Change Target -> Claude Code / Codex / Antigravity",
      "",
      "Shortcuts:",
      "  Up/Down move, Enter select, Esc back",
      "  Type to filter, / for command palette",
      "  Ctrl+L clear, Ctrl+C quit",
      "",
      "Slash Commands:",
      "  /settings /scan /release /sync /profiles /help",
      "  /claude /codex /antigravity /quit",
      "",
      "CLI:",
      "  agent-forge",
      "  agent-forge C:\\path\\to\\project -t codex",
      "  agent-forge-py  (direct Python CLI)",
    ],
    items: [
      { id: "back", title: "Back", description: "Return to previous menu", type: "back" },
    ],
  },
};

const QUICK_COMMANDS = [
  { id: "cmd-home", command: "/home", title: "Home", description: "Go to intro screen", type: "jump-menu", to: "intro" },
  { id: "cmd-quick", command: "/quick", title: "Quick Start", description: "Go to quick start menu", type: "jump-menu", to: "quick" },
  { id: "cmd-tools", command: "/tools", title: "All Tools", description: "Go to all tools menu", type: "jump-menu", to: "tools" },
  { id: "cmd-target", command: "/target", title: "Target Menu", description: "Open target platform menu", type: "jump-menu", to: "target" },
  { id: "cmd-new", command: "/new", title: "New Project", description: "Run new project flow", type: "flow", flow: "new-project" },
  { id: "cmd-init", command: "/init", title: "Init Existing", description: "Run init existing flow", type: "flow", flow: "init-existing" },
  { id: "cmd-scan", command: "/scan", title: "Scan Project", description: "Run scan flow", type: "flow", flow: "scan-project" },
  { id: "cmd-release", command: "/release", title: "Release & Version", description: "Run release flow", type: "flow", flow: "release" },
  { id: "cmd-learning", command: "/learning", title: "Learning System", description: "Run learning flow", type: "flow", flow: "learning" },
  { id: "cmd-build", command: "/build", title: "Build Executable", description: "Run build flow", type: "flow", flow: "build" },
  { id: "cmd-skills", command: "/skills", title: "Skills & Models", description: "Run skills/models flow", type: "flow", flow: "skills-models" },
  { id: "cmd-profiles", command: "/profiles", title: "Profiles", description: "Run profiles flow", type: "flow", flow: "profiles" },
  { id: "cmd-map", command: "/map", title: "Map & Context", description: "Run map/context flow", type: "flow", flow: "map-context" },
  { id: "cmd-sync", command: "/sync", title: "Sync", description: "Run sync flow", type: "flow", flow: "sync" },
  { id: "cmd-settings", command: "/settings", title: "Settings", description: "Run settings flow", type: "flow", flow: "settings" },
  { id: "cmd-help", command: "/help", title: "Help", description: "Open built-in help page", type: "jump-menu", to: "help" },
  { id: "cmd-claude", command: "/claude", title: "Set Target Claude", description: "Set default target to Claude Code", type: "target", target: "claude" },
  { id: "cmd-codex", command: "/codex", title: "Set Target Codex", description: "Set default target to Codex", type: "target", target: "codex" },
  { id: "cmd-antigravity", command: "/antigravity", title: "Set Target Antigravity", description: "Set default target to Antigravity", type: "target", target: "antigravity" },
  { id: "cmd-quit", command: "/quit", title: "Quit", description: "Exit Agent Forge", type: "quit" },
];

function configPath() {
  return path.join(os.homedir(), ".agent-forge", "config.json");
}

function legacyConfigPath() {
  return path.join(os.homedir(), ".claude-forge", "config.json");
}

function loadConfig() {
  const file = configPath();
  const legacyFile = legacyConfigPath();
  try {
    if (fs.existsSync(file)) {
      return JSON.parse(fs.readFileSync(file, "utf-8"));
    }
    if (fs.existsSync(legacyFile)) {
      return JSON.parse(fs.readFileSync(legacyFile, "utf-8"));
    }
    return {};
  } catch {
    return {};
  }
}

function saveConfig(nextConfig) {
  const file = configPath();
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(nextConfig, null, 2)}\n`, "utf-8");
}

function detectPythonCommand() {
  const preferred = process.env.CLAUDE_FORGE_PYTHON;
  const candidates = [preferred, "python", "py"].filter(Boolean);

  for (const cmd of candidates) {
    const args = cmd === "py" ? ["-3", "--version"] : ["--version"];
    const probe = spawnSync(cmd, args, { encoding: "utf-8" });
    if (!probe.error && probe.status === 0) {
      return cmd;
    }
  }
  return null;
}

function runBackend(cliArgs) {
  const python = detectPythonCommand();
  if (!python) {
    return { ok: false, message: "Python bulunamadi. `python` veya `py` komutu gerekli." };
  }

  const baseArgs = python === "py" ? ["-3", "-m", "claude_forge.cli"] : ["-m", "claude_forge.cli"];
  const pythonPathParts = [PACKAGE_ROOT];
  if (process.env.PYTHONPATH) {
    pythonPathParts.push(process.env.PYTHONPATH);
  }
  const env = {
    ...process.env,
    PYTHONPATH: pythonPathParts.join(path.delimiter),
  };

  const result = spawnSync(python, [...baseArgs, ...cliArgs], {
    stdio: "inherit",
    cwd: process.cwd(),
    env,
  });

  if (result.error) {
    return { ok: false, message: `Komut hatasi: ${result.error.message}` };
  }
  if (typeof result.status === "number" && result.status !== 0) {
    return { ok: false, message: `Islem ${result.status} koduyla bitti.` };
  }
  return { ok: true, message: "Islem tamamlandi." };
}

function line(width, ch = "-") {
  const w = Math.max(20, width - 2);
  return ch.repeat(w);
}

function App() {
  const { exit } = useApp();
  const { stdout } = useStdout();
  const { setRawMode } = useStdin();

  const [menuStack, setMenuStack] = useState(["intro"]);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(0);
  const [help, setHelp] = useState(false);
  const [status, setStatus] = useState("");
  const [config, setConfig] = useState(loadConfig());

  const activeMenuId = menuStack[menuStack.length - 1];
  const menu = MENUS[activeMenuId] ?? MENUS.intro;
  const items = menu.items;
  const slashMode = query.startsWith("/");
  const pageMode = Boolean(menu.pageLines) && !slashMode;
  const sourceItems = slashMode ? QUICK_COMMANDS : items;
  const termWidth = stdout?.columns ?? 100;

  const filtered = useMemo(() => {
    const raw = slashMode ? query.slice(1) : query;
    const q = raw.trim().toLowerCase();
    if (!q) {
      return sourceItems;
    }
    return sourceItems.filter(
      (item) =>
        (item.command || "").toLowerCase().includes(q) ||
        (item.title || "").toLowerCase().includes(q) ||
        (item.description || "").toLowerCase().includes(q) ||
        (item.id || "").toLowerCase().includes(q),
    );
  }, [sourceItems, query, slashMode]);

  useEffect(() => {
    if (filtered.length === 0) {
      setSelected(0);
      return;
    }
    if (selected >= filtered.length) {
      setSelected(filtered.length - 1);
    }
    if (selected < 0) {
      setSelected(0);
    }
  }, [filtered, selected]);

  const maxVisible = 8;
  const start = Math.max(
    0,
    Math.min(selected - Math.floor(maxVisible / 2), Math.max(0, filtered.length - maxVisible)),
  );
  const end = Math.min(filtered.length, start + maxVisible);
  const visible = filtered.slice(start, end);
  const active = filtered[selected];

  function goBack() {
    setQuery("");
    setHelp(false);
    setStatus("");
    setSelected(0);
    setMenuStack((prev) => {
      if (prev.length <= 1) {
        exit();
        return prev;
      }
      return prev.slice(0, -1);
    });
  }

  function runWithCleanTerminal(args) {
    if (typeof setRawMode === "function") {
      setRawMode(false);
    }
    process.stdout.write("\x1Bc");
    const result = runBackend(args);
    process.stdout.write("\n");
    if (typeof setRawMode === "function") {
      setRawMode(true);
    }
    setStatus(result.message);
    setQuery("");
  }

  function executeAction(action) {
    if (!action) {
      return;
    }
    if (action.type === "quit") {
      exit();
      return;
    }
    if (action.type === "back") {
      goBack();
      return;
    }
    if (action.type === "menu" && action.to) {
      setMenuStack((prev) => [...prev, action.to]);
      setQuery("");
      setSelected(0);
      setHelp(false);
      setStatus("");
      return;
    }
    if (action.type === "jump-menu" && action.to) {
      setMenuStack([action.to]);
      setQuery("");
      setSelected(0);
      setHelp(false);
      setStatus("");
      return;
    }
    if (action.type === "target" && action.target) {
      const next = { ...config, default_target: action.target };
      saveConfig(next);
      setConfig(next);
      setStatus(`Varsayilan hedef: ${TARGET_LABELS[action.target] ?? action.target}`);
      return;
    }
    if (action.type === "flow" && action.flow) {
      runWithCleanTerminal(["--flow", action.flow]);
    }
  }

  function handleEnter() {
    if (!active) {
      return;
    }
    executeAction(active);
  }

  useInput((input, key) => {
    const text = input || "";
    const isEscape = key.escape || input === "\u001b";
    const isLeft = key.leftArrow;

    if (key.ctrl && text.toLowerCase() === "c") {
      exit();
      return;
    }
    if (isEscape || isLeft) {
      goBack();
      return;
    }
    if (key.ctrl && text.toLowerCase() === "l") {
      setQuery("");
      setSelected(0);
      setStatus("");
      return;
    }
    if (text === "?") {
      setHelp((prev) => !prev);
      return;
    }
    if (key.upArrow) {
      if (filtered.length > 0) {
        setSelected((prev) => (prev - 1 + filtered.length) % filtered.length);
      }
      return;
    }
    if (key.downArrow) {
      if (filtered.length > 0) {
        setSelected((prev) => (prev + 1) % filtered.length);
      }
      return;
    }
    if (key.return) {
      handleEnter();
      return;
    }
    if (key.backspace || key.delete) {
      if (query) {
        setQuery((prev) => prev.slice(0, -1));
      } else {
        goBack();
      }
      return;
    }
    if (text && text.length === 1 && !key.ctrl && !key.meta) {
      const code = text.charCodeAt(0);
      if (code >= 32 && code <= 126) {
        setQuery((prev) => prev + text);
      }
    }
  });

  const currentTarget = String(config.default_target || "claude").toLowerCase();
  const targetLabel = TARGET_LABELS[currentTarget] ?? currentTarget;
  const modelLabel = config.default_model || "(not set)";
  const frameWidth = Math.min(termWidth - 2, 112);
  const cwd = process.cwd();

  const listChildren = help
    ? [
        h(Text, { key: "h1", color: "gray" }, "Up/Down: move"),
        h(Text, { key: "h2", color: "gray" }, "Type: filter"),
        h(Text, { key: "h2b", color: "gray" }, "/: open global command palette"),
        h(Text, { key: "h3", color: "gray" }, "Enter: select"),
        h(Text, { key: "h4", color: "gray" }, "Esc/Left/Backspace: back"),
        h(Text, { key: "h5", color: "gray" }, "Ctrl+L: clear filter"),
        h(Text, { key: "h6", color: "gray" }, "Ctrl+C: quit"),
      ]
    : pageMode
      ? (() => {
          const lines = [...menu.pageLines.map((line, i) => h(Text, { key: `p${i}`, color: "gray" }, line))];
          const backSelected = selected === 0;
          lines.push(h(Text, { key: "p-spacer", color: "gray" }, ""));
          lines.push(h(Text, {
            key: "p-back",
            color: backSelected ? "black" : "white",
            backgroundColor: backSelected ? "yellow" : undefined,
            children: `${backSelected ? "> " : "  "}Back`,
          }));
          return lines;
        })()
    : visible.length === 0
      ? [h(Text, { key: "empty", color: "gray" }, "No command matches your filter.")]
      : visible.map((item, idx) => {
          const absolute = start + idx;
          const isActive = absolute === selected;
          return h(Text, {
            key: item.id,
            color: isActive ? "black" : "white",
            backgroundColor: isActive ? "yellow" : undefined,
            children: slashMode
              ? `${isActive ? "> " : "  "}${item.command}  ${item.title}`
              : `${isActive ? "> " : "  "}${item.title}`,
          });
        });

  if (!help && start > 0) {
    listChildren.unshift(h(Text, { key: "top-more", color: "gray" }, "  ..."));
  }
  if (!help && end < filtered.length) {
    listChildren.push(h(Text, { key: "bottom-more", color: "gray" }, "  ..."));
  }

  return h(
    Box,
    { flexDirection: "column" },
    h(Text, { color: "gray" }, `${cwd}>agent-forge  (npm tui)`),
    h(
      Box,
      { borderStyle: "round", borderColor: "cyan", width: frameWidth, paddingX: 1, flexDirection: "column" },
      h(Text, { color: "yellowBright", bold: true }, menu.title),
      h(Text, { color: "white" }, menu.subtitle),
      h(Text, { color: "gray" }, `Default target: ${targetLabel} | Default model: ${modelLabel}`),
      h(Text, { color: "gray" }, cwd),
    ),
    h(
      Box,
      null,
      h(Text, { color: "whiteBright" }, "> "),
      h(Text, { color: "white" }, query),
      h(Text, { inverse: true }, " "),
    ),
    h(Text, { color: "gray" }, line(termWidth)),
    h(Box, { flexDirection: "column" }, ...listChildren),
    h(
      Box,
      null,
      h(
        Text,
        { color: "gray" },
        active ? (slashMode ? `${active.command}  ${active.description}` : active.description) : " ",
      ),
    ),
    h(Text, { color: "gray" }, line(termWidth)),
    h(
      Box,
      null,
      h(
        Text,
        { color: "yellow" },
        `? shortcuts  |  / commands  Up/Down move  Type filter  Enter select  Esc back  ${filtered.length}/${sourceItems.length}`,
      ),
    ),
    h(
      Box,
      null,
      h(Text, { color: status.includes("tamamlandi") ? "green" : "red" }, status || " "),
    ),
  );
}

function main() {
  const passthroughArgs = process.argv.slice(2);

  if (passthroughArgs.length > 0) {
    const result = runBackend(passthroughArgs);
    if (!result.ok) {
      console.error(result.message);
      process.exit(1);
    }
    process.exit(0);
  }

  if (!process.stdin.isTTY || !process.stdout.isTTY) {
    const result = runBackend([]);
    if (!result.ok) {
      console.error(result.message);
      process.exit(1);
    }
    process.exit(0);
  }

  render(h(App));
}

main();
