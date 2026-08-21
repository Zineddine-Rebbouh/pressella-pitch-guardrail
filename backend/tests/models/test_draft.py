from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

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


def test_draft_construction_email():
    draft = Draft(
        channel=Channel.EMAIL,
        prospect_profile={"name": "Jane Doe", "company": "Acme Corp"},
        campaign_brief={"goal": "Introduce product X"},
        generated_pitch=EmailPitch(
            subject="Introducing Product X",
            body="Hi Jane, we would love to connect."
        ),
    )

    assert draft.id is not None
    assert draft.channel == Channel.EMAIL
    assert isinstance(draft.generated_pitch, EmailPitch)
    assert draft.generated_pitch.subject == "Introducing Product X"
    assert draft.status == DraftStatus.PENDING_VERIFICATION
    assert draft.guardrail_verdicts == []
    assert draft.human_decision is None
    assert draft.created_at.tzinfo == timezone.utc
    assert draft.updated_at.tzinfo == timezone.utc


def test_draft_construction_sms():
    draft = Draft(
        channel=Channel.SMS,
        prospect_profile={"phone": "+1234567890"},
        campaign_brief={"goal": "SMS blast"},
        generated_pitch="Check out our latest offer!",
    )

    assert draft.channel == Channel.SMS
    assert draft.generated_pitch == "Check out our latest offer!"


def test_channel_validation():
    # Test valid enum string values
    for valid_channel in ["email", "sms", "whatsapp"]:
        draft = Draft(
            channel=valid_channel,
            prospect_profile={},
            campaign_brief={},
            generated_pitch="Pitch text",
        )
        assert draft.channel == valid_channel

    # Test invalid channel value
    with pytest.raises(ValidationError):
        Draft(
            channel="slack",
            prospect_profile={},
            campaign_brief={},
            generated_pitch="Pitch text",
        )


def test_draft_serialization_round_trip():
    original_draft = Draft(
        channel=Channel.EMAIL,
        prospect_profile={"company": "TechCorp"},
        campaign_brief={"goal": "Outreach"},
        generated_pitch=EmailPitch(subject="Subject", body="Body text"),
        status=DraftStatus.VERIFIED_PASS,
        guardrail_verdicts=[
            VerificationRound(
                verdicts=[
                    GuardrailVerdict(rule="G1", passed=True, reason="No PII found"),
                    GuardrailVerdict(rule="G2", passed=True, reason="No banned phrases"),
                ]
            )
        ],
        human_decision=HumanDecision(
            decision=HumanDecisionType.APPROVE,
            note="Looks good to send",
        ),
    )

    json_str = original_draft.model_dump_json()
    reconstructed_draft = Draft.model_validate_json(json_str)

    assert reconstructed_draft.id == original_draft.id
    assert reconstructed_draft.channel == original_draft.channel
    assert reconstructed_draft.prospect_profile == original_draft.prospect_profile
    assert reconstructed_draft.campaign_brief == original_draft.campaign_brief
    assert reconstructed_draft.generated_pitch == original_draft.generated_pitch
    assert reconstructed_draft.status == original_draft.status
    assert len(reconstructed_draft.guardrail_verdicts) == 1
    assert reconstructed_draft.guardrail_verdicts[0].verdicts[0].rule == "G1"
    assert reconstructed_draft.human_decision is not None
    assert reconstructed_draft.human_decision.decision == HumanDecisionType.APPROVE
    assert reconstructed_draft.human_decision.note == "Looks good to send"


def test_guardrail_verdicts_append_only():
    draft = Draft(
        channel=Channel.WHATSAPP,
        prospect_profile={},
        campaign_brief={},
        generated_pitch="WhatsApp pitch",
    )

    round1 = VerificationRound(
        verdicts=[GuardrailVerdict(rule="G1", passed=False, reason="PII detected")]
    )
    draft.guardrail_verdicts.append(round1)

    round2 = VerificationRound(
        verdicts=[GuardrailVerdict(rule="G1", passed=True, reason="Fixed")]
    )
    draft.guardrail_verdicts.append(round2)

    assert len(draft.guardrail_verdicts) == 2
    assert draft.guardrail_verdicts[0].verdicts[0].passed is False
    assert draft.guardrail_verdicts[1].verdicts[0].passed is True
