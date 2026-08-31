#!/usr/bin/env bash
# On agent stop: if code edits were stamped dirty, refresh the AST graph (no LLM).
set -euo pipefail

# Consume stop payload (unused); keep stdin drained
cat >/dev/null || true

STAMP=.cursor/hooks/.graphify-dirty
if [[ ! -f "$STAMP" ]]; then
  exit 0
fi

if ! command -v graphify >/dev/null 2>&1; then
  rm -f "$STAMP"
  exit 0
fi

# Debounce: skip if we updated less than 20s ago
NOW=$(date +%s)
LAST_FILE=.cursor/hooks/.graphify-last-run
if [[ -f "$LAST_FILE" ]]; then
  LAST=$(cat "$LAST_FILE" 2>/dev/null || echo 0)
  if [[ "$LAST" =~ ^[0-9]+$ ]] && (( NOW - LAST < 20 )); then
    rm -f "$STAMP"
    exit 0
  fi
fi

graphify update . >/dev/null 2>&1 || true
printf '%s\n' "$NOW" > "$LAST_FILE"
rm -f "$STAMP"
exit 0
