import json
from unittest.mock import MagicMock, patch
import pytest
import anthropic

from app.models.draft import Channel, EmailPitch
from app.services.generator import GenerationError, generate_pitch


def build_mock_response(text_content: str) -> MagicMock:
    """Helper to create a mocked Anthropic message response."""
    mock_msg = MagicMock()
    mock_content = MagicMock()
    mock_content.text = text_content
    mock_msg.content = [mock_content]
    return mock_msg


@patch("app.services.generator.Anthropic")
def test_generate_pitch_email_happy_path(mock_anthropic):
    """Case 1: Email channel returns valid JSON {"subject": "...", "body": "..."}

    Verifies function returns a populated EmailPitch model instance.
    """
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client

    email_json = json.dumps(
        {
            "subject": "Exclusive PR Pitch for TechCrunch",
            "body": "Hi Jane, we are launching Acme AI to revolutionize data pipelines.",
        }
    )
    mock_client.messages.create.return_value = build_mock_response(email_json)

    prospect = {"name": "Jane Doe", "publication": "TechCrunch"}
    campaign = {"goal": "Product Announcement", "key_message": "Acme AI Launch"}

    result = generate_pitch(prospect, campaign, Channel.EMAIL)

    assert isinstance(result, EmailPitch)
    assert result.subject == "Exclusive PR Pitch for TechCrunch"
    assert result.body == "Hi Jane, we are launching Acme AI to revolutionize data pipelines."


@patch("app.services.generator.Anthropic")
def test_generate_pitch_sms_happy_path(mock_anthropic):
    """Case 2: SMS channel returns plain string within format limits.

    Verifies function returns plain str instance.
    """
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client

    sms_text = "Hi Jane! Acme AI launches today. Check out our tech at acme.ai/launch"
    mock_client.messages.create.return_value = build_mock_response(sms_text)

    prospect = {"name": "Jane Doe"}
    campaign = {"goal": "Launch alert"}

    result = generate_pitch(prospect, campaign, Channel.SMS)

    assert isinstance(result, str)
    assert result == sms_text


@patch("app.services.generator.Anthropic")
def test_generate_pitch_whatsapp_happy_path(mock_anthropic):
    """Case 3: WhatsApp channel returns plain string within format limits.

    Verifies function returns plain str instance for WhatsApp enum.
    """
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client

    whatsapp_text = "Hello Jane! Reaching out regarding Acme AI's product release. Would love to share early details."
    mock_client.messages.create.return_value = build_mock_response(whatsapp_text)

    prospect = {"name": "Jane Doe"}
    campaign = {"goal": "Partner outreach"}

    result = generate_pitch(prospect, campaign, Channel.WHATSAPP)

    assert isinstance(result, str)
    assert result == whatsapp_text


@patch("app.services.generator.Anthropic")
def test_generate_pitch_system_prompt_grounding_instruction(mock_anthropic):
    """Case 4: System prompt construction includes explicit grounding instructions.

    Asserts that the system parameter sent to Anthropic messages.create contains
    explicit instructions requiring the LLM to strictly rely on facts from the supplied
    campaign_brief and prospect_profile (first line of defense against hallucinations).
    Mentions of field names alone do NOT satisfy this assertion — a grounding directive
    is explicitly required.
    """
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client
    mock_client.messages.create.return_value = build_mock_response(
        json.dumps({"subject": "Test", "body": "Body"})
    )

    prospect = {"company": "Acme Corp"}
    campaign = {"goal": "Media Coverage"}

    generate_pitch(prospect, campaign, Channel.EMAIL)

    assert mock_client.messages.create.called
    kwargs = mock_client.messages.create.call_args.kwargs

    # Check system prompt string or messages list for strict factual grounding rules
    system_prompt = kwargs.get("system", "")
    if not system_prompt and "messages" in kwargs:
        # If passed inside messages payload
        system_prompt = " ".join(
            str(m.get("content", "")) for m in kwargs["messages"] if m.get("role") == "system"
        )

    prompt_lower = system_prompt.lower()
    has_grounding_instruction = (
        ("only" in prompt_lower and ("brief" in prompt_lower or "profile" in prompt_lower or "fact" in prompt_lower or "data" in prompt_lower or "rely" in prompt_lower or "use" in prompt_lower))
        or "do not extrapolate" in prompt_lower
        or "strictly ground" in prompt_lower
        or "do not fabricate" in prompt_lower
        or "must be traceable" in prompt_lower
    )
    assert has_grounding_instruction, (
        f"System prompt lacks an explicit factual grounding constraint directive. Prompt was: '{system_prompt}'"
    )


