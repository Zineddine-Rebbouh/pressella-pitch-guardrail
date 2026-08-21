import pytest
from app.models.draft import Channel, Draft, EmailPitch, GuardrailVerdict
from app.guardrails.pii import check_pii


def create_draft(channel: Channel, generated_pitch) -> Draft:
    return Draft(
        channel=channel,
        prospect_profile={"company": "Acme Inc", "contact": "Jane Doe"},
        campaign_brief={"goal": "Product Launch", "tone": "Professional"},
        generated_pitch=generated_pitch,
    )


def test_clean_draft_passes():
    """Draft containing no PII passes."""
    pitch = EmailPitch(
        subject="Welcome to our platform",
        body="We are excited to share our latest product updates with your company.",
    )
    draft = create_draft(Channel.EMAIL, pitch)
    verdict = check_pii(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "pii"
    assert verdict.passed is True
    assert isinstance(verdict.reason, str)


def test_ssn_detection_fails():
    """Draft containing a Social Security Number (XXX-XX-XXXX) fails and reports category + exact character position."""
    pii_str = "123-45-6789"
    pitch = f"Please send SSN to {pii_str} for verification."
    expected_offset = pitch.index(pii_str)
    draft = create_draft(Channel.SMS, pitch)
    verdict = check_pii(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "pii"
    assert verdict.passed is False
    assert isinstance(verdict.reason, str)

    reason_lower = verdict.reason.lower()
    assert "ssn" in reason_lower or "social security" in reason_lower
    assert str(expected_offset) in verdict.reason


def test_email_detection_fails():
    """Draft containing an email address fails and reports email category + exact character position."""
    pii_str = "jane.doe@example.com"
    email_pitch = EmailPitch(
        subject="Contact Info",
        body=f"Please reach out to {pii_str} for more information.",
    )
    combined_text = f"{email_pitch.subject}\n{email_pitch.body}"
    expected_offset = combined_text.index(pii_str)

    draft = create_draft(Channel.EMAIL, email_pitch)
    verdict = check_pii(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "pii"
    assert verdict.passed is False
    assert isinstance(verdict.reason, str)

    reason_lower = verdict.reason.lower()
    assert "email" in reason_lower
    assert str(expected_offset) in verdict.reason


def test_north_american_phone_detection_fails():
    """Draft containing a North American phone number fails and reports phone category + exact character position."""
    pii_str = "(555) 123-4567"
    pitch = f"Call us at {pii_str} to claim your demo."
    expected_offset = pitch.index(pii_str)
    draft = create_draft(Channel.SMS, pitch)
    verdict = check_pii(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "pii"
    assert verdict.passed is False
    assert isinstance(verdict.reason, str)

    reason_lower = verdict.reason.lower()
    assert "phone" in reason_lower
    assert str(expected_offset) in verdict.reason


def test_international_phone_detection_fails():
    """Draft containing an international phone number fails and reports phone category + exact character position."""
    pii_str = "+44 20 7946 0958"
    pitch = f"Contact our UK office at {pii_str} today."
    expected_offset = pitch.index(pii_str)
    draft = create_draft(Channel.WHATSAPP, pitch)
    verdict = check_pii(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "pii"
    assert verdict.passed is False
    assert isinstance(verdict.reason, str)

    reason_lower = verdict.reason.lower()
    assert "phone" in reason_lower
    assert str(expected_offset) in verdict.reason


def test_luhn_invalid_credit_card_passes():
    """A 16-digit sequence that fails Luhn validation passes (proves Luhn check vs naive digit count)."""
    # Luhn validation check: doubled digits sum to 31 (31 % 10 = 1 != 0), so 4111111111111112 is invalid.
    pitch = "Reference number: 4111111111111112 for tracking."
    draft = create_draft(Channel.SMS, pitch)
    verdict = check_pii(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "pii"
    assert verdict.passed is True
    assert isinstance(verdict.reason, str)


def test_luhn_valid_credit_card_fails():
    """A 16-digit number passing Luhn validation (e.g. 4111111111111111) fails and reports credit card category + position."""
    pii_str = "4111111111111111"
    pitch = f"Use card {pii_str} to complete transaction."
    expected_offset = pitch.index(pii_str)
    draft = create_draft(Channel.SMS, pitch)
    verdict = check_pii(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "pii"
    assert verdict.passed is False
    assert isinstance(verdict.reason, str)

    reason_lower = verdict.reason.lower()
    assert "card" in reason_lower or "credit" in reason_lower
    assert str(expected_offset) in verdict.reason


def test_multiple_pii_reports_all():
    """Draft containing multiple PII types (email and phone) fails and reports both categories + exact character positions."""
    email_str = "support@example.com"
    phone_str = "555-123-4567"
    email_pitch = EmailPitch(
        subject="Support Contact",
        body=f"Reach out via email at {email_str} or phone at {phone_str}.",
    )
    combined_text = f"{email_pitch.subject}\n{email_pitch.body}"
    expected_email_offset = combined_text.index(email_str)
    expected_phone_offset = combined_text.index(phone_str)

    draft = create_draft(Channel.EMAIL, email_pitch)
    verdict = check_pii(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "pii"
    assert verdict.passed is False
    assert isinstance(verdict.reason, str)

    reason_lower = verdict.reason.lower()
    assert "email" in reason_lower
    assert "phone" in reason_lower
    assert str(expected_email_offset) in verdict.reason
    assert str(expected_phone_offset) in verdict.reason


def test_plain_long_number_passes():
    """Order reference / invoice number (e.g. ORD-2024-88213910) passes to prevent over-matching."""
    pitch = "Your order reference ORD-2024-88213910 has been processed successfully."
    draft = create_draft(Channel.SMS, pitch)
    verdict = check_pii(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "pii"
    assert verdict.passed is True
    assert isinstance(verdict.reason, str)
