# Mandatory Directive
- Always use [Context7](#Context7)
- Always perform [Logging](#Logging)
- Only use these [Agents](#Agents)

# Context7
For any library/framework/package:
1. `resolve-library-id`: get ID
2. `query-docs` with ID: get docs
Never rely on training knowledge for library APIs.

# Logging
- Log every action to `.memory/LOG.md` (1-sentence summary, link detail files, grouped in folders if needed).
- Check `.memory/LOG.md` before starting work.
- Save confirmed patterns, decisions, and user preferences to `.memory/` topic files linked from `MEMORY.md`.

# Agents
- Codebase exploration (specs-first): @explorer
- Design and planning: @architect
- Spec writing (deployed by @architect): @clerk
- Spec implementation (deployed by @architect): @engineer