@patch("app.services.generator.Anthropic")
def test_generate_pitch_email_malformed_json_raises_generation_error(mock_anthropic):
    """Case 5a: Email channel with non-JSON string response raises GenerationError."""
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client
    mock_client.messages.create.return_value = build_mock_response(
        "Here is your email pitch: Subject: Hello, Body: World"
    )

    prospect = {"name": "Jane"}
    campaign = {"goal": "Outreach"}

    with pytest.raises(GenerationError) as exc_info:
        generate_pitch(prospect, campaign, Channel.EMAIL)

    assert "JSON" in str(exc_info.value) or "malformed" in str(exc_info.value).lower() or "parse" in str(exc_info.value).lower()


@patch("app.services.generator.Anthropic")
def test_generate_pitch_email_missing_fields_raises_generation_error(mock_anthropic):
    """Case 5b: Email channel returning valid JSON but missing 'body' key raises GenerationError."""
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client
    mock_client.messages.create.return_value = build_mock_response(
        json.dumps({"subject": "Only a subject line"})
    )

    prospect = {"name": "Jane"}
    campaign = {"goal": "Outreach"}

    with pytest.raises(GenerationError) as exc_info:
        generate_pitch(prospect, campaign, Channel.EMAIL)

    assert "schema" in str(exc_info.value).lower() or "missing" in str(exc_info.value).lower() or "body" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()


@patch("app.services.generator.Anthropic")
def test_generate_pitch_timeout_preserves_error_detail(mock_anthropic):
    """Case 6a: Anthropic API timeout raises GenerationError preserving underlying detail."""
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client
    mock_request = MagicMock()
    timeout_err = anthropic.APITimeoutError(request=mock_request)
    mock_client.messages.create.side_effect = timeout_err

    prospect = {"name": "Jane"}
    campaign = {"goal": "Outreach"}

    with pytest.raises(GenerationError) as exc_info:
        generate_pitch(prospect, campaign, Channel.SMS)

    # Require BOTH proper exception chaining AND message text
    assert exc_info.value.__cause__ is timeout_err
    assert "timeout" in str(exc_info.value).lower() or "timed out" in str(exc_info.value).lower()


@patch("app.services.generator.Anthropic")
def test_generate_pitch_connection_error_preserves_error_detail(mock_anthropic):
    """Case 6b: Anthropic API connection error raises GenerationError preserving detail."""
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client
    mock_request = MagicMock()
    conn_err = anthropic.APIConnectionError(message="Connection refused to Anthropic server", request=mock_request)
    mock_client.messages.create.side_effect = conn_err

    prospect = {"name": "Jane"}
    campaign = {"goal": "Outreach"}

    with pytest.raises(GenerationError) as exc_info:
        generate_pitch(prospect, campaign, Channel.SMS)

    # Require BOTH proper exception chaining AND exact dynamic message verbatim
    assert exc_info.value.__cause__ is conn_err
    assert "Connection refused to Anthropic server" in str(exc_info.value)



@patch("app.services.generator.Anthropic")
def test_generate_pitch_over_limit_response_returns_raw_string(mock_anthropic):
    """Case 7: Over-limit response for SMS returns raw string without raising GenerationError.

    DESIGN CHOICE & JUSTIFICATION:
    `generate_pitch` DOES NOT enforce channel length limits during generation time (it returns
    whatever raw output the LLM produced). Length enforcement is intentionally decoupled and
    delegated to `check_channel_format` (G3) during verification time.

    RATIONALE:
    1. Separation of Concerns: Generation synthesizes the draft; verification audits it.
    2. Audit Trail Integrity: If generation failed closed on length, over-limit LLM drafts
       would be aborted and lost, preventing compliance auditing or evaluation metrics on model output.
    3. PRD §4.1 Alignment: PRD §4.1 states that POST /drafts creates a draft with status
       `pending_verification` without running guardrail checks. PRD §2 G3 explicitly specifies
       that channel limits are evaluated when the draft is verified.
    """
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client

    # 180 characters string > 160 char SMS limit
    over_limit_sms = "X" * 180
    mock_client.messages.create.return_value = build_mock_response(over_limit_sms)

    prospect = {"name": "Jane"}
    campaign = {"goal": "Outreach"}

    result = generate_pitch(prospect, campaign, Channel.SMS)

    assert isinstance(result, str)
    assert result == over_limit_sms
    assert len(result) == 180
