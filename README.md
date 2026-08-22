# Pressella Pitch Guardrail & Evaluation Harness

[![CI Workflow](https://github.com/Zineddine-Rebbouh/pressella-pitch-guardrail/actions/workflows/ci.yml/badge.svg)](https://github.com/Zineddine-Rebbouh/pressella-pitch-guardrail/actions)

A production-grade outbound PR pitch generation and compliance evaluation harness. Pressella allows PR teams to generate targeted outreach pitches across multiple channels (`email`, `sms`, `whatsapp`), run them through a 5-layer automated guardrail verification pipeline, and review verdicts in an editorial compliance audit console.

---

## Architecture & Lifecycle Flow

The application follows a strict compliance-first lifecycle where every generated draft must undergo multi-rule automated verification before a human decision can be recorded:

```
[ Intake Form ] ──► [ Generate Pitch ] ──► [ SQLite Store ]
                           │ (502 on error)       │
                           ▼                      ▼
                  [ 5-Guardrail Pipeline ] ◄──────┘
                           │ (Append-only Round)
                           ▼
                  [ Review Console UI ] ──► [ Human Decision ] (Immutability Enforced)
```

### 1. Pitch Intake & Generation (`POST /drafts`)
- Accepts structured campaign briefs (Company, Target Audience, Industry, Value Proposition, Tone, Key Differentiators).
- Calls Anthropic Claude (`kr/claude-sonnet-4.5`) to generate channel-specific pitches (`EMAIL`, `SMS`, `WHATSAPP`).
- **Fail-Fast Error Handling**: If LLM generation fails or times out, the backend returns `502 Bad Gateway` and aborts. No unverified or broken draft is persisted in SQLite.

### 2. Multi-Rule Guardrail Verification (`POST /drafts/{id}/verify`)
Executes all 5 guardrail rules sequentially **without short-circuiting**, recording an append-only verification round into SQLite:

- **G1 — PII / Compliance Check (`pii`)**: Scans for SSNs, email addresses, phone numbers, and credit card numbers (with Luhn validation). Reports exact character offsets into the joined pitch text.
- **G2 — Banned Phrases (`banned_phrases`)**: Detects high-risk promotional language using word-boundary-anchored regex (`\b`) to eliminate substring false positives.
- **G3 — Channel Constraints (`channel_format`)**: Audits character limits (SMS ≤160, WhatsApp ≤1000) and required structure (Email `subject` + `body`).
- **G4 — Unsubstantiated Numeric Claims (`unsubstantiated_claims`)**: Extracts numeric claims (%, $, multipliers like `3x`/`3×`, bare numbers) and cross-checks them against input brief/profile data. Normalizes formatting and exempts bare integers < 10 to avoid false positives on counting language ("3 easy steps").
- **G5 — LLM Tone & Claim Traceability (`llm_judge`)**: Uses Claude as an independent compliance reviewer. Hardened with double-layer prompt instructions and defensive code-block stripping to prevent unparseable markdown responses.

### 3. Human Decision & State Immutability (`POST /drafts/{id}/decision`)
- Reviewers approve or reject verified drafts in the console interface.
- **Strict Immutability (`409 Conflict`)**: A decision can only be made if status is `verified_pass` or `verified_fail`. Once decided (`approved` or `rejected`), the state machine locks the draft permanently — subsequent decision requests return `409 Conflict`.

### 4. Review Console UI
- **Design Aesthetic**: Built as an *Editorial Compliance Audit Console* using Playfair Display typography, warm off-white editorial backgrounds, HSL dark contrast panels, and color-coded status badges.
- **Interactive Verification**: Displays pitch content alongside real-time guardrail verdict breakdowns, flagged claims, and append-only verification history.

---

## Real-World Findings: Bugs & Defects Caught by TDD & Testing

This project prioritizes professional skepticism toward AI outputs and evaluation logic. Development surfaced 5 concrete real-world defects caught by unit tests and live execution:

1. **Banned-Phrase Substring False Positives (ADR-004)**  
   *Discovery:* Naive substring search (`phrase in text`) caused valid words like `"enact now"` to trigger the banned phrase `"act now"`.  
   *Fix:* Upgraded G2 matching to word-boundary-anchored regex (`\b{phrase}\b`).

2. **PII Character Offset Misalignment (ADR-005)**  
   *Discovery:* Multi-field email pitches (`subject` + `body`) produced inconsistent character offsets when scanner logic ran against fields individually.  
   *Fix:* Standardized deterministic string joining (`f"{subject}\n{body}"`), ensuring reported offsets align 1:1 with UI highlighting contracts.

3. **Unsubstantiated Claims Decoy Blindness & Counting Noise (ADR-006)**  
   *Discovery:* Literal string matching missed equivalent multipliers (`3x` vs `3×`, `$50,000` vs `$50000`), while flagging innocent counting language ("3 simple steps").  
   *Fix:* Implemented numeric value normalization and added a bare-integer exemption threshold (`BARE_INTEGER_EXEMPTION_THRESHOLD = 10`).

4. **LLM Judge Schema Invariant Failures (ADR-008)**  
   *Discovery:* Models occasionally returned `passed: false` with an empty `flagged_claims` list, violating the audit explainability contract.  
   *Fix:* Added explicit schema invariant validation — any failed verdict without at least one flagged claim fails safe immediately as schema-invalid.

5. **Live Markdown-Fence LLM Response Parsing Failure (ADR-013)**  
   *Discovery:* During live Stage 6 testing against the real LLM gateway (`kr/claude-sonnet-4.5`), the judge model wrapped its JSON response in ```json ... ``` code fences, causing `json.loads` to throw a `JSONDecodeError`.  
   *Fix:* Hardened the system prompt with explicit raw-JSON instructions and implemented defensive markdown block stripping in Python before parsing. Verified by dedicated unit test `test_markdown_code_fence_stripping`.

---

## How to Run Locally

### Prerequisites
- Python 3.10+ (tested on Python 3.14.0)
- Node.js 18+ and npm
- `uv` package manager (optional, standard `pip` works)

### 1. Environment Setup
Create a `.env` file in `backend/`:

```env
ANTHROPIC_API_KEY=your_api_key_here
ANTHROPIC_BASE_URL=http://localhost:20128/v1  # Or default Anthropic API endpoint
```

### 2. Running the Backend
From the root directory:

```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The backend health check is accessible at `http://localhost:8000/health`.

### 3. Running the Frontend
In a separate terminal:

```bash
cd frontend
npm run dev
```

Open `http://localhost:3000` to launch the Pitch Guardrail Review Console.

### 4. Running Tests
Run the full unit test suite (80 tests):

```bash
cd backend
python -m pytest
```

To run non-integration tests (used in CI):

```bash
python -m pytest -m "not integration"
```

---

## What I'd Do Next (Production Roadmap)

1. **Confidence-Tiered Fail-Safe Reporting**  
   Distinguish raw LLM parsing failures (e.g. timeout / network / malformed output) from policy rule violations in the UI. Provide visual indicators so reviewers know whether a draft failed due to compliance content or technical infrastructure issues.

2. **Externalized Deny-List Management**  
   Move the G2 banned-phrase starter list from code constants to a dynamic database table or configuration service (YAML/Redis), allowing compliance officers to update regex rules at runtime without code releases.

3. **Advanced Semantic Claim Extraction (G4 Upgrade)**  
   Upgrade G4 from regex pattern matching to spaCy NER / dependency parsing to extract implicit numeric claims ("doubled our revenue", "forty percent growth") and handle range comparisons ("between $10k and $50k").

4. **Visual Character-Offset Overlay in Review Console**  
   Render interactive inline highlight overlays in the pitch body matching character offsets returned by G1 (PII), G2 (banned phrases), and G4 (unsubstantiated claims).

5. **Live LLM Integration Test Suite in CI**  
   Maintain an isolated nightly test suite (`@pytest.mark.integration`) hitting live LLM endpoints to detect prompt drift and schema changes across model versions.
