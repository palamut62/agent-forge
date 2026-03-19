#!/bin/bash
# Hook: qa-gate.sh (Stop - notification type)
# Claude durmadan once kalite kontrolu yapar.
# Commit edilmemis degisiklik, kalan TODO, veya test basarisizligi varsa uyarir.

QA_ISSUES=""

# 1. Commit edilmemis degisiklik kontrolu
if [ -d ".git" ]; then
  DIRTY=$(git status --porcelain 2>/dev/null | wc -l)
  if [ "$DIRTY" -gt 0 ] 2>/dev/null; then
    QA_ISSUES="$QA_ISSUES\n[!] $DIRTY dosyada commit edilmemis degisiklik var"
  fi
fi

# 2. TODO/FIXME kontrolu - son degisikliklerde
if [ -d ".git" ]; then
  NEW_TODOS=$(git diff 2>/dev/null | grep -c "^+.*\(TODO\|FIXME\|HACK\|XXX\)" 2>/dev/null || echo 0)
  if [ "$NEW_TODOS" -gt 0 ] 2>/dev/null; then
    QA_ISSUES="$QA_ISSUES\n[!] $NEW_TODOS yeni TODO/FIXME eklenmis"
  fi
fi

# 3. Test kontrolu - test komutu varsa calistir
TEST_CMD=""
if [ -f "pyproject.toml" ] && command -v pytest &>/dev/null; then
  TEST_CMD="pytest tests/ -x -q --tb=line 2>&1"
elif [ -f "package.json" ] && grep -q '"test"' package.json 2>/dev/null; then
  TEST_CMD="npm test --silent 2>&1"
elif [ -f "go.mod" ] && command -v go &>/dev/null; then
  TEST_CMD="go test ./... -count=1 -short 2>&1"
elif [ -f "Cargo.toml" ] && command -v cargo &>/dev/null; then
  TEST_CMD="cargo test --quiet 2>&1"
fi

if [ -n "$TEST_CMD" ]; then
  TEST_OUTPUT=$(eval "$TEST_CMD" 2>&1)
  TEST_EXIT=$?
  if [ $TEST_EXIT -ne 0 ]; then
    FAIL_SUMMARY=$(echo "$TEST_OUTPUT" | grep -iE "(FAILED|FAIL|ERROR|error)" | head -3 | tr '\n' ' ' | cut -c1-200)
    QA_ISSUES="$QA_ISSUES\n[!] Testler basarisiz: $FAIL_SUMMARY"
  fi
fi

# 4. Syntax hatasi kontrolu (Python)
if [ -f "pyproject.toml" ] && command -v python3 &>/dev/null; then
  SYNTAX_ERRORS=""
  for f in $(git diff --name-only 2>/dev/null | grep '\.py$'); do
    if [ -f "$f" ]; then
      python3 -c "import py_compile; py_compile.compile('$f', doraise=True)" 2>&1
      if [ $? -ne 0 ]; then
        SYNTAX_ERRORS="$SYNTAX_ERRORS $f"
      fi
    fi
  done
  if [ -n "$SYNTAX_ERRORS" ]; then
    QA_ISSUES="$QA_ISSUES\n[!] Syntax hatasi:$SYNTAX_ERRORS"
  fi
fi

# Sonuc
if [ -n "$QA_ISSUES" ]; then
  echo "===== QA Gate Uyarisi ====="
  echo -e "$QA_ISSUES"
  echo ""
  echo "Bu sorunlari cozmeyi dusun."
  echo "============================"

  # Brain'e kaydet
  BRAIN_FILE="memory/brain.jsonl"
  TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  if [ -d "memory" ]; then
    CLEAN_ISSUES=$(echo -e "$QA_ISSUES" | tr '\n' '; ' | cut -c1-300)
    echo "{\"type\":\"qa_warning\",\"issues\":\"$CLEAN_ISSUES\",\"ts\":\"$TIMESTAMP\"}" >> "$BRAIN_FILE"
  fi
else
  echo "QA Gate: Tum kontroller gecti."
fi

exit 0
