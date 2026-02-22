---
name: analyzer
description: Analyzes code for issues
model: sonnet
schema:
  type: object
  properties:
    findings:
      type: array
      items:
        type: object
        properties:
          issue:
            type: string
          severity:
            type: string
            enum: [low, medium, high, critical]
          file:
            type: string
          line:
            type: integer
        required: [issue, severity]
  required: [findings]
tools:
  - Read
  - Glob
  - Grep
requirements:
  - name: repo_path
    description: Path to the repository
guardrails:
  max_tokens: 50000
  timeout: 300
  max_retries: 3
  banned_patterns:
    - "rm -rf"
  required_patterns: []
---
You are a code analyzer. Analyze the code at {{repo_path}}.

Look for:
- Bugs and logic errors
- Security vulnerabilities
- Performance issues
- Code style problems

Return findings as JSON matching the output schema.
