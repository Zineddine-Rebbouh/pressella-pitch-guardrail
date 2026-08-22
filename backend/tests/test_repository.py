from datetime import datetime, timezone
from uuid import uuid4
import pytest

from app.models.draft import (
    Channel,
    Draft,
    DraftStatus,
    EmailPitch,
    FlaggedClaim,
    GuardrailVerdict,
    HumanDecision,
    HumanDecisionType,
    VerificationRound,
)
from app.repository import get_draft, init_db, save_draft


@pytest.fixture
def test_db_path(tmp_path):
    """Provides a temporary file-backed SQLite database path per test."""
    db_file = str(tmp_path / "test_guardrail.db")
    init_db(db_file)
    return db_file


def test_save_and_get_draft_happy_path(test_db_path):
    """Case 1: Save a draft and retrieve it by ID.

    Verifies full round-trip accuracy including nested Pydantic models:
    VerificationRound, GuardrailVerdict, FlaggedClaim, and HumanDecision,
    as well as UTC-aware timestamp survival.
    """
    draft_id = uuid4()
    verdict = GuardrailVerdict(
        rule="llm_judge",
        passed=False,
        reason="Claim not substantiated",
        flagged_claims=[
            FlaggedClaim(claim="100% ROI", reason="Not found in brief")
        ],
    )
    round_one = VerificationRound(verdicts=[verdict])
    decision = HumanDecision(
        decision=HumanDecisionType.REJECT,
        note="Too risky",
        decided_at=datetime.now(timezone.utc),
    )

    draft = Draft(
        id=draft_id,
        channel=Channel.EMAIL,
        prospect_profile={"company": "Acme Inc", "contact": "Alice"},
        campaign_brief={"goal": "Outreach", "budget": 5000},
        generated_pitch=EmailPitch(
            subject="Introducing Acme Analytics",
            body="Our platform streamlines data workflows.",
        ),
        status=DraftStatus.REJECTED,
        guardrail_verdicts=[round_one],
        human_decision=decision,
    )

    save_draft(draft, db_path=test_db_path)
    retrieved = get_draft(str(draft_id), db_path=test_db_path)

    assert retrieved is not None
    assert retrieved.id == draft.id
    assert retrieved.channel == Channel.EMAIL
    assert retrieved.status == DraftStatus.REJECTED
    assert retrieved.prospect_profile == {"company": "Acme Inc", "contact": "Alice"}
    assert retrieved.campaign_brief == {"goal": "Outreach", "budget": 5000}

    # Verify EmailPitch model round-trip
    assert isinstance(retrieved.generated_pitch, EmailPitch)
    assert retrieved.generated_pitch.subject == "Introducing Acme Analytics"
    assert retrieved.generated_pitch.body == "Our platform streamlines data workflows."

    # Verify nested verdicts round-trip
    assert len(retrieved.guardrail_verdicts) == 1
    assert len(retrieved.guardrail_verdicts[0].verdicts) == 1
    v = retrieved.guardrail_verdicts[0].verdicts[0]
    assert v.rule == "llm_judge"
    assert v.passed is False
    assert len(v.flagged_claims) == 1
    assert v.flagged_claims[0].claim == "100% ROI"

    # Verify human decision round-trip
    assert retrieved.human_decision is not None
    assert retrieved.human_decision.decision == HumanDecisionType.REJECT
    assert retrieved.human_decision.note == "Too risky"

    # Verify UTC-aware timestamp round-trip (Stage 2 UTC timestamp decision)
    assert retrieved.created_at.tzinfo is not None
    assert retrieved.updated_at.tzinfo is not None
    assert abs((retrieved.created_at - draft.created_at).total_seconds()) < 1.0
    assert abs((retrieved.updated_at - draft.updated_at).total_seconds()) < 1.0


def test_get_nonexistent_draft_returns_none(test_db_path):
    """Case 2: Retrieve a draft that was never saved.

    Verifies get_draft returns None without raising an exception.
    """
    non_existent_id = str(uuid4())
    result = get_draft(non_existent_id, db_path=test_db_path)

    assert result is None


def test_save_draft_update_existing_id(test_db_path):
    """Case 3: Save a draft, mutate it, and save again with the same ID.

    Verifies update-by-ID functionality (UPSERT).
    """
    draft = Draft(
        channel=Channel.SMS,
        prospect_profile={"name": "Bob"},
        campaign_brief={"goal": "SMS campaign"},
        generated_pitch="Hello Bob! Check out our new platform at acme.ai",
        status=DraftStatus.PENDING_VERIFICATION,
    )

    # Initial insert
    save_draft(draft, db_path=test_db_path)

    initial_retrieved = get_draft(str(draft.id), db_path=test_db_path)
    assert initial_retrieved is not None
    assert initial_retrieved.status == DraftStatus.PENDING_VERIFICATION
    assert len(initial_retrieved.guardrail_verdicts) == 0

    # Mutate draft
    verdict = GuardrailVerdict(rule="channel_format", passed=True, reason="Within 160 chars")
    new_round = VerificationRound(verdicts=[verdict])
    draft.guardrail_verdicts.append(new_round)
    draft.status = DraftStatus.VERIFIED_PASS
    draft.human_decision = HumanDecision(
        decision=HumanDecisionType.APPROVE,
        note="Approved for SMS send",
    )

    # Update save
    save_draft(draft, db_path=test_db_path)

    updated_retrieved = get_draft(str(draft.id), db_path=test_db_path)
    assert updated_retrieved is not None
    assert updated_retrieved.status == DraftStatus.VERIFIED_PASS
    assert len(updated_retrieved.guardrail_verdicts) == 1
    assert updated_retrieved.human_decision is not None
    assert updated_retrieved.human_decision.decision == HumanDecisionType.APPROVE


