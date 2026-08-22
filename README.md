# Pressella Pitch Guardrail & Eval Harness

A proof-of-concept service that generates LLM-powered outreach pitches, runs them through a deterministic + LLM-as-judge guardrail layer, and lets a human reviewer approve or reject before (mock) sending.

## Overview

This PoC provides an end-to-end auditability and compliance evaluation pipeline for PR pitches across multiple channels (`email`, `sms`, `whatsapp`).

### Guardrail Pipeline

- **G1 — PII / Compliance Check (`pii`)**: Detects sensitive personal identification (SSNs, emails, phone numbers, credit card numbers with Luhn validation).
- **G2 — Banned Phrases (`banned_phrases`)**: Catches high-risk or misleading promotional claims using word-boundary-aware regex (`\b`).
- **G3 — Channel Constraints (`channel_format`)**: Verifies character limits and required fields for Email, SMS, and WhatsApp.
- **G4 — Unsubstantiated Numeric Claims (`unsubstantiated_claims`)**: Cross-checks numeric claims (percentages, dollar amounts, multipliers, bare numbers) against input brief/profile data with normalization and bare small integer exemptions.
- **G5 — LLM Tone & Claim Traceability (`llm_judge`)**: Uses Claude/Anthropic structured outputs to verify tone alignment and factual claim traceability with strict fail-safe guarantees.

---

## What I'd Do Next (Future Enhancements & Production Roadmap)

The following items represent architectural improvements, production readiness tasks, and extensions identified during development (accumulated through Stage 3 guardrail implementation):

### 1. Live LLM Integration Smoke Test Suite
- Add an isolated integration test suite tagged `@pytest.mark.integration` that hits the live Anthropic API.
- Validate live prompt responses against schema evolution and measure real latency/token usage without blocking deterministic CI unit test runs.

### 2. Externalized Deny-List Management
- Move the G2 banned-phrase starter list from code constants to a dynamic database table or configuration service (e.g., YAML / SQLite / Redis).
- Allow compliance teams to add, flag, or modify regex patterns and phrase thresholds at runtime without releasing code changes.

### 3. Advanced NLP & Claim Extraction (G4 Upgrade)
- Catch non-standard or semantic claims — like "doubled our client base" or spelled-out numbers ("forty percent growth", "five million dollars") — that regex-only matching cannot parse.
- Upgrade from static regex pattern matching to a dedicated NER / dependency parser (e.g., spaCy or LLM pre-pass) to extract semantic numeric expressions and handle range comparisons ("between $10k and $50k").

### 4. Interactive Visual Diffing & Reviewer UI
- In the frontend reviewer dashboard, render visual highlight overlays corresponding to exact character offsets reported by G1, G2, and G4.
- Provide side-by-side historical diffing across multiple re-verification rounds.

### 5. Configurable Thresholds & Severity Tiers
- Support check severity tiers (e.g., `WARNING` vs `BLOCKING_FAIL`).
- Make parameters like `BARE_INTEGER_EXEMPTION_THRESHOLD` configurable per campaign type or client profile.


