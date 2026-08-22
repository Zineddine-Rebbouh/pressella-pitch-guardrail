import sqlite3
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.models.draft import (
    Channel,
    Draft,
    DraftStatus,
    EmailPitch,
    GuardrailVerdict,
    HumanDecision,
    HumanDecisionType,
    VerificationRound,
)
from app.repository import init_db, save_draft
from app.services.generator import GenerationError

client = TestClient(app)


@pytest.fixture
def test_db_path(tmp_path):
    """Provides a temporary file-backed SQLite database path per test."""
    db_file = str(tmp_path / "test_guardrail.db")
    init_db(db_file)
    return db_file


def make_mock_verdict(rule: str, passed: bool = True, reason: str = "Clean") -> GuardrailVerdict:
    return GuardrailVerdict(rule=rule, passed=passed, reason=reason)


# ---------------------------------------------------------------------------
# Case 1: POST /drafts Happy Path
# ---------------------------------------------------------------------------
@patch("app.routes.drafts.get_db_path")
@patch("app.routes.drafts.generate_pitch")
def test_create_draft_happy_path(mock_generate_pitch, mock_get_db_path, test_db_path):
    """Case 1: POST /drafts calls generate_pitch and returns 201 Created with pending_verification status."""
    mock_get_db_path.return_value = test_db_path
    mock_generate_pitch.return_value = EmailPitch(
        subject="Test Subject", body="Test Body"
    )

    payload = {
        "prospect_profile": {"company": "Acme"},
        "campaign_brief": {"goal": "Launch"},
        "channel": "email",
    }

    response = client.post("/drafts", json=payload)

    assert response.status_code == 201
    data = response.json()

    assert "id" in data
    assert data["status"] == "pending_verification"
    assert data["channel"] == "email"
    assert data["generated_pitch"] == {"subject": "Test Subject", "body": "Test Body"}
    assert data["guardrail_verdicts"] == []
    assert data["human_decision"] is None

    # Verify generate_pitch was called with input params
    mock_generate_pitch.assert_called_once_with(
        {"company": "Acme"}, {"goal": "Launch"}, Channel.EMAIL
    )