def test_save_draft_preserves_multi_round_history(test_db_path):
    """Case 3b: Save a draft across multiple verify cycles to prove append-only history survival.

    Verifies that performing two separate verify/mutate + save cycles preserves
    both VerificationRound objects in chronological order without silently overwriting
    earlier rounds.
    """
    draft = Draft(
        channel=Channel.EMAIL,
        prospect_profile={"company": "Acme"},
        campaign_brief={"goal": "Multi-round Test"},
        generated_pitch=EmailPitch(subject="S", body="B"),
    )

    # Initial save
    save_draft(draft, db_path=test_db_path)

    # First verify round & save
    round_1 = VerificationRound(
        verdicts=[GuardrailVerdict(rule="pii", passed=False, reason="PII found")]
    )
    draft.guardrail_verdicts.append(round_1)
    draft.status = DraftStatus.VERIFIED_FAIL
    save_draft(draft, db_path=test_db_path)

    # Second re-verify round & save
    round_2 = VerificationRound(
        verdicts=[
            GuardrailVerdict(rule="pii", passed=True, reason="PII resolved"),
            GuardrailVerdict(rule="banned_phrases", passed=True, reason="Clean"),
        ]
    )
    draft.guardrail_verdicts.append(round_2)
    draft.status = DraftStatus.VERIFIED_PASS
    save_draft(draft, db_path=test_db_path)

    # Retrieve and verify both rounds exist in history in order
    retrieved = get_draft(str(draft.id), db_path=test_db_path)
    assert retrieved is not None
    assert retrieved.status == DraftStatus.VERIFIED_PASS
    assert len(retrieved.guardrail_verdicts) == 2

    # Round 1 checks
    r1 = retrieved.guardrail_verdicts[0]
    assert len(r1.verdicts) == 1
    assert r1.verdicts[0].rule == "pii"
    assert r1.verdicts[0].passed is False

    # Round 2 checks
    r2 = retrieved.guardrail_verdicts[1]
    assert len(r2.verdicts) == 2
    assert r2.verdicts[0].rule == "pii"
    assert r2.verdicts[0].passed is True
    assert r2.verdicts[1].rule == "banned_phrases"
    assert r2.verdicts[1].passed is True


def test_save_multiple_independent_drafts(test_db_path):
    """Case 4: Save two distinct drafts with different IDs.

    Verifies each draft is stored and retrievable independently.
    """
    draft_a = Draft(
        channel=Channel.SMS,
        prospect_profile={"name": "Alice"},
        campaign_brief={"goal": "Goal A"},
        generated_pitch="Pitch A",
    )
    draft_b = Draft(
        channel=Channel.WHATSAPP,
        prospect_profile={"name": "Charlie"},
        campaign_brief={"goal": "Goal B"},
        generated_pitch="Pitch B",
    )

    save_draft(draft_a, db_path=test_db_path)
    save_draft(draft_b, db_path=test_db_path)

    retrieved_a = get_draft(str(draft_a.id), db_path=test_db_path)
    retrieved_b = get_draft(str(draft_b.id), db_path=test_db_path)

    assert retrieved_a is not None
    assert retrieved_b is not None
    assert retrieved_a.id != retrieved_b.id
    assert retrieved_a.channel == Channel.SMS
    assert retrieved_b.channel == Channel.WHATSAPP
    assert retrieved_a.generated_pitch == "Pitch A"
    assert retrieved_b.generated_pitch == "Pitch B"


def test_generated_pitch_union_types_survival(test_db_path):
    """Case 5: EmailPitch object vs plain string pitch Union serialization survival.

    Verifies that the Union[EmailPitch, str] type is preserved without ambiguity
    across JSON serialization and deserialization.
    """
    # Draft with EmailPitch object
    email_draft = Draft(
        channel=Channel.EMAIL,
        prospect_profile={"name": "David"},
        campaign_brief={"goal": "Email Goal"},
        generated_pitch=EmailPitch(subject="Subj", body="Body text"),
    )

    # Draft with plain str
    sms_draft = Draft(
        channel=Channel.SMS,
        prospect_profile={"name": "Eve"},
        campaign_brief={"goal": "SMS Goal"},
        generated_pitch="Plain text pitch",
    )

    save_draft(email_draft, db_path=test_db_path)
    save_draft(sms_draft, db_path=test_db_path)

    retrieved_email = get_draft(str(email_draft.id), db_path=test_db_path)
    retrieved_sms = get_draft(str(sms_draft.id), db_path=test_db_path)

    assert retrieved_email is not None
    assert retrieved_sms is not None

    # Email draft must deserialize to EmailPitch model
    assert isinstance(retrieved_email.generated_pitch, EmailPitch)
    assert retrieved_email.generated_pitch.subject == "Subj"

    # SMS draft must deserialize to plain str
    assert isinstance(retrieved_sms.generated_pitch, str)
    assert retrieved_sms.generated_pitch == "Plain text pitch"
