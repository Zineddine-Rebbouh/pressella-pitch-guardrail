import json
from unittest.mock import MagicMock, patch
import pytest

import anthropic

from app.models.draft import Channel, Draft, EmailPitch, GuardrailVerdict
from app.guardrails.llm_judge import check_llm_judge


def create_draft() -> Draft:
    return Draft(
        channel=Channel.EMAIL,
        prospect_profile={"company": "Acme Inc", "industry": "Tech"},
        campaign_brief={"goal": "Product Launch", "tone": "Professional"},
        generated_pitch=EmailPitch(
            subject="Introducing Acme Analytics",
            body="Our platform helps tech companies streamline data workflows.",
        ),
    )


def build_mock_response(text_content: str):
    mock_msg = MagicMock()
    mock_content = MagicMock()
    mock_content.text = text_content
    mock_msg.content = [mock_content]
    return mock_msg


@patch("app.guardrails.llm_judge.Anthropic")
def test_happy_path_pass(mock_anthropic):
    """Happy path pass: Judge returns valid JSON with passed=True, reason, and empty flagged_claims."""
    response_payload = {
        "passed": True,
        "reason": "Tone aligns with brief and all claims are traceable to profile.",
        "flagged_claims": [],
    }
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client
    mock_client.messages.create.return_value = build_mock_response(
        json.dumps(response_payload)
    )

    draft = create_draft()
    verdict = check_llm_judge(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "llm_judge"
    assert verdict.passed is True
    assert verdict.reason == response_payload["reason"]


@patch("app.guardrails.llm_judge.Anthropic")
def test_happy_path_fail(mock_anthropic):
    """Happy path fail: Judge returns valid JSON with passed=False, reason, and non-empty flagged_claims."""
    response_payload = {
        "passed": False,
        "reason": "Tone is overly aggressive and claim cannot be traced.",
        "flagged_claims": [
            {
                "claim": "Streamline data workflows by 50%",
                "reason": "Metric not found in campaign brief or profile.",
            }
        ],
    }
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client
    mock_client.messages.create.return_value = build_mock_response(
        json.dumps(response_payload)
    )

    draft = create_draft()
    verdict = check_llm_judge(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "llm_judge"
    assert verdict.passed is False
    assert verdict.reason == response_payload["reason"]


@patch("app.guardrails.llm_judge.Anthropic")
def test_failsafe_unparseable_json(mock_anthropic):
    """Fail-safe: Judge returns unparseable/malformed JSON string."""
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client
    mock_client.messages.create.return_value = build_mock_response(
        "I am an AI assistant and I think the pitch looks good."
    )

    draft = create_draft()
    verdict = check_llm_judge(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "llm_judge"
    assert verdict.passed is False
    assert (
        verdict.reason
        == "Judge response was malformed or unparseable — failing safe."
    )


@patch("app.guardrails.llm_judge.Anthropic")
def test_failsafe_missing_required_fields(mock_anthropic):
    """Fail-safe: Valid JSON missing required field 'reason'."""
    invalid_payload = {"passed": True}
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client
    mock_client.messages.create.return_value = build_mock_response(
        json.dumps(invalid_payload)
    )

    draft = create_draft()
    verdict = check_llm_judge(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "llm_judge"
    assert verdict.passed is False
    assert verdict.reason == "Judge response schema invalid — failing safe."


@patch("app.guardrails.llm_judge.Anthropic")
def test_failsafe_non_boolean_passed(mock_anthropic):
    """Fail-safe: Valid JSON but 'passed' field is string 'yes' instead of boolean."""
    invalid_payload = {
        "passed": "yes",
        "reason": "Pitch is good.",
        "flagged_claims": [],
    }
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client
    mock_client.messages.create.return_value = build_mock_response(
        json.dumps(invalid_payload)
    )

    draft = create_draft()
    verdict = check_llm_judge(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "llm_judge"
    assert verdict.passed is False
    assert verdict.reason == "Judge response schema invalid — failing safe."


@patch("app.guardrails.llm_judge.Anthropic")
def test_failsafe_failed_verdict_empty_flagged_claims(mock_anthropic):
    """Fail-safe: Valid JSON with passed=False but empty flagged_claims list (schema invalid per PRD)."""
    invalid_payload = {
        "passed": False,
        "reason": "Tone is mismatched.",
        "flagged_claims": [],
    }
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client
    mock_client.messages.create.return_value = build_mock_response(
        json.dumps(invalid_payload)
    )

    draft = create_draft()
    verdict = check_llm_judge(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "llm_judge"
    assert verdict.passed is False
    assert verdict.reason == "Judge response schema invalid — failing safe."


@patch("app.guardrails.llm_judge.Anthropic")
def test_failsafe_timeout_error(mock_anthropic):
    """Fail-safe: LLM API call times out."""
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client
    mock_request = MagicMock()
    mock_client.messages.create.side_effect = anthropic.APITimeoutError(
        request=mock_request
    )

    draft = create_draft()
    verdict = check_llm_judge(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "llm_judge"
    assert verdict.passed is False
    assert verdict.reason == "Judge call timed out — failing safe."


@patch("app.guardrails.llm_judge.Anthropic")
def test_failsafe_connection_error(mock_anthropic):
    """Fail-safe: LLM API call raises connection error."""
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client
    mock_request = MagicMock()
    mock_client.messages.create.side_effect = anthropic.APIConnectionError(
        message="Connection refused", request=mock_request
    )

    draft = create_draft()
    verdict = check_llm_judge(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "llm_judge"
    assert verdict.passed is False
    assert "Judge call failed" in verdict.reason
    assert "Connection refused" in verdict.reason
    assert "failing safe." in verdict.reason


@patch("app.guardrails.llm_judge.Anthropic")
def test_failsafe_malformed_flagged_claim_entry(mock_anthropic):
    """Fail-safe: Valid JSON with passed=False but flagged_claims entry is missing required 'reason' key."""
    invalid_payload = {
        "passed": False,
        "reason": "Tone is mismatched.",
        "flagged_claims": [{"claim": "Unsubstantiated claim text"}],
    }
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client
    mock_client.messages.create.return_value = build_mock_response(
        json.dumps(invalid_payload)
    )

    draft = create_draft()
    verdict = check_llm_judge(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "llm_judge"
    assert verdict.passed is False
    assert verdict.reason == "Judge response schema invalid — failing safe."


@patch("app.guardrails.llm_judge.Anthropic")
def test_markdown_code_fence_stripping(mock_anthropic):
    """Parses JSON successfully even if model wraps response in ```json ... ``` markdown code fences."""
    response_payload = {
        "passed": True,
        "reason": "Tone aligns with brief and all claims are traceable to profile.",
        "flagged_claims": [],
    }
    raw_markdown = f"```json\n{json.dumps(response_payload)}\n```"
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client
    mock_client.messages.create.return_value = build_mock_response(raw_markdown)

    draft = create_draft()
    verdict = check_llm_judge(draft)

    assert isinstance(verdict, GuardrailVerdict)
    assert verdict.rule == "llm_judge"
    assert verdict.passed is True
    assert verdict.reason == response_payload["reason"]

