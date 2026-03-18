#!/bin/bash
# Enforce architect-before-engineer pattern.
# - When architect agent is spawned, set a session flag.
# - Block engineer agent if explorer has run (new feature context)
#   but architect has not — this targets "designing new solutions"
#   without blocking direct explorer→engineer flows for bug fixes.

INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name')
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')

EXPLORER_FLAG="/tmp/claude-explorer-${SESSION_ID}"
ARCHITECT_FLAG="/tmp/claude-architect-${SESSION_ID}"

if [[ "$TOOL" != "Agent" ]]; then
  exit 0
fi

SUBAGENT=$(echo "$INPUT" | jq -r '.tool_input.subagent_type // empty')

case "$SUBAGENT" in
  architect)
    touch "$ARCHITECT_FLAG"
    exit 0
    ;;
  engineer)
    # Block only when: exploration has happened (new feature context)
    # but architect has not yet been consulted.
    if [ -f "$EXPLORER_FLAG" ] && [ ! -f "$ARCHITECT_FLAG" ]; then
      jq -n '{
        "decision": "block",
        "reason": "Deploy the architect agent before the engineer. Exploration is done — architect must design the solution, delegate specs to clerk, then hand off to engineer."
      }'
    fi
    exit 0
    ;;
esac

exit 0
