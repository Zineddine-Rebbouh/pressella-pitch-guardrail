# Product Requirements Document — Pitch Guardrail & Eval Harness

## 1. Overview

This service takes a PR outreach draft (a prospect profile + a campaign brief),
has an LLM generate a pitch message, then runs it through a guardrail layer
before a human can approve it to send. The guardrail layer consists of
**4 deterministic checks** and **1 LLM-as-judge check**. Every check returns a
pass/fail verdict and a human-readable reason — the system is fully auditable
with no black-box decisions. A human reviewer sees the aggregated verdicts and
makes the final approve/reject call. Sending is always mocked (logged, never
actually delivered).

**Stack:** Python / FastAPI backend, TypeScript / Next.js frontend, Pytest for
testing, SQLite for storage.

---

## 2. Guardrail Rules — Deterministic

### G1 — PII / Compliance Check

**What it catches:** Personal identifiers that must never appear in outbound
outreach messages.

**How it works:** The check scans the generated pitch text for patterns that
match:

- Social Security Numbers (e.g., `XXX-XX-XXXX`)
- Email addresses
- Phone numbers (common North-American and international formats)
- Credit card numbers (13–19 digit sequences matching Luhn-checkable patterns)

If any pattern matches, the check **fails**. The reason string lists every
matched pattern category and the approximate position in the text where it was
found (e.g., "Email address detected at character 142"). Multiple matches
produce multiple entries.

### G2 — Banned Phrases

**What it catches:** Language that is misleading, high-pressure, or could
expose the sender to regulatory risk.

**How it works:** The check maintains a configurable deny-list of phrases.
Matching is **case-insensitive** and matches whole phrases (not substrings of
unrelated words). If the pitch contains any denied phrase, the check **fails**
and reports every match with the phrase and its position in the text.

**Starter deny-list:**

| Phrase |
|---|
| guaranteed ROI |
| risk-free |
| 100% success rate |
| no obligation |
| act now |
| limited time offer |
| you've been selected |
| exclusive deal just for you |

The list is intended to be extended over time via configuration, not code
changes.

### G3 — Channel Format / Length

**What it catches:** Drafts that violate the structural or length constraints of
their target outreach channel.

**How it works:** Each supported channel has defined limits. When the draft is
verified, its content is measured against the limits for its declared channel.
If any limit is exceeded, the check **fails** and reports which limit was
exceeded and by how much.

| Channel | Constraints |
|---|---|
| **Email** | Subject line ≤ 100 characters; body ≤ 2 000 characters. Both fields must be present. |
| **SMS** | Total message ≤ 160 characters. |
| **WhatsApp** | Total message ≤ 1 000 characters. |

### G4 — Unsubstantiated Numeric Claims

**What it catches:** Numbers, percentages, dollar amounts, or multiplier claims
(e.g., "3× improvement") in the pitch that cannot be traced back to the input
data.

**How it works:** The check first extracts all numeric claims from the generated
pitch using pattern matching (percentages like "25%", dollar amounts like "$1M",
multipliers like "3×" or "3x", and bare large numbers). It then checks whether
each extracted claim also appears in the prospect profile or campaign brief that
was supplied as input. A claim is considered **substantiated** if the same
numeric value appears in the input data. Any claim that is present in the pitch
but absent from the inputs is flagged as unsubstantiated, and the check
**fails**. The reason string lists each unsubstantiated claim.

---

## 3. Guardrail Rule — LLM-as-Judge

### G5 — Tone & Claim Traceability

**What it evaluates:**

1. **Tone alignment:** Whether the pitch's tone (professional, casual, urgent,
   empathetic, etc.) matches the intent described in the campaign brief.
2. **Claim traceability:** Whether every factual claim made in the pitch can be
   traced back to a specific piece of data in the prospect profile or campaign
   brief.

**Inputs:**

- The generated pitch text
- The prospect profile (JSON)
- The campaign brief (JSON)

**Expected output (structured JSON):**

```
{
  "passed": true | false,
  "reason": "free-text explanation of the overall assessment",
  "flagged_claims": [
    {
      "claim": "the verbatim claim text from the pitch",
      "reason": "why it could not be traced or why the tone is off"
    }
  ]
}
```

`flagged_claims` may be empty when the check passes. When it fails, at least one
entry should be present.

**Fail-safe behavior:**

The LLM judge is an external, non-deterministic dependency. The following
conditions are all treated as a **hard failure** (the check does NOT pass):

| Condition | Recorded reason |
|---|---|
| Response is not valid JSON | "Judge response was malformed or unparseable — failing safe." |
| Response JSON is missing required fields (`passed`, `reason`) | "Judge response schema invalid — failing safe." |
| LLM call times out | "Judge call timed out — failing safe." |
| LLM returns an HTTP error or is unreachable | "Judge call failed ({error detail}) — failing safe." |
| `passed` field is not a boolean | "Judge response schema invalid — failing safe." |

In every failure case the check is recorded in the verdict list with
`passed: false` and the appropriate reason. **A malformed judge response must
never be silently ignored or defaulted to pass.**

---

## 4. API Operations

### 4.1 — Generate Draft

