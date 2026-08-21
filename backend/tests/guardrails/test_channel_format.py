import pytest
from app.models.draft import Channel, Draft, EmailPitch, GuardrailVerdict
from app.guardrails.channel_format import check_channel_format


def create_draft(channel: Channel, generated_pitch) -> Draft:
    return Draft(
        channel=channel,
        prospect_profile={"company": "Acme Inc", "contact": "Jane Doe"},
        campaign_brief={"goal": "Product Launch", "tone": "Professional"},
        generated_pitch=generated_pitch,
    )


def test_email_format_valid():
    """Valid email (subject <= 100 chars, body <= 2000 chars) passes."""
    email_pitch = EmailPitch(
        subject="A" * 50,
        body="B" * 500,
    )
    draft = create_draft(Channel.EMAIL, email_pitch)
    verdict = check_channel_format(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "channel_format"
    assert verdict.passed is True
    assert isinstance(verdict.reason, str)


def test_email_subject_exceeds_limit():
    """Email subject over 100 chars fails; reason mentions subject, actual count, and limit."""
    email_pitch = EmailPitch(
        subject="S" * 101,
        body="B" * 500,
    )
    draft = create_draft(Channel.EMAIL, email_pitch)
    verdict = check_channel_format(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "channel_format"
    assert verdict.passed is False
    assert isinstance(verdict.reason, str)
    assert len(verdict.reason.strip()) > 0
    assert "subject" in verdict.reason.lower()
    assert "101" in verdict.reason
    assert "100" in verdict.reason


def test_email_body_exceeds_limit():
    """Email body over 2000 chars fails; reason mentions body, actual count, and limit."""
    email_pitch = EmailPitch(
        subject="S" * 50,
        body="B" * 2001,
    )
    draft = create_draft(Channel.EMAIL, email_pitch)
    verdict = check_channel_format(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "channel_format"
    assert verdict.passed is False
    assert isinstance(verdict.reason, str)
    assert len(verdict.reason.strip()) > 0
    assert "body" in verdict.reason.lower()
    assert "2001" in verdict.reason
    assert "2000" in verdict.reason


def test_sms_format_valid():
    """Valid SMS (<= 160 chars) passes."""
    sms_pitch = "M" * 100
    draft = create_draft(Channel.SMS, sms_pitch)
    verdict = check_channel_format(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "channel_format"
    assert verdict.passed is True
    assert isinstance(verdict.reason, str)


def test_sms_exceeds_limit():
    """SMS over 160 chars fails and reason states actual vs limit char count."""
    sms_pitch = "M" * 161
    draft = create_draft(Channel.SMS, sms_pitch)
    verdict = check_channel_format(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "channel_format"
    assert verdict.passed is False
    assert isinstance(verdict.reason, str)
    assert len(verdict.reason.strip()) > 0
    assert "161" in verdict.reason
    assert "160" in verdict.reason


def test_whatsapp_format_valid():
    """Valid WhatsApp message (<= 1000 chars) passes."""
    whatsapp_pitch = "W" * 500
    draft = create_draft(Channel.WHATSAPP, whatsapp_pitch)
    verdict = check_channel_format(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "channel_format"
    assert verdict.passed is True
    assert isinstance(verdict.reason, str)


def test_whatsapp_exceeds_limit():
    """WhatsApp message over 1000 chars fails and reason states actual vs limit char count."""
    whatsapp_pitch = "W" * 1005
    draft = create_draft(Channel.WHATSAPP, whatsapp_pitch)
    verdict = check_channel_format(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "channel_format"
    assert verdict.passed is False
    assert isinstance(verdict.reason, str)
    assert len(verdict.reason.strip()) > 0
    assert "1005" in verdict.reason
    assert "1000" in verdict.reason


def test_boundary_exact_limits_pass():
    """Boundary test: content exactly at maximum allowed limits passes (off-by-one check)."""
    # Email at boundary: subject=100, body=2000
    email_draft = create_draft(
        Channel.EMAIL,
        EmailPitch(subject="E" * 100, body="B" * 2000),
    )
    email_verdict = check_channel_format(email_draft)
    assert email_verdict.rule == "channel_format"
    assert email_verdict.passed is True

    # SMS at boundary: 160 chars
    sms_draft = create_draft(Channel.SMS, "S" * 160)
    sms_verdict = check_channel_format(sms_draft)
    assert sms_verdict.rule == "channel_format"
    assert sms_verdict.passed is True

    # WhatsApp at boundary: 1000 chars
    whatsapp_draft = create_draft(Channel.WHATSAPP, "W" * 1000)
    whatsapp_verdict = check_channel_format(whatsapp_draft)
    assert whatsapp_verdict.rule == "channel_format"
    assert whatsapp_verdict.passed is True
