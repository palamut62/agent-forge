#!/bin/bash
# Hook: brain-sync.sh (PostToolUse)
# Her tool kullanimi sonrasi kararlari, hatalari ve hedefleri otomatik kaydeder.
# memory/brain.jsonl dosyasina JSONL formatta yazar.

BRAIN_FILE="memory/brain.jsonl"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Tool bilgilerini al
TOOL_NAME="${CLAUDE_TOOL_NAME:-unknown}"
TOOL_INPUT=$(echo "$CLAUDE_TOOL_INPUT" 2>/dev/null || echo "{}")
TOOL_OUTPUT=$(echo "$CLAUDE_TOOL_OUTPUT" 2>/dev/null || echo "")

# brain.jsonl yoksa olustur
mkdir -p memory
touch "$BRAIN_FILE"

# Dosya boyutu kontrolu - 500KB'dan buyukse eski kayitlari temizle
if [ -f "$BRAIN_FILE" ]; then
  FILE_SIZE=$(wc -c < "$BRAIN_FILE" 2>/dev/null || echo 0)
  if [ "$FILE_SIZE" -gt 512000 ] 2>/dev/null; then
    tail -100 "$BRAIN_FILE" > "${BRAIN_FILE}.tmp" && mv "${BRAIN_FILE}.tmp" "$BRAIN_FILE"
  fi
fi

# Hata tespiti - exit code veya hata mesaji varsa kaydet
if echo "$TOOL_OUTPUT" | grep -qiE "(error|exception|traceback|failed|FAILED|panic|undefined)" 2>/dev/null; then
  SNIPPET=$(echo "$TOOL_OUTPUT" | head -3 | tr '\n' ' ' | cut -c1-200)
  echo "{\"type\":\"error\",\"tool\":\"$TOOL_NAME\",\"summary\":\"$SNIPPET\",\"ts\":\"$TIMESTAMP\"}" >> "$BRAIN_FILE"
fi

# Dosya yazma/duzenleme tespiti
if [ "$TOOL_NAME" = "Write" ] || [ "$TOOL_NAME" = "Edit" ]; then
  FILE_PATH=$(echo "$TOOL_INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('file_path',d.get('path','')))" 2>/dev/null)
  if [ -n "$FILE_PATH" ]; then
    echo "{\"type\":\"change\",\"tool\":\"$TOOL_NAME\",\"file\":\"$FILE_PATH\",\"ts\":\"$TIMESTAMP\"}" >> "$BRAIN_FILE"
  fi
fi

# Bash komutu tespiti
if [ "$TOOL_NAME" = "Bash" ]; then
  CMD=$(echo "$TOOL_INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('command','')[:150])" 2>/dev/null)
  if [ -n "$CMD" ]; then
    echo "{\"type\":\"command\",\"command\":\"$CMD\",\"ts\":\"$TIMESTAMP\"}" >> "$BRAIN_FILE"
  fi
fi

exit 0
