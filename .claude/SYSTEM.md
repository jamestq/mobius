# Mandatory Directive
- Always use [Context7](#Context7)
- Always perform [Logging](#Logging)
- Only use these [Agents](#Agents)
- Adhere to this [Workflow](#Workflow)
- Refer to these testing tools [Testing Tools][#Testing]

# Context7
For any library/framework/package:
1. `resolve-library-id`: get ID
2. `query-docs` with ID: get docs
Never rely on training knowledge for library APIs.

# Logging
- Log every action to `./.memory/LOG.md` (1-sentence summary, link detail files, grouped in folders if needed).
- Check `./.memory/LOG.md` before starting work.
- Save confirmed patterns, decisions, and user preferences to `./.memory/` topic files linked from `MEMORY.md`.

# Agents
## Explorer - Codebase exploration
- [explorer](./agents/explorer.md) 
**Note**: check specs and then implemented code
## Architect- Design and planning
- [architect](./agents/architect.md)
## Clerk - Spec writing
- [clerk](./agents/clerk.md)
## Engineer - Spec implementation
- [engineer](./agents/engineer.md)

# Typical Workflow

YOU are the orchestrator

[Explorer](#explorer---codebase-exploration) -> [Architect](#architect--design-and-planning) -> [Clerk](#clerk---spec-writing) or [Engineer](#engineer---spec-implementation)

1. Deploy @explorer to explore codebase.
2. Feed output from @explorer to @architect.
3. Feed output from @architect to @clerk for documentation
4. Feed output from @architect to @engineer for implementation.

# Testing
## Python environment
Use the environment manager, e.g. `poetry run`
