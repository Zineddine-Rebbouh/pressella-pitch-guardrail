# Architecture Decision Records

This log tracks key technical decisions made during the development of the
Pitch Guardrail & Eval Harness PoC, in chronological order.

---

## ADR-001 — Use SQLite (file-backed) over pure in-memory storage

**Date:** 2026-08-21

**Status:** Accepted

**Decision:** Use a file-backed SQLite database (`guardrail.db`) as the sole
data store.

**Justification:** SQLite persists data across server restarts, lets reviewers
inspect the database with standard tooling (e.g., `sqlite3` CLI, DB Browser),
and costs nothing extra — while remaining zero-config and single-file, fitting
the PoC scope perfectly.

**Alternatives considered:**

- *Pure in-memory dict/list:* Simpler, but data is lost on every restart,
  making it impossible to review historical drafts or demo the audit trail.
- *PostgreSQL:* Overkill for a single-user PoC; adds setup complexity with no
  benefit at this scale.
