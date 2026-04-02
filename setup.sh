#!/bin/bash
# This script is a crude setup script for isolated development environments.
# A more robust solution would be developed soon, but this should work for now.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# Check environment variables
TZ="${TZ:-Australia/Sydney}"
GIT_DELTA_VERSION="${GIT_DELTA_VERSION:-0.18.2}"
ZSH_IN_DOCKER_VERSION="${ZSH_IN_DOCKER_VERSION:-1.2.0}"
BASE_IMAGE="${BASE_IMAGE:-devcontainer-base:latest}"
DEVCONTAINER=true

MODE="vscode"
REBUILD=false
POSITIONAL=()

for arg in "$@"; do
    case $arg in
        --nvim)    MODE="nvim" ;;
        --rebuild) REBUILD=true ;;
        *)         POSITIONAL+=("$arg") ;;
    esac
done

if [ "${#POSITIONAL[@]}" -eq 0 ]; then
    echo "Usage: $0 <target_directory> [--nvim] [--rebuild]"
    exit 1
fi

TARGET_DIR="${POSITIONAL[0]}"

# Create the target directory if it doesn't exist
mkdir -p "$TARGET_DIR"

# Create volumes if don't exist yet
volumes=(claude-config bash-history poetry-cache pip-cache npm-cache)
for v in "${volumes[@]}"; do
  if docker volume inspect "$v" >/dev/null 2>&1; then
    echo "[exists] $v"
  else
    echo "[missing] $v -> creating"
    docker volume create "$v" >/dev/null
    echo "[created] $v"
  fi
done

# Build the base image if it doesn't already exist (or if --rebuild is passed)
if [[ "$REBUILD" == true ]] || ! docker image inspect "$BASE_IMAGE" &>/dev/null; then
    echo "Building base image: $BASE_IMAGE ..."
    docker build \
        -f "$SCRIPT_DIR/.devcontainer/Dockerfile.base" \
        --build-arg TZ="$TZ" \
        --build-arg GIT_DELTA_VERSION="$GIT_DELTA_VERSION" \
        --build-arg ZSH_IN_DOCKER_VERSION="$ZSH_IN_DOCKER_VERSION" \
        -t "$BASE_IMAGE" \
        "$SCRIPT_DIR/.devcontainer"
    echo "Base image built: $BASE_IMAGE"
else
    echo "Reusing existing base image: $BASE_IMAGE"
fi

# Copy the relevant folders to the isolated environment
cp -r "$SCRIPT_DIR/.claude" "$TARGET_DIR"
cp -r "$SCRIPT_DIR/.devcontainer" "$TARGET_DIR"
if [ ! -f "$TARGET_DIR/.devcontainer/.env" ]; then
    mv "$TARGET_DIR/.devcontainer/.env.sample" "$TARGET_DIR/.devcontainer/.env"
fi
cp -r "$SCRIPT_DIR/.github" "$TARGET_DIR"

# Update devcontainer name to match the target directory
DIR_NAME=$(basename "$TARGET_DIR")
sed "s/\"name\": \"Development Sandbox\"/\"name\": \"$DIR_NAME\"/" "$TARGET_DIR/.devcontainer/devcontainer.json" > "$TARGET_DIR/.devcontainer/devcontainer.json.tmp" && mv "$TARGET_DIR/.devcontainer/devcontainer.json.tmp" "$TARGET_DIR/.devcontainer/devcontainer.json"

# If .gitignore already exists, only append lines not already present
if [ -f "$TARGET_DIR/.gitignore" ]; then
    # Find lines in source not present in target, append only new lines
    NEW_LINES=$(grep -Fxvf "$TARGET_DIR/.gitignore" "$SCRIPT_DIR/.devcontainer/.gitignore.project" || true)
    if [ -n "$NEW_LINES" ]; then
        echo >> "$TARGET_DIR/.gitignore"
        echo "$NEW_LINES" >> "$TARGET_DIR/.gitignore"
    fi
else
    cp "$SCRIPT_DIR/.devcontainer/.gitignore.project" "$TARGET_DIR/.gitignore"
fi

# cd into the isolated environment and run the setup script
cd "$TARGET_DIR"

if [ ! -d ".git" ]; then
    git init
fi

if [[ "$MODE" == "nvim" ]]; then
    echo "Starting Neovim CLI environment via Docker Compose..."
    echo "Run 'bash .devcontainer/entry.sh' once inside the container to complete setup."
    docker compose -f .devcontainer/docker-compose.nvim.yml -p "$DIR_NAME" run --rm dev zsh
else
    devcontainer up --workspace-folder .
fi
