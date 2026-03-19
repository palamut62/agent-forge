#!/bin/bash
# Hook: session-start.sh (SessionStart - notification type)
# Proje acildiginda tech stack tespit edip context ozetini gosterir.
# memory/brain.jsonl'den son session bilgilerini yukler.

BRAIN_FILE="memory/brain.jsonl"
PROJECT_DIR="$(pwd)"
PROJECT_NAME=$(basename "$PROJECT_DIR")

# --- Tech Stack Tespiti ---
TECH_STACK=""
FRAMEWORKS=""

# Python
if [ -f "pyproject.toml" ] || [ -f "setup.py" ] || [ -f "requirements.txt" ]; then
  TECH_STACK="$TECH_STACK python"
  if grep -qiE "fastapi" pyproject.toml requirements.txt setup.py 2>/dev/null; then FRAMEWORKS="$FRAMEWORKS fastapi"; fi
  if grep -qiE "django" pyproject.toml requirements.txt setup.py 2>/dev/null; then FRAMEWORKS="$FRAMEWORKS django"; fi
  if grep -qiE "flask" pyproject.toml requirements.txt setup.py 2>/dev/null; then FRAMEWORKS="$FRAMEWORKS flask"; fi
fi

# Node.js
if [ -f "package.json" ]; then
  TECH_STACK="$TECH_STACK node"
  if grep -q '"react"' package.json 2>/dev/null; then FRAMEWORKS="$FRAMEWORKS react"; fi
  if grep -q '"next"' package.json 2>/dev/null; then FRAMEWORKS="$FRAMEWORKS nextjs"; fi
  if grep -q '"vue"' package.json 2>/dev/null; then FRAMEWORKS="$FRAMEWORKS vue"; fi
  if grep -q '"svelte"' package.json 2>/dev/null; then FRAMEWORKS="$FRAMEWORKS svelte"; fi
  if grep -q '"express"' package.json 2>/dev/null; then FRAMEWORKS="$FRAMEWORKS express"; fi
  if grep -q '"fastify"' package.json 2>/dev/null; then FRAMEWORKS="$FRAMEWORKS fastify"; fi
  if grep -q '"electron"' package.json 2>/dev/null; then FRAMEWORKS="$FRAMEWORKS electron"; fi
  if grep -q '"react-native"' package.json 2>/dev/null; then FRAMEWORKS="$FRAMEWORKS react-native"; fi
fi

# Go
if [ -f "go.mod" ]; then
  TECH_STACK="$TECH_STACK go"
  if grep -q "gin-gonic" go.mod 2>/dev/null; then FRAMEWORKS="$FRAMEWORKS gin"; fi
  if grep -q "go-chi" go.mod 2>/dev/null; then FRAMEWORKS="$FRAMEWORKS chi"; fi
  if grep -q "echo" go.mod 2>/dev/null; then FRAMEWORKS="$FRAMEWORKS echo"; fi
fi

# Rust
if [ -f "Cargo.toml" ]; then
  TECH_STACK="$TECH_STACK rust"
  if grep -q "actix" Cargo.toml 2>/dev/null; then FRAMEWORKS="$FRAMEWORKS actix"; fi
  if grep -q "axum" Cargo.toml 2>/dev/null; then FRAMEWORKS="$FRAMEWORKS axum"; fi
  if grep -q "tokio" Cargo.toml 2>/dev/null; then FRAMEWORKS="$FRAMEWORKS tokio"; fi
fi

# Java/Kotlin
if [ -f "build.gradle" ] || [ -f "build.gradle.kts" ] || [ -f "pom.xml" ]; then
  if [ -f "build.gradle.kts" ]; then TECH_STACK="$TECH_STACK kotlin"; else TECH_STACK="$TECH_STACK java"; fi
  if grep -qiE "spring" build.gradle build.gradle.kts pom.xml 2>/dev/null; then FRAMEWORKS="$FRAMEWORKS springboot"; fi
  if grep -qiE "compose" build.gradle.kts 2>/dev/null; then FRAMEWORKS="$FRAMEWORKS jetpack-compose"; fi
fi

# Flutter/Dart
if [ -f "pubspec.yaml" ]; then
  TECH_STACK="$TECH_STACK dart"
  FRAMEWORKS="$FRAMEWORKS flutter"
fi

# Swift
if [ -f "Package.swift" ] || ls *.xcodeproj 1>/dev/null 2>&1 || ls *.xcworkspace 1>/dev/null 2>&1; then
  TECH_STACK="$TECH_STACK swift"
  if grep -qr "SwiftUI" . --include="*.swift" 2>/dev/null; then FRAMEWORKS="$FRAMEWORKS swiftui"; fi
fi

# --- Brain Ozeti ---
BRAIN_SUMMARY=""
if [ -f "$BRAIN_FILE" ]; then
  ERROR_COUNT=$(grep -c '"type":"error"' "$BRAIN_FILE" 2>/dev/null || echo 0)
  CHANGE_COUNT=$(grep -c '"type":"change"' "$BRAIN_FILE" 2>/dev/null || echo 0)
  LAST_ERRORS=$(grep '"type":"error"' "$BRAIN_FILE" 2>/dev/null | tail -3 | python3 -c "
import sys,json
for line in sys.stdin:
    try:
        d=json.loads(line.strip())
        print(f\"  - {d.get('summary','')[:80]}\")
    except: pass
" 2>/dev/null)
  BRAIN_SUMMARY="Brain: ${CHANGE_COUNT} degisiklik, ${ERROR_COUNT} hata kaydi"
  if [ -n "$LAST_ERRORS" ]; then
    BRAIN_SUMMARY="$BRAIN_SUMMARY\nSon hatalar:\n$LAST_ERRORS"
  fi
fi

# --- Cikti ---
echo "===== Session Start: $PROJECT_NAME ====="
if [ -n "$TECH_STACK" ]; then
  echo "Tech:$TECH_STACK"
fi
if [ -n "$FRAMEWORKS" ]; then
  echo "Frameworks:$FRAMEWORKS"
fi

# Dosya sayisi
FILE_COUNT=$(find . -maxdepth 3 -type f -not -path './.git/*' -not -path './node_modules/*' -not -path './__pycache__/*' -not -path './.venv/*' 2>/dev/null | wc -l)
echo "Files: $FILE_COUNT"

if [ -n "$BRAIN_SUMMARY" ]; then
  echo -e "$BRAIN_SUMMARY"
fi

# Git durumu
if [ -d ".git" ]; then
  BRANCH=$(git branch --show-current 2>/dev/null)
  DIRTY=$(git status --porcelain 2>/dev/null | wc -l)
  echo "Git: $BRANCH ($DIRTY uncommitted)"
fi

echo "=================================="
exit 0
