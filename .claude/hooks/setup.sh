#!/bin/bash
# Environment setup hook — runs once per session.
# Reads .claude/env.json for explicit config, falls back to auto-detection.
# Writes exports to .claude/project-env.sh, sourced by ~/.bashrc on every Bash call.

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty')
FLAG="/tmp/claude-env-setup-${SESSION_ID}"
ENV_FILE="/workspace/.claude/project-env.sh"
CONFIG_FILE="/workspace/.claude/env.json"

# Run once per session
[ -f "$FLAG" ] && exit 0
[ -n "$SESSION_ID" ] && touch "$FLAG"

# ── Read explicit config ─────────────────────────────────────────

PYTHON_MGR=""
NODE_MGR=""

if [ -f "$CONFIG_FILE" ]; then
  PYTHON_MGR=$(jq -r '.python // empty' "$CONFIG_FILE")
  NODE_MGR=$(jq -r '.node // empty' "$CONFIG_FILE")
fi

# ── Python ───────────────────────────────────────────────────────

VENV_PATH=""
CONDA_ENV=""
ACTIVATE_ENV=""
TEST_CMD=""

resolve_python() {
  local mgr="$1"
  case "$mgr" in
    poetry)
      VENV_PATH=$(poetry env info --path 2>/dev/null || echo ".venv")
      ACTIVATE_ENV="poetry run"
      TEST_CMD="poetry run pytest"
      ;;
    uv)
      VENV_PATH=".venv"
      ACTIVATE_ENV="uv run"
      TEST_CMD="uv run pytest"
      ;;
    pip)
      for d in .venv venv env; do
        [ -f "$d/bin/activate" ] && VENV_PATH="$d" && break
      done
      ACTIVATE_ENV="source ${VENV_PATH:-venv}/bin/activate"
      TEST_CMD="pytest"
      ;;
    conda)
      CONDA_ENV=$(grep 'name:' environment.yml 2>/dev/null | cut -d: -f2 | tr -d ' ')
      ACTIVATE_ENV="conda activate ${CONDA_ENV}"
      TEST_CMD="pytest"
      ;;
    pipenv)
      ACTIVATE_ENV="pipenv run"
      TEST_CMD="pipenv run pytest"
      ;;
  esac
}

if [ -n "$PYTHON_MGR" ]; then
  resolve_python "$PYTHON_MGR"
else
  # Auto-detect
  if [ -f pyproject.toml ] && command -v poetry >/dev/null 2>&1; then
    resolve_python poetry
  elif [ -f pyproject.toml ] && command -v uv >/dev/null 2>&1; then
    resolve_python uv
  elif [ -f Pipfile ] && command -v pipenv >/dev/null 2>&1; then
    resolve_python pipenv
  elif [ -f environment.yml ]; then
    resolve_python conda
  else
    resolve_python pip
  fi
fi

# ── Node ─────────────────────────────────────────────────────────

PKG_MANAGER=""

resolve_node() {
  local mgr="$1"
  case "$mgr" in
    pnpm|yarn|npm) PKG_MANAGER="$mgr" ;;
  esac
}

if [ -n "$NODE_MGR" ]; then
  resolve_node "$NODE_MGR"
elif [ -f package.json ]; then
  if command -v pnpm >/dev/null 2>&1 && [ -f pnpm-lock.yaml ]; then
    resolve_node pnpm
  elif command -v yarn >/dev/null 2>&1 && [ -f yarn.lock ]; then
    resolve_node yarn
  else
    resolve_node npm
  fi
fi

# ── Write project-env.sh (idempotent) ───────────────────────────

NEW_CONTENT=""
[ -n "$VENV_PATH" ]     && NEW_CONTENT+="export VENV_PATH=\"$VENV_PATH\"\n"
[ -n "$CONDA_ENV" ]     && NEW_CONTENT+="export CONDA_ENV=\"$CONDA_ENV\"\n"
[ -n "$PKG_MANAGER" ]   && NEW_CONTENT+="export PKG_MANAGER=\"$PKG_MANAGER\"\n"
[ -n "$TEST_CMD" ]      && NEW_CONTENT+="export TEST_CMD=\"$TEST_CMD\"\n"
[ -n "$ACTIVATE_ENV" ]  && NEW_CONTENT+="export ACTIVATE_ENV=\"$ACTIVATE_ENV\"\n"

OLD_CONTENT=""
[ -f "$ENV_FILE" ] && OLD_CONTENT=$(cat "$ENV_FILE")

RESOLVED=$(printf '%b' "$NEW_CONTENT")
[ "$RESOLVED" != "$OLD_CONTENT" ] && printf '%b' "$NEW_CONTENT" > "$ENV_FILE"

exit 0
