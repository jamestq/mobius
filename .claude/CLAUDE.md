# Directives
- [Context7](#Context7)
- [Logging](#Logging)
- [Agents](#Agents)
- [Memory](#Memory)
- [Paths](#Paths)
- Always create tasks to track your progress and blockers

# Context7
For any library/framework/package:
1. `resolve-library-id`: get ID
2. `query-docs` with ID: get docs
Never rely on training knowledge for library APIs.

# Logging
- Log every action to `./.memory/LOG.md` (1-sentence summary, link detail files, grouped in folders if needed).
- Check `./.memory/LOG.md` before starting work.
- Save confirmed patterns, decisions, and user preferences to `./.memory/` topic files linked from `MEMORY.md`.

# Memory
When you have new memory to save, ask the user before saving and always save to this project directory (`./.claude/CLAUDE.md`), never to the auto-memory system (`~/.claude/projects/`).

# Paths
All directory/file paths must be relative to the project/workspace root using `./` prefix (e.g., `./.specs/`, `./.memory/LOG.md`, `./tests/unit/`).

# Agents
Use these agents by default:
- Codebase exploration (specs-first): [explorer](./agents/explorer.md)
- Design and planning: [architect](./agents/architect.md)
- Spec writing: [clerk](./agents/clerk.md) 
- Spec implementation: [engineer](./agents/engineer.md)
