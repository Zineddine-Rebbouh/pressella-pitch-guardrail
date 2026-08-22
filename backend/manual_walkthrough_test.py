"""
Comprehensive Manual Walkthrough Test for Pressella Pitch Guardrail Application
Tests all functionality with the local gateway setup.
"""

import json
import time
import requests
from typing import Dict, Any, List

# Configuration
BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"
GATEWAY_URL = "http://localhost:20128"
TIMEOUT = 30  # seconds

# ANSI color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

class TestResult:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []

    def add_pass(self, test_name: str, details: str = ""):
        self.passed.append((test_name, details))
        print(f"{GREEN}✓ PASS{RESET} - {test_name}")
        if details:
            print(f"  {details}")

    def add_fail(self, test_name: str, error: str):
        self.failed.append((test_name, error))
        print(f"{RED}✗ FAIL{RESET} - {test_name}")
        print(f"  Error: {error}")

    def add_warning(self, test_name: str, message: str):
        self.warnings.append((test_name, message))
        print(f"{YELLOW}⚠ WARNING{RESET} - {test_name}")
        print(f"  {message}")

    def print_summary(self):
        print(f"\n{'='*80}")
        print(f"{BLUE}TEST SUMMARY{RESET}")
        print(f"{'='*80}")
        print(f"{GREEN}Passed: {len(self.passed)}{RESET}")
        print(f"{RED}Failed: {len(self.failed)}{RESET}")
        print(f"{YELLOW}Warnings: {len(self.warnings)}{RESET}")
        print(f"{'='*80}\n")

results = TestResult()

def section_header(title: str):
    print(f"\n{BLUE}{'='*80}")
    print(f"{title}")
    print(f"{'='*80}{RESET}\n")

# Test 1: Application Load & Health Checks
section_header("1. APPLICATION LOAD & HEALTH CHECKS")

try:
    response = requests.get(f"{BACKEND_URL}/health", timeout=5)
    if response.status_code == 200 and response.json().get("status") == "ok":
        results.add_pass("Backend health check", f"Status: {response.json()}")
    else:
        results.add_fail("Backend health check", f"Unexpected response: {response.status_code}")
except Exception as e:
    results.add_fail("Backend health check", str(e))

try:
    response = requests.get(FRONTEND_URL, timeout=5)
    if response.status_code == 200:
        results.add_pass("Frontend accessibility", f"HTTP {response.status_code}")
    else:
        results.add_fail("Frontend accessibility", f"HTTP {response.status_code}")
except Exception as e:
    results.add_fail("Frontend accessibility", str(e))

try:
    response = requests.get(f"{GATEWAY_URL}/health", timeout=5)
    if response.status_code == 200:
        results.add_pass("Local gateway health check", "Gateway responding")
    else:
        results.add_warning("Local gateway health check", f"HTTP {response.status_code}")
except Exception as e:
    results.add_warning("Local gateway health check", f"Gateway may not have /health endpoint: {e}")

# Test 2: Draft Creation Flow
section_header("2. DRAFT CREATION FLOW")

draft_payload = {
    "prospect_profile": {
        "company_name": "TechFlow Solutions",
        "contact_role": "VP of Marketing",
        "industry": "SaaS B2B",
        "talking_points": "Recently raised $15M Series B, 150% YoY growth, serving 500+ enterprise clients"
    },
    "campaign_brief": {
        "goal": "Secure coverage in TechCrunch and VentureBeat",
        "tone": "Professional, data-driven, confident",
        "key_talking_points": "AI-powered workflow automation, enterprise security certifications, rapid customer adoption"
    },
    "channel": "email"
}

draft_id = None

try:
    print(f"Creating draft with email channel...")
    response = requests.post(
        f"{BACKEND_URL}/drafts",
        json=draft_payload,
        headers={"Content-Type": "application/json"},
        timeout=TIMEOUT
    )

    if response.status_code == 201:
        draft = response.json()
        draft_id = draft.get("id")
        results.add_pass("Draft creation", f"Draft ID: {draft_id[:16]}...")

        # Verify draft structure
        if draft.get("status") == "pending_verification":
            results.add_pass("Draft initial status", "Status is 'pending_verification'")
        else:
            results.add_fail("Draft initial status", f"Expected 'pending_verification', got '{draft.get('status')}'")

        # Check generated pitch
        pitch = draft.get("generated_pitch")
        if isinstance(pitch, dict) and "subject" in pitch and "body" in pitch:
            results.add_pass("Email pitch generation", f"Subject: {pitch['subject'][:50]}...")
            print(f"  Body preview: {pitch['body'][:100]}...")
        else:
            results.add_fail("Email pitch generation", "Invalid pitch structure")

    else:
        results.add_fail("Draft creation", f"HTTP {response.status_code}: {response.text[:200]}")

