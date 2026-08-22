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

## ADR-004 — Word-boundary-aware matching for banned phrases

**Date:** 2026-08-22

**Status:** Accepted

**Decision:** G2 matching uses `re.search(rf"\b{re.escape(phrase)}\b", text, re.IGNORECASE)` — word-boundary anchors (`\b`) plus `re.escape` on each deny-list entry.

**Justification:** Naive substring (`phrase in text.lower()`) caused false positives on word-internal occurrences (e.g., `enact now` triggering `act now`). Caught by `test_substring_false_positive_passes` (`backend/tests/guardrails/test_banned_phrases.py:91`). Boundary-aware regex eliminates that class of bug while `re.escape` prevents list entries containing regex metacharacters (e.g., `100% success rate`) from being misinterpreted.

**Alternatives considered:**

- *Plain substring:* Simpler but over-matches inside unrelated words; rejected after failing test.

---

## ADR-005 — EmailPitch text-join convention for offset reporting

**Date:** 2026-08-22

**Status:** Accepted

**Decision:** For `EmailPitch` inputs, G1 (PII), G2 (banned phrases), and G4 (unsubstantiated claims) join subject and body as `f"{subject}\n{body}"` before scanning. G5 (LLM judge) uses `f"Subject: {subject}\nBody: {body}"` for prompt readability. Reported character offsets are offsets into the joined string, not into body alone.

**Justification:** Provides a single deterministic string for all offset-bearing checks. Tests depend on this exact join — e.g., `test_email_detection_fails` computes `expected_offset = f"{subject}\n{body}".index(pii_str)` (`backend/tests/guardrails/test_pii.py:55`). Changing the separator (e.g., `" "` or `"\n\n"`) would shift every reported offset and break tests; the convention must be documented so nobody "fixes" it.

**Alternatives considered:**

- *Body only:* Would silently miss subject-line violations and under-report positions.
- *Different separator:* Any change breaks offset contract with tests and any future frontend highlighting.

---

## ADR-006 — Unsubstantiated-claims: normalized matching, input traversal, and bare-integer exemption

**Date:** 2026-08-22

**Status:** Accepted

**Decision:** G4 implements three rules codified in PRD §2 G4 and `backend/app/guardrails/unsubstantiated_claims.py:5`:

1. **Normalized matching** — strip `%`, `$`, `,` and normalize `x`/`×` before comparing claim value to input values; compare bare numeric values. Spelled-out numbers out of scope.
2. **Input traversal** — `harvest_input_numbers` checks both recursively stringified values (regex over `str` values) and direct `isinstance(v, (int, float))` on dict values; either path substantiates the claim (`backend/app/guardrails/unsubstantiated_claims.py:17`).
3. **Bare small-integer exemption** — bare integers (no `%`/`$`/`x`/`×` marker) with value `< BARE_INTEGER_EXEMPTION_THRESHOLD` are exempt. Threshold is a named constant `BARE_INTEGER_EXEMPTION_THRESHOLD = 10`, not an inline magic number. Marked small numbers (e.g., `3%`) are never exempt.

**Justification:** Prevents false failures on counting language ("3 easy steps") while still catching material claims ("3% increase", "$50,000", "25 years"). Named constant makes the threshold auditable and changeable without code archaeology; boundary proven by `test_bare_integer_exemption_boundary` (`backend/tests/guardrails/test_unsubstantiated_claims.py:121`).

**Alternatives considered:**

- *Literal string matching:* Would miss equivalent forms (`3x` vs `3×`, `50000` vs `50,000`).
- *Single traversal path (string only or numeric only):* Would miss numbers stored as the other type.
- *No exemption:* Would flag every small counting number, noisy for reviewers.

---

## ADR-007 — LLM-judge: mock boundary and deferred live integration test

**Date:** 2026-08-22

**Status:** Accepted

**Decision:** Unit tests mock the Anthropic call at the client-instantiation boundary (`@patch("app.guardrails.llm_judge.Anthropic")`, `backend/tests/guardrails/test_llm_judge.py:31`), asserting against the structured `GuardrailVerdict` fail-safe contract (PRD §3). A live integration test that hits the real Claude API is deliberately deferred to implementation-adjacent verification, not part of the TDD test-first pass, and not run in CI.

**Justification:** Mocking at `Anthropic` keeps tests deterministic, fast, and free of API keys/network. Every fail-safe branch (malformed JSON, missing fields, non-boolean `passed`, timeout, connection error) is covered without external dependency. Live calls are non-deterministic, incur cost/latency, and would make CI flaky.

**Alternatives considered:**

- *Mock at HTTP layer (httpx/respx):* More brittle to SDK internals; client boundary is the public contract.
- *Live calls in CI:* Rejected — non-determinism and secrets-management cost outweigh value for a PoC gate; manual/later live smoke test covers it.

---

## ADR-008 — flagged_claims filtering: fail safe on first malformed entry

**Date:** 2026-08-22

**Status:** Accepted

**Decision:** In `check_llm_judge` (`backend/app/guardrails/llm_judge.py:113`), iteration over `flagged_claims` validates each entry's shape (`claim: str`, `reason: str`). The first malformed entry causes immediate fail-safe (`passed: false`, `"Judge response schema invalid — failing safe."`), rather than filtering it out and continuing.

**Justification:** A partially-malformed judge response is not trustworthy; silently dropping bad entries and accepting the rest would risk surfacing incomplete or misleading explainability in the UI. Fail-safe on first defect is stricter and matches the PRD's "malformed response must never be silently ignored" principle. Also covers the edge `passed: false` with empty `flagged_claims` (treated as schema-invalid, `backend/app/guardrails/llm_judge.py:132`).

**Alternatives considered:**

- *Filter-then-check (drop malformed, pass if any valid remain):* Would hide model output errors and violate fail-safe intent.
- *Zero-valid-entries-only check:* Would pass a response with one valid + one malformed claim, incorrectly treating it as trustworthy.
