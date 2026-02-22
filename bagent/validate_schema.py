#!/usr/bin/env python3
"""Standalone JSON schema validator. Copied into pipeline output directories at build time.

Usage: python3 validate_schema.py <schema.json> [input.json]
  - If input.json is omitted, reads JSON from stdin.
  - Exits 0 if valid, exits 1 with error message if invalid.
"""

import json
import sys


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 validate_schema.py <schema.json> [input.json]", file=sys.stderr)
        sys.exit(2)

    schema_path = sys.argv[1]

    try:
        with open(schema_path) as f:
            schema = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"Error reading schema file: {e}", file=sys.stderr)
        sys.exit(2)

    # Read input JSON
    if len(sys.argv) >= 3:
        try:
            with open(sys.argv[2]) as f:
                data_text = f.read()
        except OSError as e:
            print(f"Error reading input file: {e}", file=sys.stderr)
            sys.exit(2)
    else:
        data_text = sys.stdin.read()

    try:
        data = json.loads(data_text)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    # Try to import jsonschema
    try:
        import jsonschema
    except ImportError:
        print(
            "Error: 'jsonschema' package is not installed.\n"
            "Install it with: pip install jsonschema",
            file=sys.stderr,
        )
        sys.exit(2)

    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as e:
        print(f"Validation error: {e.message}", file=sys.stderr)
        sys.exit(1)

    # Valid - exit 0 silently


if __name__ == "__main__":
    main()
