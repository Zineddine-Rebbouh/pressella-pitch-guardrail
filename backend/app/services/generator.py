import json
import os
from typing import Any, Union

import anthropic
from anthropic import Anthropic

from app.models.draft import Channel, EmailPitch


class GenerationError(Exception):
    """Custom exception raised when pitch generation fails."""

    pass


def generate_pitch(
    prospect_profile: dict[str, Any],
    campaign_brief: dict[str, Any],
    channel: Channel,
) -> Union[EmailPitch, str]:
    """Generates a pitch message for the specified channel using Anthropic Claude.

    Args:
        prospect_profile: Dict containing prospect background data.
        campaign_brief: Dict containing campaign goals, messaging, and constraints.
        channel: Outreach channel enum (email, sms, whatsapp).

    Returns:
        EmailPitch instance for email channel, or str for sms/whatsapp.

    Raises:
        GenerationError: On LLM API timeout, API connection error, malformed response,
                        or schema validation error.
    """
    system_prompt = (
        "You are an expert PR outreach assistant drafting pitches.\n"
        "Strict Grounding Instruction: Only use facts present in the campaign_brief and prospect_profile provided; "
        "do not extrapolate or fabricate details beyond what is given.\n\n"
    )

    if channel == Channel.EMAIL:
        system_prompt += (
            "Write an email pitch. Respond ONLY with a valid JSON object matching this exact schema (no markdown formatting, no preamble):\n"
            '{\n  "subject": "...",\n  "body": "..."\n}'
        )
    else:
        system_prompt += (
            f"Write a concise outreach message suitable for {channel.value}.\n"
            "Respond with ONLY the raw message text."
        )

    user_prompt = (
        f"Prospect Profile:\n{json.dumps(prospect_profile, indent=2)}\n\n"
        f"Campaign Brief:\n{json.dumps(campaign_brief, indent=2)}\n\n"
        f"Channel: {channel.value}"
    )

    try:
        client = Anthropic()
        response = client.messages.create(
            model="kr/claude-sonnet-4.5",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        response_text = ""
        if response.content and len(response.content) > 0:
            response_text = response.content[0].text

    except anthropic.APITimeoutError as e:
        raise GenerationError(f"Anthropic API call timed out: {e}") from e
    except anthropic.APIConnectionError as e:
        error_msg = getattr(e, "message", str(e))
        raise GenerationError(f"API connection error: {error_msg}") from e
    except anthropic.APIError as e:
        error_msg = getattr(e, "message", str(e))
        raise GenerationError(f"API call failed: {error_msg}") from e
    except Exception as e:
        raise GenerationError(f"Generation failed: {e}") from e

    if channel == Channel.EMAIL:
        cleaned_text = response_text.strip()
        if cleaned_text.startswith("```"):
            lines = cleaned_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned_text = "\n".join(lines).strip()

        try:
            data = json.loads(cleaned_text)
        except Exception as e:
            raise GenerationError(
                f"Generation response was malformed JSON: {cleaned_text}"
            ) from e

        if not isinstance(data, dict):
            raise GenerationError(
                "Generation response schema invalid: expected JSON object"
            )

        subject = data.get("subject")
        body = data.get("body")

        if not isinstance(subject, str) or not isinstance(body, str):
            raise GenerationError(
                "Generation response schema invalid: missing or non-string 'subject' or 'body' keys"
            )

        return EmailPitch(subject=subject, body=body)

    return response_text
