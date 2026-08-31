#!/usr/bin/env bash
# After a code edit, stamp that graphify should refresh once (on agent stop).
set -euo pipefail

input=$(cat)
file_path=$(printf '%s' "$input" | jq -r '.file_path // empty')

# Nothing to do without a path
if [[ -z "$file_path" ]]; then
  exit 0
fi

# Skip non-product / generated / archive paths
case "$file_path" in
  */graphify-out/*|graphify-out/*) exit 0 ;;
  */.cursor/*|.cursor/*) exit 0 ;;
  */.vendor/*|.vendor/*) exit 0 ;;
  */node_modules/*|*/.next/*|*/.venv/*|*/venv/*) exit 0 ;;
  */canvases/*) exit 0 ;;
esac

# Only stamp for code / infra sources that affect the product graph
case "$file_path" in
  *.py|*.ts|*.tsx|*.js|*.jsx|*.mjs|*.cjs|*.yml|*.yaml|*.toml|*.sql|*.md)
    ;;
  *)
    exit 0
    ;;
esac

case "$file_path" in
  */apps/*|*/docs/*|*/infra/*|*/scripts/*|*/.github/*|docker-compose*.yml|Makefile|README.md|REQUIREMENTS.md|pyproject.toml|apps/*|docs/*|infra/*|scripts/*|.github/*)
    mkdir -p .cursor/hooks
    # One line per dirty file keeps the stamp cheap to inspect
    printf '%s\n' "$file_path" >> .cursor/hooks/.graphify-dirty
    ;;
esac

exit 0
