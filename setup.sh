#!/bin/bash
# This script is a crude setup script for isolated development environments.
# A more robust solution would be developed soon, but this should work for now.

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

if [ -z "$1" ]; then
    echo "Usage: $0 <target_directory>"
    exit 1
    fi

TARGET_DIR="$1"

# Create the target directory if it doesn't exist
mkdir -p "$TARGET_DIR"

# Copy the relevant folders to the isolated environment
# If CLAUDE.md already exists in the target, append rather than override
if [ -f "$TARGET_DIR/.claude/CLAUDE.md" ]; then
    # Find lines in source not present in target, append only new lines
    NEW_LINES=$(grep -Fxvf "$TARGET_DIR/.claude/CLAUDE.md" "$SCRIPT_DIR/.claude/CLAUDE.md" || true)
    if [ -n "$NEW_LINES" ]; then
        echo >> "$TARGET_DIR/.claude/CLAUDE.md"
        echo "$NEW_LINES" >> "$TARGET_DIR/.claude/CLAUDE.md"
    fi
    # Copy everything else from .claude except CLAUDE.md
    find "$SCRIPT_DIR/.claude" -mindepth 1 -not -name "CLAUDE.md" -exec cp -r {} "$TARGET_DIR/.claude/" \;
else
    cp -r "$SCRIPT_DIR/.claude" "$TARGET_DIR"
fi
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
devcontainer up --workspace-folder .

# if no git repository
if [ ! -d ".git" ]; then
    git init
fi