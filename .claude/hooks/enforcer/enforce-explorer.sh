#!/bin/bash
# Enforce explorer-first pattern.
# - When orchestrator spawns the explorer agent, set a session flag.
# - Block direct Grep/Glob calls until the flag exists.
# This ensures the explorer agent (haiku, specs-first) is always used
# before the orchestrator reaches for raw search tools.

INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name')
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
FLAG="/tmp/claude-explorer-${SESSION_ID}"

case "$TOOL" in
  Agent)
    SUBAGENT=$(echo "$INPUT" | jq -r '.tool_input.subagent_type // empty')
    if [[ "$SUBAGENT" == "explorer" ]]; then
      touch "$FLAG"
    fi
    exit 0
    ;;
  Grep|Glob)
    if [ ! -f "$FLAG" ]; then
      jq -n '{
        "decision": "block",
        "reason": "Do not call Grep or Glob directly. Deploy the explorer agent first — it checks .specs/ before searching code, uses haiku (cheaper), and is the required first step per workflow."
      }'
    fi
    exit 0
    ;;
esac

exit 0
