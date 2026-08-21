import pytest
from app.models.draft import Channel, Draft, EmailPitch, GuardrailVerdict
from app.guardrails.unsubstantiated_claims import check_unsubstantiated_claims


def create_draft(
    channel: Channel,
    generated_pitch,
    campaign_brief: dict = None,
    prospect_profile: dict = None,
) -> Draft:
    return Draft(
        channel=channel,
        prospect_profile=prospect_profile or {"company": "Acme Inc"},
        campaign_brief=campaign_brief or {"goal": "Product Launch"},
        generated_pitch=generated_pitch,
    )


def test_claim_matches_string_in_brief_passes():
    """Pitch containing '40% increase' passes when brief mentions '40% increase' as text."""
    pitch = EmailPitch(
        subject="Growth Results",
        body="Our software delivered a 40% increase in productivity for early users.",
    )
    brief = {"notes": "Internal testing showed we saw a 40% increase last quarter."}
    draft = create_draft(Channel.EMAIL, pitch, campaign_brief=brief)
    verdict = check_unsubstantiated_claims(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "unsubstantiated_claims"
    assert verdict.passed is True
    assert isinstance(verdict.reason, str)


def test_claim_matches_numeric_dict_value_passes():
    """Pitch containing '40% increase' passes when brief contains raw int 40 in a dict field."""
    pitch = "We achieved a 40% increase in team efficiency."
    brief = {"metrics": {"metric_value": 40, "metric_unit": "percent"}}
    draft = create_draft(Channel.SMS, pitch, campaign_brief=brief)
    verdict = check_unsubstantiated_claims(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "unsubstantiated_claims"
    assert verdict.passed is True
    assert isinstance(verdict.reason, str)


def test_unsubstantiated_dollar_claim_fails():
    """Pitch containing '$50,000 saved' fails when brief has decoy number (2024) but not matching 50,000."""
    pitch = "Clients saw $50,000 saved within the first 30 days of implementation."
    brief = {"goal": "Cost reduction campaign", "target_year": 2024}
    draft = create_draft(Channel.SMS, pitch, campaign_brief=brief)
    verdict = check_unsubstantiated_claims(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "unsubstantiated_claims"
    assert verdict.passed is False
    assert isinstance(verdict.reason, str)
    assert len(verdict.reason.strip()) > 0
    assert "50,000" in verdict.reason or "50000" in verdict.reason


def test_multiplier_symbol_normalization_passes():
    """Pitch containing '3x faster' passes when brief contains '3×' (proves x/× normalization)."""
    pitch = "Process data 3x faster than legacy solutions."
    brief = {"key_results": "Demonstrated 3× performance improvement."}
    draft = create_draft(Channel.SMS, pitch, campaign_brief=brief)
    verdict = check_unsubstantiated_claims(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "unsubstantiated_claims"
    assert verdict.passed is True
    assert isinstance(verdict.reason, str)


def test_marked_small_number_unsubstantiated_fails():
    """Pitch containing '3% increase' without matching brief value fails even with decoy number 5 in brief."""
    pitch = "Guaranteed 3% increase in conversion rates."
    brief = {"goal": "Boost conversion", "team_size": 5}
    draft = create_draft(Channel.WHATSAPP, pitch, campaign_brief=brief)
    verdict = check_unsubstantiated_claims(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "unsubstantiated_claims"
    assert verdict.passed is False
    assert isinstance(verdict.reason, str)
    assert "3%" in verdict.reason or "3" in verdict.reason


def test_bare_small_integer_exempt_passes():
    """Pitch containing 'in 3 easy steps' (bare integer < 10) passes without brief match."""
    pitch = "Onboard your entire team in 3 easy steps."
    brief = {"goal": "Simplified onboarding"}
    draft = create_draft(Channel.SMS, pitch, campaign_brief=brief)
    verdict = check_unsubstantiated_claims(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "unsubstantiated_claims"
    assert verdict.passed is True
    assert isinstance(verdict.reason, str)


def test_bare_large_integer_unsubstantiated_fails():
    """Pitch containing bare integer >= 10 ('25 years') fails when brief contains decoy year 2010 but not 25."""
    pitch = EmailPitch(
        subject="Industry Expertise",
        body="Our leadership team brings 25 years of experience to your enterprise.",
    )
    brief = {"company_info": "Established agency", "founded_year": 2010}
    draft = create_draft(Channel.EMAIL, pitch, campaign_brief=brief)
    verdict = check_unsubstantiated_claims(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "unsubstantiated_claims"
    assert verdict.passed is False
    assert isinstance(verdict.reason, str)
    assert "25" in verdict.reason


def test_bare_integer_exemption_boundary():
    """Proves boundary threshold BARE_INTEGER_EXEMPTION_THRESHOLD = 10: bare 9 is exempt (passes), bare 10 is NOT exempt (fails)."""
    # Bare 9 (below threshold 10): exempt -> passes
    pitch_9 = "Complete setup in 9 simple clicks."
    draft_9 = create_draft(Channel.SMS, pitch_9, campaign_brief={"goal": "Quick setup"})
    verdict_9 = check_unsubstantiated_claims(draft_9)
    assert verdict_9.rule == "unsubstantiated_claims"
    assert verdict_9.passed is True

    # Bare 10 (at threshold 10): not exempt -> fails without brief match
    pitch_10 = "Complete setup in 10 simple clicks."
    draft_10 = create_draft(Channel.SMS, pitch_10, campaign_brief={"goal": "Quick setup"})
    verdict_10 = check_unsubstantiated_claims(draft_10)
    assert verdict_10.rule == "unsubstantiated_claims"
    assert verdict_10.passed is False
    assert "10" in verdict_10.reason


def test_multiple_unsubstantiated_claims_reports_all():
    """Pitch containing multiple unsubstantiated claims fails and reports all in reason even with decoy numbers."""
    pitch = EmailPitch(
        subject="Proven Growth",
        body="Save $50,000 in operational costs with our 25 years of experience.",
    )
    brief = {"summary": "General PR pitch", "quarter": 2}
    draft = create_draft(Channel.EMAIL, pitch, campaign_brief=brief)
    verdict = check_unsubstantiated_claims(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "unsubstantiated_claims"
    assert verdict.passed is False
    assert isinstance(verdict.reason, str)

    reason_lower = verdict.reason.lower()
    assert "50,000" in reason_lower or "50000" in reason_lower
    assert "25" in reason_lower


def test_clean_pitch_no_numeric_claims_passes():
    """Clean pitch containing no numeric claims at all passes."""
    pitch = EmailPitch(
        subject="Collaboration Proposal",
        body="We are excited to discuss potential synergy between our organizations.",
    )
    brief = {"goal": "Strategic partnership"}
    draft = create_draft(Channel.EMAIL, pitch, campaign_brief=brief)
    verdict = check_unsubstantiated_claims(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "unsubstantiated_claims"
    assert verdict.passed is True
    assert isinstance(verdict.reason, str)
