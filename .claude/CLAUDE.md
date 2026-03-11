## Available Agents
- Software engineering planning: @lead-architect
- Spec writing (deployed by @lead-architect): @specs
- Codebase exploration (specs-first): @explore

## Exploration
When researching the codebase (in plan mode or otherwise), always use @explore to find relevant context before writing code.

## Designing
When designing, always use @lead-architect

## Tool Research with Context7
Always use Context7 for any library, framework, or package documentation:
1. First call `resolve-library-id` to get the library ID
2. Then call `query-docs` with the resolved ID to get up-to-date docs and code examples

DO NOT rely on training knowledge for library APIs — always verify with Context7.

# Persistent Memory - MEMORY.md
Memory directory: `./.memory/` (persists across conversations, local to project only). Consult before starting; update as you learn.

`MEMORY.md` loads into system prompt. Use topic files for details, link from MEMORY.md. Organize by topic, not chronology.

- **Save**: confirmed patterns, architecture decisions, file paths, project structure, user preferences, recurring solutions.
- **Skip**: session-specific state, unverified info, CLAUDE.md duplicates, single-file speculation.
- **User requests**: save immediately when asked to remember; remove when asked to forget. Scope to this project.

Your MEMORY.md may be empty. 
When you notice a pattern worth preserving across sessions, save it here. 
Anything in MEMORY.md will be included in your system prompt next time.

## LOGGING
- **Logging** — always logged what you have done in `./.memory/LOG.md`.
- **Referencing** - always check `./.memory/LOG.md`.

