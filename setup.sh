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
cp -r "$SCRIPT_DIR/.claude" "$TARGET_DIR"
cp -r "$SCRIPT_DIR/.devcontainer" "$TARGET_DIR"
cp -r "$SCRIPT_DIR/.github" "$TARGET_DIR"
cp "$TARGET_DIR/.devcontainer/.gitignore.project" "$TARGET_DIR/.gitignore"

# cd into the isolated environment and run the setup script
cd "$TARGET_DIR"
devcontainer up --workspace-folder .