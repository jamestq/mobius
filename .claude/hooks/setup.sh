#!/bin/bash
# Detect project environment and testing setup

# Python virtual environment
if [ -f .venv/bin/activate ]; then
    echo "VENV_PATH=.venv"
elif [ -f venv/bin/activate ]; then
    echo "VENV_PATH=venv"
elif [ -f env/bin/activate ]; then
    echo "VENV_PATH=env"
elif [ -f environment.yml ]; then
    CONDA_ENV=$(grep 'name:' environment.yml | cut -d: -f2 | tr -d ' ')
    echo "CONDA_ENV=$CONDA_ENV"
fi

# Node.js package manager
if [ -f package.json ]; then
    if command -v pnpm >/dev/null 2>&1 && [ -f pnpm-lock.yaml ]; then
        echo "PKG_MANAGER=pnpm"
    elif command -v yarn >/dev/null 2>&1 && [ -f yarn.lock ]; then
        echo "PKG_MANAGER=yarn"
    else
        echo "PKG_MANAGER=npm"
    fi
fi

# Test framework detection
if [ -f pytest.ini ] || grep -q pytest pyproject.toml 2>/dev/null; then
    echo "TEST_FRAMEWORK=pytest"
    echo "TEST_CMD=pytest"
elif [ -f package.json ] && grep -q '"test"' package.json; then
    PKG_MGR=${PKG_MANAGER:-npm}
    echo "TEST_FRAMEWORK=jest"  # or mocha, detect from package.json
    echo "TEST_CMD=$PKG_MGR test"
elif [ -f Cargo.toml ]; then
    echo "TEST_FRAMEWORK=cargo"
    echo "TEST_CMD=cargo test"
elif [ -f go.mod ]; then
    echo "TEST_FRAMEWORK=go"
    echo "TEST_CMD=go test ./..."
elif [ -f Gemfile ]; then
    echo "TEST_FRAMEWORK=rspec"
    echo "TEST_CMD=bundle exec rspec"
elif [ -f pom.xml ]; then
    echo "TEST_FRAMEWORK=maven"
    echo "TEST_CMD=mvn test"
elif [ -f build.gradle ] || [ -f build.gradle.kts ]; then
    echo "TEST_FRAMEWORK=gradle"
    echo "TEST_CMD=gradle test"
fi

# Activate environment function
if [ -n "$VENV_PATH" ]; then
    echo "ACTIVATE_ENV=source $VENV_PATH/bin/activate"
elif [ -n "$CONDA_ENV" ]; then
    echo "ACTIVATE_ENV=conda activate $CONDA_ENV"
fi