# Bagent Specifications
- Builder: Python CLI (Typer), reads agent .md files (YAML frontmatter + prompt) and pipeline .yaml configs, resolves missing requirements via interactive prompts, generates self-contained pipeline directory
- Pipeline: Fully autonomous, non-interactive bash. entry.sh takes task as string or file, runs agents sequentially via claude -p, enforces JSON schema on all outputs, handles revision loops, saves everything to runs/<run_id>/, state tracking, --resume support, stops on failure
- Agents: Reusable across pipelines, two types (agent with tools, prompt-only without), YAML frontmatter defines schema, tools, requirements, and guardrails
- Multiple pipelines: Different configs for different scopes, each generates its own entry.sh
- Guardrails: Defined at agent-level and pipeline-step-level, merged with stricter-wins for scalars, list concatenation for arrays. Includes token limits, timeouts, banned/required patterns, post-validation scripts
- Task input: String or file path