| | |
|---|---|
| **Method + Path** | `POST /drafts` |
| **Inputs** | A JSON body containing: `prospect_profile` (object — the prospect's company, role, industry, and any relevant data points), `campaign_brief` (object — the campaign's goal, tone, key talking points, and any supporting stats), `channel` (string enum: `"email"`, `"sms"`, `"whatsapp"`). |
| **Behavior** | Sends the prospect profile and campaign brief to an LLM with a system prompt instructing it to produce a pitch message appropriate for the specified channel. Stores the result as a new draft record with status `pending_verification`. Does **not** run any guardrail checks — that is a separate step. |
| **Outputs** | `201 Created` — the full draft record (see §5 for shape). |
| **Error cases** | `422` if required fields are missing or `channel` is not a valid enum value. `502` if the LLM call fails (the draft is not created). |

### 4.2 — Verify Draft

| | |
|---|---|
| **Method + Path** | `POST /drafts/{id}/verify` |
| **Inputs** | `id` (path parameter — UUID of an existing draft). No request body. |
| **Behavior** | Retrieves the draft, then runs all 5 guardrail checks (G1–G5) against it. Each check produces a verdict object `{rule, passed, reason}`. The overall status is set to `verified_pass` if **all 5** checks pass, otherwise `verified_fail`. The verdicts are stored on the draft record. Re-running verify on an already-verified draft re-runs all checks and overwrites previous verdicts. |
| **Outputs** | `200 OK` — the updated draft record, including the `guardrail_verdicts` list. |
| **Error cases** | `404` if the draft ID does not exist. `502` if the LLM-judge call (G5) fails (the check is still recorded as a failure per the fail-safe rule; the endpoint itself still returns `200` with the verdict). |

### 4.3 — Retrieve Draft

| | |
|---|---|
| **Method + Path** | `GET /drafts/{id}` |
| **Inputs** | `id` (path parameter — UUID of an existing draft). |
| **Behavior** | Returns the full draft record, including guardrail verdicts (if verification has been run) and human decision (if one has been recorded). Read-only; no side effects. |
| **Outputs** | `200 OK` — the full draft record. |
| **Error cases** | `404` if the draft ID does not exist. |

### 4.4 — Record Human Decision

| | |
|---|---|
| **Method + Path** | `POST /drafts/{id}/decision` |
| **Inputs** | `id` (path parameter — UUID). JSON body containing: `decision` (string enum: `"approve"` or `"reject"`), `note` (optional string — reviewer's free-text comment). |
| **Behavior** | Records the human reviewer's decision on the draft. If `decision` is `"approve"`, the status moves to `approved` and a mock send is logged (a log line is written; no real message is sent). If `decision` is `"reject"`, the status moves to `rejected`. A decision can be recorded when the draft is in `verified_pass` or `verified_fail` status (humans can override a guardrail failure). Recording a decision on a draft that is already `approved` or `rejected` is idempotent if the same decision is sent, or returns an error if a different decision is sent. |
| **Outputs** | `200 OK` — the updated draft record. |
| **Error cases** | `404` if the draft ID does not exist. `409 Conflict` if a different decision has already been recorded. `422` if the draft has not been verified yet (`pending_verification` status). |

---

## 5. Draft Data Shape

A single draft record contains the following fields:

| Field | Type | Description |
|---|---|---|
| `id` | UUID string | Unique identifier, generated server-side. |
| `created_at` | ISO 8601 timestamp | When the draft was created. |
| `channel` | enum: `email`, `sms`, `whatsapp` | The target outreach channel. |
| `prospect_profile` | JSON object | The input prospect data as supplied by the caller. |
| `campaign_brief` | JSON object | The input campaign brief as supplied by the caller. |
| `generated_pitch` | string or object | The LLM-produced message. For `email` channel this is an object with `subject` (string) and `body` (string). For `sms` and `whatsapp` this is a plain string. |
| `status` | enum: `pending_verification`, `verified_pass`, `verified_fail`, `approved`, `rejected` | Current lifecycle state. |
| `guardrail_verdicts` | list of `{rule: string, passed: boolean, reason: string}` | One entry per guardrail check (G1–G5). Empty list until verification is run. |
| `human_decision` | nullable object: `{decision: "approve" \| "reject", note: string \| null, decided_at: ISO 8601 timestamp}` | Null until a human records a decision. |

---

## 6. Out of Scope

The following are explicitly **not** part of this PoC:

- **No real sending.** Twilio, HubSpot, SendGrid, WhatsApp Business API — all
  integrations are mocked. An "approved" draft results in a log entry, not an
  actual delivered message.
- **No authentication or authorization.** All endpoints are open. There is no
  login, no API keys, no role-based access.
- **No multi-user / multi-tenant support.** The system assumes a single user.
  There are no user accounts, no team workspaces, no permission boundaries.
- **No persistence beyond SQLite.** No Postgres, no cloud-hosted database, no
  migration framework. SQLite is the only data store.
- **No CI/CD pipeline.** Continuous integration and deployment are out of scope
  for this PoC; they may be added in a later stage.
- **No rate limiting or quota management.** LLM calls are unbounded; there is no
  token budget or request throttling.
