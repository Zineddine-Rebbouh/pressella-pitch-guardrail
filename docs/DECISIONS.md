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

---

## ADR-002 — Separated test directory mirroring app structure

**Date:** 2026-08-21

**Status:** Accepted

**Decision:** Tests live in a dedicated `backend/tests/` directory that mirrors
the `backend/app/` package tree, rather than being colocated alongside each
module (e.g., `app/guardrails/test_pii.py`).

**Justification:** A separated test directory gives a clean boundary between
shipped code and test code — no test files, fixtures, or test-only dependencies
leak into the application package. As Stage 3 onward adds implementation, the
test tree mirrors the app tree one-for-one (e.g., `tests/guardrails/`,
`tests/routes/`), making it straightforward to find the tests for any module.
Pytest's `testpaths = ["tests"]` config (already in `pyproject.toml`) makes
discovery explicit.

**Alternatives considered:**

- *Colocated tests (test file next to source file):* Common in some ecosystems,
  but mixes test and production code in the same directories, complicating
  packaging and increasing the chance of accidentally shipping test fixtures.

---

## ADR-003 — Banned-phrase starter list curated for PR-pitch risk, not generic spam

**Date:** 2026-08-21

**Status:** Accepted

**Decision:** The G2 banned-phrase starter list targets unverifiable
authority/credibility claims common in PR outreach (e.g., "as seen in every
major outlet", "trusted by industry leaders") rather than generic spam-filter
phrases (e.g., "you've been selected", "exclusive deal just for you").

**Justification:** A PR consultancy's compliance risk is fabricated credibility,
not e-commerce spam. The deny-list should reflect the language patterns that
actually appear in — and cause problems for — outbound PR pitches.

---

## ADR-004 — GuardrailVerdict extended with flagged_claims for LLM-as-judge rule

**Date:** 2026-08-22

**Status:** Accepted

**Decision:** GuardrailVerdict extended with `flagged_claims` (`list[FlaggedClaim]`) to support the `llm_judge` rule's structured claim-level feedback, needed for UI-level per-claim explainability.
