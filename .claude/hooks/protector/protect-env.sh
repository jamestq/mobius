#!/bin/bash
# Block agents from reading, editing, or writing .env files.
# Also blocks Bash commands that would read .env file contents.

INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name')

case "$TOOL" in
  Read|Edit|Write)
    FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
    BASENAME=$(basename "$FILE_PATH")
    if [[ "$BASENAME" == .env || "$BASENAME" == .env.* ]]; then
      echo "Blocked: reading or modifying .env files is not allowed ($FILE_PATH)" >&2
      exit 2
    fi
    ;;
  Bash)
    CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
    # Check if the command references a .env file (as argument, not as substring of other words)
    if echo "$CMD" | grep -qP '(^|\s|/|"'"'"')\.env(\s|$|\.|-|"'"'"'|;|\||&|>|<|/)'; then
      echo "Blocked: Bash commands that access .env files are not allowed" >&2
      exit 2
    fi
    ;;
  Grep)
    GREP_PATH=$(echo "$INPUT" | jq -r '.tool_input.path // empty')
    if [[ -n "$GREP_PATH" ]]; then
      BASENAME=$(basename "$GREP_PATH")
      if [[ "$BASENAME" == .env || "$BASENAME" == .env.* ]]; then
        echo "Blocked: searching .env files is not allowed ($GREP_PATH)" >&2
        exit 2
      fi
    fi
    ;;
esac

exit 0