except requests.exceptions.Timeout:
    results.add_fail("Draft creation", "Request timed out after 30 seconds - possible gateway connection issue")
except Exception as e:
    results.add_fail("Draft creation", str(e))

# Test 3: Guardrail Evaluation
section_header("3. GUARDRAIL EVALUATION")

if draft_id:
    try:
        print(f"Running guardrail verification on draft {draft_id[:16]}...")
        response = requests.post(
            f"{BACKEND_URL}/drafts/{draft_id}/verify",
            timeout=TIMEOUT
        )

        if response.status_code == 200:
            draft = response.json()
            results.add_pass("Guardrail verification endpoint", "Verification completed")

            # Check verification rounds
            verdicts = draft.get("guardrail_verdicts", [])
            if len(verdicts) > 0:
                results.add_pass("Verification rounds created", f"{len(verdicts)} round(s) recorded")

                latest_round = verdicts[-1]
                round_verdicts = latest_round.get("verdicts", [])

                # Check all 5 guardrails ran
                expected_rules = ["pii", "banned_phrases", "channel_format", "unsubstantiated_claims", "llm_judge"]
                actual_rules = [v.get("rule") for v in round_verdicts]

                if len(round_verdicts) == 5:
                    results.add_pass("All guardrails executed", f"5 rules checked: {', '.join(actual_rules)}")
                else:
                    results.add_fail("All guardrails executed", f"Expected 5, got {len(round_verdicts)}")

                # Check individual verdicts
                for verdict in round_verdicts:
                    rule = verdict.get("rule")
                    passed = verdict.get("passed")
                    reason = verdict.get("reason", "")

                    status = "PASS" if passed else "FAIL"
                    print(f"  {rule}: {status} - {reason[:60]}...")

                    # Special check for LLM judge
                    if rule == "llm_judge":
                        if "failed" in reason.lower() or "timed out" in reason.lower():
                            results.add_warning("LLM judge execution", f"Judge call issue: {reason}")
                        else:
                            results.add_pass("LLM judge execution", "Judge evaluated successfully")

                        # Check flagged claims structure
                        flagged_claims = verdict.get("flagged_claims", [])
                        if not passed and len(flagged_claims) == 0:
                            results.add_fail("LLM judge flagged claims", "Failed verdict but no flagged claims")
                        elif not passed:
                            results.add_pass("LLM judge flagged claims", f"{len(flagged_claims)} claims flagged")

                # Check status update
                new_status = draft.get("status")
                all_passed = all(v.get("passed") for v in round_verdicts)
                expected_status = "verified_pass" if all_passed else "verified_fail"

                if new_status == expected_status:
                    results.add_pass("Draft status update", f"Status correctly set to '{new_status}'")
                else:
                    results.add_fail("Draft status update", f"Expected '{expected_status}', got '{new_status}'")

            else:
                results.add_fail("Verification rounds created", "No verification rounds found")

        else:
            results.add_fail("Guardrail verification endpoint", f"HTTP {response.status_code}: {response.text[:200]}")

    except requests.exceptions.Timeout:
        results.add_fail("Guardrail verification", "Request timed out - possible LLM judge timeout")
    except Exception as e:
        results.add_fail("Guardrail verification", str(e))
else:
    results.add_warning("Guardrail evaluation", "Skipped - no draft ID available")

# Test 4: Draft Retrieval
section_header("4. DRAFT RETRIEVAL")

if draft_id:
    try:
        response = requests.get(f"{BACKEND_URL}/drafts/{draft_id}", timeout=5)

        if response.status_code == 200:
            draft = response.json()
            results.add_pass("Draft retrieval", f"Draft {draft_id[:16]}... retrieved")

            # Verify data persistence
            if draft.get("id") == draft_id:
                results.add_pass("Data persistence", "Draft data matches original")
            else:
                results.add_fail("Data persistence", "Draft ID mismatch")
        else:
            results.add_fail("Draft retrieval", f"HTTP {response.status_code}")

    except Exception as e:
        results.add_fail("Draft retrieval", str(e))
else:
    results.add_warning("Draft retrieval", "Skipped - no draft ID available")

