#!/usr/bin/env bash
# Deny reading the archived 800+ cyber skill dump (and offensive skill paths)
# so they are not injected into the model context.
set -euo pipefail

input=$(cat)
file_path=$(printf '%s' "$input" | jq -r '.file_path // empty')

# Fail open on empty path (nothing to gate)
if [[ -z "$file_path" ]]; then
  echo '{ "permission": "allow" }'
  exit 0
fi

deny_msg='Blocked: cybersecurity skill archive / offensive skill path. Use only .cursor/skills/<allowlisted>/SKILL.md.'

# Absolute or relative paths into the vendor archive
if [[ "$file_path" == *'/.vendor/cybersecurity-skills/'* ]] \
  || [[ "$file_path" == *'/vendor/cybersecurity-skills/'* ]] \
  || [[ "$file_path" == .vendor/cybersecurity-skills/* ]] \
  || [[ "$file_path" == *'/.cursor/rules/.agents/'* ]] \
  || [[ "$file_path" == *'/skills-lock.json' && "$file_path" == *cybersecurity* ]]; then
  jq -n \
    --arg um "$deny_msg" \
    --arg am "$deny_msg" \
    '{ permission: "deny", user_message: $um, agent_message: $am }'
  exit 0
fi

# Offensive skill directory names if ever reintroduced under .cursor
base=$(basename "$(dirname "$file_path")")
case "$base" in
  exploiting-*|abusing-*|attacking-*|relaying-*|escaping-*|coercing-*|moving-laterally-*|operating-sliver-*|operating-havoc-*|building-c2-*|building-red-team-*|post-exploiting-*)
    if [[ "$file_path" == */SKILL.md || "$file_path" == */references/* || "$file_path" == */scripts/* || "$file_path" == */assets/* ]]; then
      jq -n \
        --arg um "$deny_msg" \
        --arg am "$deny_msg" \
        '{ permission: "deny", user_message: $um, agent_message: $am }'
      exit 0
    fi
    ;;
esac

echo '{ "permission": "allow" }'
exit 0