# ---------------------------------------------------------------------------
# Case 2: POST /drafts Generation Error (502 Bad Gateway + Direct DB Verification)
# ---------------------------------------------------------------------------
@patch("app.routes.drafts.get_db_path")
@patch("app.routes.drafts.generate_pitch")
def test_create_draft_generation_failure_returns_502_and_does_not_persist(
    mock_generate_pitch, mock_get_db_path, test_db_path
):
    """Case 2: POST /drafts returns 502 Bad Gateway when generate_pitch raises GenerationError.

    CRITICAL VERIFICATION: Direct SQLite count query verifies zero rows were written to DB.
    """
    mock_get_db_path.return_value = test_db_path
    mock_generate_pitch.side_effect = GenerationError("Anthropic API connection timeout")

    payload = {
        "prospect_profile": {"company": "Beta"},
        "campaign_brief": {"goal": "PR"},
        "channel": "sms",
    }

    response = client.post("/drafts", json=payload)

    assert response.status_code == 502
    assert "Generation failed" in response.json()["detail"] or "timeout" in response.json()["detail"].lower()

    # DIRECT DATABASE CHECK: Confirm 0 rows written to SQLite database
    with sqlite3.connect(test_db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM drafts").fetchone()[0]

    assert count == 0, f"Expected 0 rows persisted on generation failure, found {count}"


# ---------------------------------------------------------------------------
# Case 3: POST /drafts/{id}/verify Happy Path (All 5 Pass)
# ---------------------------------------------------------------------------
@patch("app.routes.drafts.get_db_path")
@patch("app.routes.drafts.check_llm_judge")
@patch("app.routes.drafts.check_unsubstantiated_claims")
@patch("app.routes.drafts.check_channel_format")
@patch("app.routes.drafts.check_banned_phrases")
@patch("app.routes.drafts.check_pii")
def test_verify_draft_all_pass(
    mock_pii,
    mock_banned,
    mock_channel,
    mock_unsub,
    mock_judge,
    mock_get_db_path,
    test_db_path,
):
    """Case 3: POST /drafts/{id}/verify runs all 5 rules; status becomes verified_pass when all pass."""
    mock_get_db_path.return_value = test_db_path

    mock_pii.return_value = make_mock_verdict("pii", passed=True)
    mock_banned.return_value = make_mock_verdict("banned_phrases", passed=True)
    mock_channel.return_value = make_mock_verdict("channel_format", passed=True)
    mock_unsub.return_value = make_mock_verdict("unsubstantiated_claims", passed=True)
    mock_judge.return_value = make_mock_verdict("llm_judge", passed=True)

    draft = Draft(
        channel=Channel.EMAIL,
        prospect_profile={"company": "Acme"},
        campaign_brief={"goal": "Launch"},
        generated_pitch=EmailPitch(subject="S", body="B"),
    )
    save_draft(draft, db_path=test_db_path)

    response = client.post(f"/drafts/{draft.id}/verify")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "verified_pass"
    assert len(data["guardrail_verdicts"]) == 1
    verdicts = data["guardrail_verdicts"][0]["verdicts"]
    assert len(verdicts) == 5
    assert all(v["passed"] for v in verdicts)


# ---------------------------------------------------------------------------
# Case 4: POST /drafts/{id}/verify No Short-Circuiting (All 5 Run Even If One Fails)
# ---------------------------------------------------------------------------
@patch("app.routes.drafts.get_db_path")
@patch("app.routes.drafts.check_llm_judge")
@patch("app.routes.drafts.check_unsubstantiated_claims")
@patch("app.routes.drafts.check_channel_format")
@patch("app.routes.drafts.check_banned_phrases")
@patch("app.routes.drafts.check_pii")
def test_verify_draft_runs_all_rules_without_short_circuiting(
    mock_pii,
    mock_banned,
    mock_channel,
    mock_unsub,
    mock_judge,
    mock_get_db_path,
    test_db_path,
):
    """Case 4: POST /drafts/{id}/verify where G1 (pii) fails; all remaining checks still execute.

    Proves no short-circuiting — auditability requires full verdict evaluation.
    """
    mock_get_db_path.return_value = test_db_path

    # First check fails
    mock_pii.return_value = make_mock_verdict("pii", passed=False, reason="PII detected")
    # Remaining checks pass
    mock_banned.return_value = make_mock_verdict("banned_phrases", passed=True)
    mock_channel.return_value = make_mock_verdict("channel_format", passed=True)
    mock_unsub.return_value = make_mock_verdict("unsubstantiated_claims", passed=True)
    mock_judge.return_value = make_mock_verdict("llm_judge", passed=True)

    draft = Draft(
        channel=Channel.SMS,
        prospect_profile={"name": "Alice"},
        campaign_brief={"goal": "SMS"},
        generated_pitch="Hello Alice",
    )
    save_draft(draft, db_path=test_db_path)

    response = client.post(f"/drafts/{draft.id}/verify")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "verified_fail"
    assert len(data["guardrail_verdicts"]) == 1
    verdicts = data["guardrail_verdicts"][0]["verdicts"]

    # All 5 rules must be present in output
    assert len(verdicts) == 5
    assert mock_pii.called
    assert mock_banned.called
    assert mock_channel.called
    assert mock_unsub.called
    assert mock_judge.called

    # Explicitly verify the PII check's passed=False verdict survived into response payload
    pii_verdict = next(v for v in verdicts if v["rule"] == "pii")
    assert pii_verdict["passed"] is False
    assert pii_verdict["reason"] == "PII detected"


# ---------------------------------------------------------------------------
# Case 1b: POST /drafts Invalid Channel Value → 422 Unprocessable Entity
# ---------------------------------------------------------------------------
def test_create_draft_invalid_channel_returns_422():
    """Case 1b: POST /drafts with invalid channel returns 422 Unprocessable Entity."""
    payload = {
        "prospect_profile": {"company": "Acme"},
        "campaign_brief": {"goal": "Launch"},
        "channel": "carrier_pigeon",
    }

    response = client.post("/drafts", json=payload)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Case 5: POST /drafts/{id}/verify Multi-Round History Append
# ---------------------------------------------------------------------------
@patch("app.routes.drafts.get_db_path")
@patch("app.routes.drafts.check_llm_judge")
@patch("app.routes.drafts.check_unsubstantiated_claims")
@patch("app.routes.drafts.check_channel_format")
@patch("app.routes.drafts.check_banned_phrases")
@patch("app.routes.drafts.check_pii")
def test_verify_draft_twice_appends_second_round(
    mock_pii,
    mock_banned,
    mock_channel,
    mock_unsub,
    mock_judge,
    mock_get_db_path,
    test_db_path,
):
    """Case 5: Calling verify twice on the same draft appends a second VerificationRound."""
    mock_get_db_path.return_value = test_db_path

    mock_pii.return_value = make_mock_verdict("pii", passed=True)
    mock_banned.return_value = make_mock_verdict("banned_phrases", passed=True)
    mock_channel.return_value = make_mock_verdict("channel_format", passed=True)
    mock_unsub.return_value = make_mock_verdict("unsubstantiated_claims", passed=True)
    mock_judge.return_value = make_mock_verdict("llm_judge", passed=True)

    draft = Draft(
        channel=Channel.WHATSAPP,
        prospect_profile={"name": "Bob"},
        campaign_brief={"goal": "WA"},
        generated_pitch="Hello Bob",
    )
    save_draft(draft, db_path=test_db_path)

    # First verify call
    res1 = client.post(f"/drafts/{draft.id}/verify")
    assert res1.status_code == 200
    assert len(res1.json()["guardrail_verdicts"]) == 1

    # Second verify call
    res2 = client.post(f"/drafts/{draft.id}/verify")
    assert res2.status_code == 200
    data2 = res2.json()

    assert len(data2["guardrail_verdicts"]) == 2


# ---------------------------------------------------------------------------
# Case 6: POST /drafts/{id}/verify Nonexistent ID → 404 Not Found
# ---------------------------------------------------------------------------
@patch("app.routes.drafts.get_db_path")
def test_verify_draft_nonexistent_id_returns_404(mock_get_db_path, test_db_path):
    """Case 6: POST /drafts/{id}/verify on a nonexistent draft returns 404 Not Found."""
    mock_get_db_path.return_value = test_db_path
    non_existent_id = str(uuid4())

    response = client.post(f"/drafts/{non_existent_id}/verify")

    assert response.status_code == 404
    assert "Draft not found" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Case 7: GET /drafts/{id} Happy Path
# ---------------------------------------------------------------------------
@patch("app.routes.drafts.get_db_path")
def test_get_draft_happy_path(mock_get_db_path, test_db_path):
    """Case 7: GET /drafts/{id} returns 200 OK with full draft object."""
    mock_get_db_path.return_value = test_db_path

    draft = Draft(
        channel=Channel.EMAIL,
        prospect_profile={"company": "Acme"},
        campaign_brief={"goal": "PR"},
        generated_pitch=EmailPitch(subject="S", body="B"),
    )
    save_draft(draft, db_path=test_db_path)

    response = client.get(f"/drafts/{draft.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(draft.id)
    assert data["channel"] == "email"


# ---------------------------------------------------------------------------
# Case 8: GET /drafts/{id} Nonexistent ID → 404 Not Found
# ---------------------------------------------------------------------------
@patch("app.routes.drafts.get_db_path")
def test_get_draft_nonexistent_id_returns_404(mock_get_db_path, test_db_path):
    """Case 8: GET /drafts/{id} returns 404 Not Found for nonexistent ID."""
    mock_get_db_path.return_value = test_db_path
    non_existent_id = str(uuid4())

    response = client.get(f"/drafts/{non_existent_id}")

    assert response.status_code == 404
    assert "Draft not found" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Case 9: POST /drafts/{id}/decision on Pending Verification → 409 Conflict
# ---------------------------------------------------------------------------
@patch("app.routes.drafts.get_db_path")
def test_decision_on_pending_verification_returns_409_conflict(
    mock_get_db_path, test_db_path
):
    """Case 9: POST /drafts/{id}/decision on pending_verification draft returns 409 Conflict.

    ROADMAP GUARDRAIL: A draft cannot be approved or rejected before at least one verify cycle.
    """
    mock_get_db_path.return_value = test_db_path

    draft = Draft(
        channel=Channel.SMS,
        prospect_profile={"name": "Alice"},
        campaign_brief={"goal": "Unverified"},
        generated_pitch="Hello Alice",
        status=DraftStatus.PENDING_VERIFICATION,
    )
    save_draft(draft, db_path=test_db_path)

    payload = {"decision": "approve", "note": "Attempting premature approval"}
    response = client.post(f"/drafts/{draft.id}/decision", json=payload)

    assert response.status_code == 409
    assert "cannot record decision" in response.json()["detail"].lower() or "unverified" in response.json()["detail"].lower() or "pending_verification" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Case 10: POST /drafts/{id}/decision (Approve) on Verified Draft → 200 OK
# ---------------------------------------------------------------------------
@patch("app.routes.drafts.get_db_path")
def test_decision_approve_on_verified_draft(mock_get_db_path, test_db_path):
    """Case 10: POST /drafts/{id}/decision (approve) on a verified draft sets status to approved."""
    mock_get_db_path.return_value = test_db_path

    draft = Draft(
        channel=Channel.EMAIL,
        prospect_profile={"company": "Acme"},
        campaign_brief={"goal": "Verified"},
        generated_pitch=EmailPitch(subject="S", body="B"),
        status=DraftStatus.VERIFIED_PASS,
    )
    save_draft(draft, db_path=test_db_path)

    payload = {"decision": "approve", "note": "Looks good to send"}
    response = client.post(f"/drafts/{draft.id}/decision", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "approved"
    assert data["human_decision"] is not None
    assert data["human_decision"]["decision"] == "approve"
    assert data["human_decision"]["note"] == "Looks good to send"
    assert "decided_at" in data["human_decision"]


# ---------------------------------------------------------------------------
# Case 11: POST /drafts/{id}/decision (Reject) on Verified Draft → 200 OK
# ---------------------------------------------------------------------------
@patch("app.routes.drafts.get_db_path")
def test_decision_reject_on_verified_draft(mock_get_db_path, test_db_path):
    """Case 11: POST /drafts/{id}/decision (reject) sets status to rejected and stores note."""
    mock_get_db_path.return_value = test_db_path

    draft = Draft(
        channel=Channel.SMS,
        prospect_profile={"name": "Bob"},
        campaign_brief={"goal": "Reject test"},
        generated_pitch="Hello Bob",
        status=DraftStatus.VERIFIED_FAIL,
    )
    save_draft(draft, db_path=test_db_path)

    payload = {"decision": "reject", "note": "Tone is mismatched"}
    response = client.post(f"/drafts/{draft.id}/decision", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "rejected"
    assert data["human_decision"] is not None
    assert data["human_decision"]["decision"] == "reject"
    assert data["human_decision"]["note"] == "Tone is mismatched"


# ---------------------------------------------------------------------------
# Case 11b: POST /drafts/{id}/decision Invalid Decision Value → 422 Unprocessable Entity
# ---------------------------------------------------------------------------
@patch("app.routes.drafts.get_db_path")
def test_decision_invalid_value_returns_422(mock_get_db_path, test_db_path):
    """Case 11b: POST /drafts/{id}/decision with invalid decision value returns 422."""
    mock_get_db_path.return_value = test_db_path

    draft = Draft(
        channel=Channel.SMS,
        prospect_profile={"name": "Bob"},
        campaign_brief={"goal": "Test"},
        generated_pitch="Hello Bob",
        status=DraftStatus.VERIFIED_PASS,
    )
    save_draft(draft, db_path=test_db_path)

    payload = {"decision": "maybe"}
    response = client.post(f"/drafts/{draft.id}/decision", json=payload)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Case 12: POST /drafts/{id}/decision Nonexistent ID → 404 Not Found
# ---------------------------------------------------------------------------
@patch("app.routes.drafts.get_db_path")
def test_decision_nonexistent_id_returns_404(mock_get_db_path, test_db_path):
    """Case 12: POST /drafts/{id}/decision on nonexistent draft returns 404 Not Found."""
    mock_get_db_path.return_value = test_db_path
    non_existent_id = str(uuid4())

    payload = {"decision": "approve"}
    response = client.post(f"/drafts/{non_existent_id}/decision", json=payload)

    assert response.status_code == 404
    assert "Draft not found" in response.json()["detail"]

