#!/bin/bash
# Hook: pre-compact.sh (PreCompact - notification type)
# Context sikistirilmadan once onemli bilgileri brain.jsonl'e kaydeder.
# Boylece context kaybi yasandiginda bile kritik bilgiler korunur.

BRAIN_FILE="memory/brain.jsonl"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

mkdir -p memory

# Mevcut brain'den son durum ozetini al
if [ -f "$BRAIN_FILE" ]; then
  TOTAL_CHANGES=$(grep -c '"type":"change"' "$BRAIN_FILE" 2>/dev/null || echo 0)
  TOTAL_ERRORS=$(grep -c '"type":"error"' "$BRAIN_FILE" 2>/dev/null || echo 0)
  TOTAL_COMMANDS=$(grep -c '"type":"command"' "$BRAIN_FILE" 2>/dev/null || echo 0)

  # Son degisiklikleri topla
  RECENT_FILES=$(grep '"type":"change"' "$BRAIN_FILE" 2>/dev/null | tail -10 | python3 -c "
import sys,json
files=set()
for line in sys.stdin:
    try:
        d=json.loads(line.strip())
        f=d.get('file','')
        if f: files.add(f)
    except: pass
print(', '.join(sorted(files)[:10]))
" 2>/dev/null)

  # Compact ozeti yaz
  echo "{\"type\":\"compact\",\"changes\":$TOTAL_CHANGES,\"errors\":$TOTAL_ERRORS,\"commands\":$TOTAL_COMMANDS,\"recent_files\":\"$RECENT_FILES\",\"ts\":\"$TIMESTAMP\"}" >> "$BRAIN_FILE"
fi

# Git diff ozetini kaydet (varsa)
if [ -d ".git" ]; then
  BRANCH=$(git branch --show-current 2>/dev/null)
  DIFF_STAT=$(git diff --stat 2>/dev/null | tail -1 | tr -d '\n')
  STAGED_STAT=$(git diff --cached --stat 2>/dev/null | tail -1 | tr -d '\n')
  if [ -n "$DIFF_STAT" ] || [ -n "$STAGED_STAT" ]; then
    echo "{\"type\":\"compact_git\",\"branch\":\"$BRANCH\",\"unstaged\":\"$DIFF_STAT\",\"staged\":\"$STAGED_STAT\",\"ts\":\"$TIMESTAMP\"}" >> "$BRAIN_FILE"
  fi
fi

echo "Pre-compact: context ozeti brain.jsonl'e kaydedildi."
exit 0