# Test 5: Human Decision Recording
section_header("5. HUMAN DECISION RECORDING")

if draft_id:
    try:
        decision_payload = {
            "decision": "approve",
            "note": "Test approval from walkthrough"
        }

        response = requests.post(
            f"{BACKEND_URL}/drafts/{draft_id}/decision",
            json=decision_payload,
            headers={"Content-Type": "application/json"},
            timeout=5
        )

        if response.status_code == 200:
            draft = response.json()
            results.add_pass("Human decision recording", "Decision recorded successfully")

            # Check decision structure
            human_decision = draft.get("human_decision")
            if human_decision:
                if human_decision.get("decision") == "approve":
                    results.add_pass("Decision data accuracy", f"Decision: approve, Note: {human_decision.get('note')}")
                else:
                    results.add_fail("Decision data accuracy", f"Expected 'approve', got '{human_decision.get('decision')}'")

                if human_decision.get("decided_at"):
                    results.add_pass("Decision timestamp", "Timestamp recorded")
                else:
                    results.add_fail("Decision timestamp", "No timestamp found")
            else:
                results.add_fail("Decision data structure", "No human_decision field found")

            # Check status update
            if draft.get("status") == "approved":
                results.add_pass("Decision status update", "Status updated to 'approved'")
            else:
                results.add_fail("Decision status update", f"Expected 'approved', got '{draft.get('status')}'")

        elif response.status_code == 409:
            results.add_warning("Human decision recording", "Conflict - decision may already exist or draft not verified")
        else:
            results.add_fail("Human decision recording", f"HTTP {response.status_code}: {response.text[:200]}")

    except Exception as e:
        results.add_fail("Human decision recording", str(e))
else:
    results.add_warning("Human decision recording", "Skipped - no draft ID available")

# Test 6: Error Handling - Invalid Draft ID
section_header("6. ERROR HANDLING")

try:
    response = requests.get(f"{BACKEND_URL}/drafts/nonexistent-id", timeout=5)
    if response.status_code == 404:
        results.add_pass("404 error handling", "Correctly returns 404 for nonexistent draft")
    else:
        results.add_fail("404 error handling", f"Expected 404, got {response.status_code}")
except Exception as e:
    results.add_fail("404 error handling", str(e))

try:
    invalid_payload = {"channel": "invalid_channel"}
    response = requests.post(
        f"{BACKEND_URL}/drafts",
        json=invalid_payload,
        headers={"Content-Type": "application/json"},
        timeout=5
    )
    if response.status_code in [400, 422]:
        results.add_pass("Invalid payload handling", f"Correctly rejects invalid data with HTTP {response.status_code}")
    else:
        results.add_fail("Invalid payload handling", f"Expected 400/422, got {response.status_code}")
except Exception as e:
    results.add_fail("Invalid payload handling", str(e))

# Test 7: Multi-Channel Support
section_header("7. MULTI-CHANNEL SUPPORT")

for channel in ["sms", "whatsapp"]:
    try:
        payload = dict(draft_payload)
        payload["channel"] = channel

        response = requests.post(
            f"{BACKEND_URL}/drafts",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT
        )

        if response.status_code == 201:
            draft = response.json()
            pitch = draft.get("generated_pitch")

            if isinstance(pitch, str):
                results.add_pass(f"{channel.upper()} channel support", f"Generated text message ({len(pitch)} chars)")
            else:
                results.add_fail(f"{channel.upper()} channel support", f"Expected string, got {type(pitch)}")
        else:
            results.add_fail(f"{channel.upper()} channel support", f"HTTP {response.status_code}")

    except requests.exceptions.Timeout:
        results.add_fail(f"{channel.upper()} channel support", "Request timed out")
    except Exception as e:
        results.add_fail(f"{channel.upper()} channel support", str(e))

# Print final summary
results.print_summary()

# Save detailed report
report = {
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    "passed": len(results.passed),
    "failed": len(results.failed),
    "warnings": len(results.warnings),
    "details": {
        "passed_tests": [{"test": name, "details": details} for name, details in results.passed],
        "failed_tests": [{"test": name, "error": error} for name, error in results.failed],
        "warnings": [{"test": name, "message": msg} for name, msg in results.warnings]
    }
}

with open("walkthrough_report.json", "w") as f:
    json.dump(report, f, indent=2)

print(f"{GREEN}Detailed report saved to: walkthrough_report.json{RESET}\n")

# Exit with appropriate code
exit_code = 0 if len(results.failed) == 0 else 1
exit(exit_code)
