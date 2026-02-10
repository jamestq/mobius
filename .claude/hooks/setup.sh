#!/bin/bash
# Detect project environment and testing setup.
# Writes export statements to .claude/project-env.sh so they are
# picked up by every Bash tool call via ~/.bashrc sourcing.

ENV_FILE="/workspace/.claude/project-env.sh"

# ── Detect environment ──────────────────────────────────────────

# Python virtual environment
VENV_PATH=""
CONDA_ENV=""
if [ -f .venv/bin/activate ]; then
    VENV_PATH=.venv
elif [ -f venv/bin/activate ]; then
    VENV_PATH=venv
elif [ -f env/bin/activate ]; then
    VENV_PATH=env
elif [ -f environment.yml ]; then
    CONDA_ENV=$(grep 'name:' environment.yml | cut -d: -f2 | tr -d ' ')
fi

# Node.js package manager
PKG_MANAGER=""
if [ -f package.json ]; then
    if command -v pnpm >/dev/null 2>&1 && [ -f pnpm-lock.yaml ]; then
        PKG_MANAGER=pnpm
    elif command -v yarn >/dev/null 2>&1 && [ -f yarn.lock ]; then
        PKG_MANAGER=yarn
    else
        PKG_MANAGER=npm
    fi
fi

# Test framework detection
TEST_FRAMEWORK=""
TEST_CMD=""
if [ -f pytest.ini ] || grep -q pytest pyproject.toml 2>/dev/null; then
    TEST_FRAMEWORK=pytest
    TEST_CMD=pytest
elif [ -f package.json ] && grep -q '"test"' package.json; then
    TEST_FRAMEWORK=jest
    TEST_CMD="${PKG_MANAGER:-npm} test"
elif [ -f Cargo.toml ]; then
    TEST_FRAMEWORK=cargo
    TEST_CMD="cargo test"
elif [ -f go.mod ]; then
    TEST_FRAMEWORK=go
    TEST_CMD="go test ./..."
elif [ -f Gemfile ]; then
    TEST_FRAMEWORK=rspec
    TEST_CMD="bundle exec rspec"
elif [ -f pom.xml ]; then
    TEST_FRAMEWORK=maven
    TEST_CMD="mvn test"
elif [ -f build.gradle ] || [ -f build.gradle.kts ]; then
    TEST_FRAMEWORK=gradle
    TEST_CMD="gradle test"
fi

# Activate environment command
ACTIVATE_ENV=""
if [ -n "$VENV_PATH" ]; then
    ACTIVATE_ENV="source $VENV_PATH/bin/activate"
elif [ -n "$CONDA_ENV" ]; then
    ACTIVATE_ENV="conda activate $CONDA_ENV"
fi

# ── Build env file content ──────────────────────────────────────

NEW_CONTENT=""
[ -n "$VENV_PATH" ]      && NEW_CONTENT="${NEW_CONTENT}export VENV_PATH=\"$VENV_PATH\"
"
[ -n "$CONDA_ENV" ]      && NEW_CONTENT="${NEW_CONTENT}export CONDA_ENV=\"$CONDA_ENV\"
"
[ -n "$PKG_MANAGER" ]    && NEW_CONTENT="${NEW_CONTENT}export PKG_MANAGER=\"$PKG_MANAGER\"
"
[ -n "$TEST_FRAMEWORK" ] && NEW_CONTENT="${NEW_CONTENT}export TEST_FRAMEWORK=\"$TEST_FRAMEWORK\"
"
[ -n "$TEST_CMD" ]       && NEW_CONTENT="${NEW_CONTENT}export TEST_CMD=\"$TEST_CMD\"
"
[ -n "$ACTIVATE_ENV" ]   && NEW_CONTENT="${NEW_CONTENT}export ACTIVATE_ENV=\"$ACTIVATE_ENV\"
"

# ── Write only if changed (idempotent) ──────────────────────────

OLD_CONTENT=""
[ -f "$ENV_FILE" ] && OLD_CONTENT=$(cat "$ENV_FILE")

if [ "$NEW_CONTENT" != "$OLD_CONTENT" ]; then
    printf '%s' "$NEW_CONTENT" > "$ENV_FILE"
fi
