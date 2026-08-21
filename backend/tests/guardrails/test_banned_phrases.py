import pytest
from app.models.draft import Channel, Draft, EmailPitch, GuardrailVerdict
from app.guardrails.banned_phrases import check_banned_phrases


def create_draft(channel: Channel, generated_pitch) -> Draft:
    return Draft(
        channel=channel,
        prospect_profile={"company": "Acme Inc", "contact": "Jane Doe"},
        campaign_brief={"goal": "Product Launch", "tone": "Professional"},
        generated_pitch=generated_pitch,
    )


def test_clean_draft_passes():
    """Draft containing no banned phrases passes."""
    pitch = EmailPitch(
        subject="Exciting opportunity to collaborate",
        body="We would love to discuss how our platform can support your team's workflow goals.",
    )
    draft = create_draft(Channel.EMAIL, pitch)
    verdict = check_banned_phrases(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "banned_phrases"
    assert verdict.passed is True
    assert isinstance(verdict.reason, str)


def test_verbatim_banned_phrase_fails():
    """Draft containing a banned phrase verbatim fails and reason names the phrase."""
    pitch = EmailPitch(
        subject="Special Offer",
        body="We offer a risk-free trial for all new partners.",
    )
    draft = create_draft(Channel.EMAIL, pitch)
    verdict = check_banned_phrases(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "banned_phrases"
    assert verdict.passed is False
    assert isinstance(verdict.reason, str)
    assert len(verdict.reason.strip()) > 0
    assert "risk-free" in verdict.reason.lower()


def test_case_insensitive_matching_fails():
    """Banned phrase matching is case-insensitive (e.g. 'GUARANTEED ROI')."""
    pitch = "Get GUARANTEED ROI when you integrate our tool today!"
    draft = create_draft(Channel.SMS, pitch)
    verdict = check_banned_phrases(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "banned_phrases"
    assert verdict.passed is False
    assert isinstance(verdict.reason, str)
    assert len(verdict.reason.strip()) > 0
    assert "guaranteed roi" in verdict.reason.lower()


def test_phrase_within_sentence_fails():
    """Banned phrase embedded within a sentence fails."""
    pitch = "Our solution offers a 100% success rate across all enterprise deployments."
    draft = create_draft(Channel.WHATSAPP, pitch)
    verdict = check_banned_phrases(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "banned_phrases"
    assert verdict.passed is False
    assert isinstance(verdict.reason, str)
    assert len(verdict.reason.strip()) > 0
    assert "100% success rate" in verdict.reason.lower()


def test_similar_words_not_banned_passes():
    """Words sharing roots with banned phrases without matching the exact phrase pass."""
    # Contains 'guarantee' but not 'guaranteed roi', and 'risk' but not 'risk-free'
    pitch = EmailPitch(
        subject="We guarantee quality results",
        body="We manage technical risk through thorough testing and obligation management.",
    )
    draft = create_draft(Channel.EMAIL, pitch)
    verdict = check_banned_phrases(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "banned_phrases"
    assert verdict.passed is True
    assert isinstance(verdict.reason, str)


def test_substring_false_positive_passes():
    """
    Banned-phrase matching must respect word boundaries (e.g. regex \\b boundaries)
    and not match substring occurrences inside unrelated words (e.g. 'enact now' should not trigger 'act now').
    """
    pitch = EmailPitch(
        subject="Onboarding updates for your team",
        body="We will enact now-standard onboarding steps for all new clients.",
    )
    draft = create_draft(Channel.EMAIL, pitch)
    verdict = check_banned_phrases(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "banned_phrases"
    assert verdict.passed is True
    assert isinstance(verdict.reason, str)


def test_multiple_banned_phrases_reports_all():
    """
    Draft containing multiple banned phrases fails and reports ALL matched phrases in the reason.
    Reasoning: Reporting all matches in a single verification pass allows reviewers/authors
    to remediate every compliance issue at once rather than fixing one by one.
    """
    pitch = EmailPitch(
        subject="Act now for a limited time offer",
        body="We promise a 100% success rate with no obligation required.",
    )
    draft = create_draft(Channel.EMAIL, pitch)
    verdict = check_banned_phrases(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "banned_phrases"
    assert verdict.passed is False
    assert isinstance(verdict.reason, str)

    reason_lower = verdict.reason.lower()
    # Expecting all matches in the reason per PRD §2 specification
    assert "act now" in reason_lower
    assert "limited time offer" in reason_lower
    assert "100% success rate" in reason_lower
    assert "no obligation" in reason_lower
