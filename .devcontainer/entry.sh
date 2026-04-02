#!/bin/bash
set -e

# Fix ownership of shared volumes
sudo chown -R dev:dev /home/dev/.cache/pypoetry /home/dev/.claude 2>/dev/null

# Ensure project-env.sh is sourced in both shell configs (idempotent)
SOURCELINE='[ -f /workspace/.claude/project-env.sh ] && source /workspace/.claude/project-env.sh'
grep -qF "$SOURCELINE" ~/.bashrc 2>/dev/null || echo "$SOURCELINE" >>~/.bashrc
grep -qF "$SOURCELINE" ~/.zshrc 2>/dev/null || echo "$SOURCELINE" >>~/.zshrc

# Share .claude.json across containers via the shared claude-config volume.
# If a real file exists (first run), move it into the shared volume then symlink.
if [ -f ~/.claude.json ] && [ ! -L ~/.claude.json ]; then
  mv ~/.claude.json ~/.claude/.claude.json
fi
ln -sf ~/.claude/.claude.json ~/.claude.json

# Inject MCP server configs
if [ -z "${CONTEXT7}" ]; then
  echo "WARNING: CONTEXT7 env var is not set — skipping Context7 MCP injection" >&2
else
  # Ensure the backing file exists (fresh volume on first run)
  [ -f ~/.claude/.claude.json ] || echo '{}' >~/.claude/.claude.json
  jq '.mcpServers.context7 = {"type": "stdio", "command": "npx", "args": ["-y", "@upstash/context7-mcp", "--api-key", env.CONTEXT7]}' \
    ~/.claude/.claude.json >/tmp/claude.json && mv /tmp/claude.json ~/.claude/.claude.json
fi

