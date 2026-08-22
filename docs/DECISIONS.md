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

---

## ADR-009 — Generation vs Verification failure asymmetry (502 Abort vs 200 Recorded Fail-Safe)

**Date:** 2026-08-22

**Status:** Accepted

**Decision:** Draft generation (`generate_pitch` / `POST /drafts`) aborts draft creation and raises `GenerationError` (yielding `502 Bad Gateway` at the HTTP layer per PRD §4.1) when the LLM call fails or returns unparseable schema. No draft record is stored in SQLite. By contrast, verification (`POST /drafts/{id}/verify`) records G5 judge LLM failures as a `200 OK` verdict round with `status: verified_fail` and `passed: false`.

**Justification:** A failed generation attempt produces no usable outreach artifact; persisting broken drafts would pollute the database with incomplete data. Verification, however, is an audit process over an existing draft: a failed judge check must be recorded as an auditable compliance failure (`verified_fail`) rather than aborting the verification pipeline.

**Alternatives considered:**

- *Persist failed draft on generation error:* Pollutes SQLite with corrupted drafts that lack content.
- *Return 502 on verification G5 failure:* Destroys verification audit trail and prevents human review of deterministic rules G1–G4.

---

## ADR-010 — Generator length limit non-enforcement (Decoupling generation from evaluation)

**Date:** 2026-08-22

**Status:** Accepted

**Decision:** `generate_pitch` (`backend/app/services/generator.py`) returns raw LLM text output for SMS and WhatsApp channels without validating, truncating, or rejecting over-limit messages (e.g. text > 160 chars for SMS). Length enforcement is strictly decoupled and delegated to G3 (`check_channel_format`) at verification time.

**Justification:** Preserves separation of concerns (generation synthesizes; verification audits) and audit trail integrity. Failing closed on length during generation would destroy over-length drafts before they can be persisted and flagged, preventing compliance teams from measuring model failure rates on channel constraints.

**Alternatives considered:**

- *Truncate over-length messages at generation time:* Silently alters model output and conceals format violations.
- *Fail closed / raise GenerationError on over-length messages:* Prevents draft creation, destroying audit visibility into LLM channel limit compliance.

---

## ADR-011 — Native Pydantic v2 resolution of Union[EmailPitch, str] without custom discriminators

**Date:** 2026-08-22

**Status:** Accepted

**Decision:** The `generated_pitch: Union[EmailPitch, str]` field on `Draft` relies entirely on Pydantic v2's native structural union resolution (`Draft.model_validate_json()`) without custom union discriminators, field validators, or custom serializers.

**Justification:** Structural typing between `EmailPitch` (a structured object with required `subject` and `body` string keys) and `str` (a primitive string) is completely unambiguous in JSON schema representation. Pydantic v2 attempts object validation against `EmailPitch` first and falls through to `str` for primitive string payloads cleanly. Documented to avoid adding unnecessary custom deserialization logic in future extensions unless ambiguous object-vs-object unions are introduced.

**Alternatives considered:**

- *Tagged union discriminator (e.g., `kind: "email" | "plain"`):* Adds redundant boilerplate since JSON object vs string primitive is already structurally distinct.

---

## ADR-012 — Broaden requires-python from >=3.14 to >=3.10 for CI runner compatibility

**Date:** 2026-08-22

**Status:** Accepted

**Decision:** Loosen `requires-python` in `backend/pyproject.toml` from `>=3.14` to `>=3.10`.

**Justification:** The initial `>=3.14` pin was an environment-specific default from the local dev machine (Python 3.14.0). Codebase audit verified that all app and test code relies exclusively on standard Python 3.10+ features (PEP 585 built-in generics like `list[str]`, `dict[str, Any]`, standard `typing`, standard library `sqlite3` and `json`). Zero Python 3.14-only language features or stdlib APIs are used. Loosening the constraint allows CI runners (e.g. GitHub Actions `setup-python` with Python 3.12) to build and execute the backend without version rejection.

**Alternatives considered:**

- *Require Python 3.14+ in CI:* Fails on standard GitHub Actions runners where Python 3.12 is the primary stable runtime.

---

## ADR-013 — llm_judge hardened against markdown-fence-wrapped responses

**Date:** 2026-08-22

**Status:** Accepted

**Decision:** Harden `check_llm_judge` (`backend/app/guardrails/llm_judge.py`) using two complementary layers:
1. **System Prompt Hardening:** Add explicit instructions prohibiting markdown code blocks (`Do NOT wrap the JSON in markdown code blocks (no ``` or ```json)`).
2. **Defensive Stripping:** Strip leading/trailing markdown code fences from `response_text` prior to calling `json.loads()`.

**Justification:** Discovered during a live Stage 6 walkthrough with a real LLM (`kr/claude-sonnet-4.5` via gateway). Mocked unit tests control the response string format directly and never surfaced this issue. Real models frequently wrap JSON responses in markdown code blocks despite prompt instructions. Without defensive stripping, `json.loads` fails and short-circuits to the generic `unparseable` fail-safe path instead of parsing structured verdicts. A dedicated unit test (`test_markdown_code_fence_stripping` in `backend/tests/guardrails/test_llm_judge.py:230`) verifies that wrapped responses parse cleanly into valid verdicts.

**Alternatives considered:**

- *Prompt change only:* Fragile across different LLM providers or gateway wrappers.
- *Stripping code only:* Leaves system prompt ambiguous for model output formatting.




