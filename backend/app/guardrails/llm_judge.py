import json
import os
from typing import Any
import anthropic
from anthropic import Anthropic

from app.models.draft import Draft, EmailPitch, FlaggedClaim, GuardrailVerdict

RULE_NAME = "llm_judge"


def check_llm_judge(draft: Draft) -> GuardrailVerdict:
    """Evaluates pitch tone and claim traceability using an LLM-as-judge (Anthropic Claude)."""
    pitch = draft.generated_pitch
    if isinstance(pitch, EmailPitch):
        pitch_str = f"Subject: {pitch.subject}\nBody: {pitch.body}"
    elif isinstance(pitch, dict):
        pitch_str = f"Subject: {pitch.get('subject', '')}\nBody: {pitch.get('body', '')}"
    else:
        pitch_str = str(pitch)

    system_prompt = (
        "You are an expert PR compliance reviewer evaluating an outbound pitch.\n"
        "Assess two criteria:\n"
        "1. Tone alignment: Is the tone appropriate and non-pushy?\n"
        "2. Claim traceability: Can every factual claim in the pitch be traced to the prospect profile or campaign brief?\n\n"
        "Respond ONLY with a JSON object matching this exact schema (no markdown, no preamble):\n"
        "{\n"
        '  "passed": true | false,\n'
        '  "reason": "overall explanation",\n'
        '  "flagged_claims": [\n'
        '    {"claim": "verbatim claim", "reason": "why untraceable or tone mismatch"}\n'
        "  ]\n"
        "}\n"
        "If passed is true, flagged_claims must be []. If passed is false, flagged_claims must contain at least one entry."
    )

    user_prompt = (
        f"Prospect Profile:\n{json.dumps(draft.prospect_profile, indent=2)}\n\n"
        f"Campaign Brief:\n{json.dumps(draft.campaign_brief, indent=2)}\n\n"
        f"Target Channel: {draft.channel.value}\n\n"
        f"Generated Pitch:\n{pitch_str}"
    )

    try:
        client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", "dummy-key"))
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        response_text = ""
        if response.content and len(response.content) > 0:
            response_text = response.content[0].text

    except anthropic.APITimeoutError:
        return GuardrailVerdict(
            rule=RULE_NAME,
            passed=False,
            reason="Judge call timed out — failing safe.",
        )
    except anthropic.APIError as e:
        error_detail = str(e.message) if hasattr(e, "message") and e.message else str(e)
        return GuardrailVerdict(
            rule=RULE_NAME,
            passed=False,
            reason=f"Judge call failed ({error_detail}) — failing safe.",
        )
    except Exception as e:
        return GuardrailVerdict(
            rule=RULE_NAME,
            passed=False,
            reason=f"Judge call failed ({str(e)}) — failing safe.",
        )

    # JSON Parsing & Schema Validation
    try:
        data = json.loads(response_text)
    except Exception:
        return GuardrailVerdict(
            rule=RULE_NAME,
            passed=False,
            reason="Judge response was malformed or unparseable — failing safe.",
        )

    if not isinstance(data, dict):
        return GuardrailVerdict(
            rule=RULE_NAME,
            passed=False,
            reason="Judge response schema invalid — failing safe.",
        )

    passed_val = data.get("passed")
    reason_val = data.get("reason")
    flagged_claims_val = data.get("flagged_claims")

    if not isinstance(passed_val, bool) or not isinstance(reason_val, str):
        return GuardrailVerdict(
            rule=RULE_NAME,
            passed=False,
            reason="Judge response schema invalid — failing safe.",
        )

    if not isinstance(flagged_claims_val, list):
        return GuardrailVerdict(
            rule=RULE_NAME,
            passed=False,
            reason="Judge response schema invalid — failing safe.",
        )

    flagged_objects = []
    for fc in flagged_claims_val:
        if (
            not isinstance(fc, dict)
            or "claim" not in fc
            or "reason" not in fc
            or not isinstance(fc["claim"], str)
            or not isinstance(fc["reason"], str)
        ):
            return GuardrailVerdict(
                rule=RULE_NAME,
                passed=False,
                reason="Judge response schema invalid — failing safe.",
            )
        flagged_objects.append(
            FlaggedClaim(claim=fc["claim"], reason=fc["reason"])
        )

    # If passed is False, flagged_claims must contain at least 1 valid entry per PRD
    if not passed_val and len(flagged_objects) == 0:
        return GuardrailVerdict(
            rule=RULE_NAME,
            passed=False,
            reason="Judge response schema invalid — failing safe.",
        )

    return GuardrailVerdict(
        rule=RULE_NAME,
        passed=passed_val,
        reason=reason_val,
        flagged_claims=flagged_objects,
    )
