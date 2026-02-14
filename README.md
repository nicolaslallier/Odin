# Odin

This repo uses Cursor as the main brain: the agent acts as **Architect** and **Product Owner**, enforcing a strict process for non-trivial changes.

## Operating Model

- **Product Owner**: Problem definition, goals, acceptance criteria, prioritization. Source of truth: `docs/product/`.
- **Architect**: Technical decisions, tradeoffs, system design. Significant decisions: `docs/architecture/adr/`.

For non-trivial work (new features, refactors, infra), the agent will:

1. Draft PRD section + acceptance criteria
2. Propose architecture; create ADR when significant
3. Define test plan and rollout/observability
4. Only then proceed to implementation

## Docs

| Location | Purpose |
|----------|---------|
| `docs/product/backlog.md` | Prioritized backlog |
| `docs/product/roadmap.md` | High-level roadmap |
| `docs/product/prd-template.md` | PRD template |
| `docs/architecture/architecture-overview.md` | System overview |
| `docs/architecture/adr/` | Architecture Decision Records |

## GitHub

- **PR template**: `.github/pull_request_template.md` — enforces AC, test plan, docs
- **Issue templates**: `.github/ISSUE_TEMPLATE/` — feature requests, bug reports

## Rules

The always-on rule is in `.cursor/rules/architect-po.mdc`.
