from app.models.draft import Channel, Draft, EmailPitch, GuardrailVerdict

# Channel format & length limits (per PRD section 2, G3)
EMAIL_SUBJECT_MAX_LENGTH = 100
EMAIL_BODY_MAX_LENGTH = 2000
SMS_MAX_LENGTH = 160
WHATSAPP_MAX_LENGTH = 1000

RULE_NAME = "channel_format"


def check_channel_format(draft: Draft) -> GuardrailVerdict:
    """Checks a Draft's generated_pitch against its channel's format and length limits."""
    pitch = draft.generated_pitch

    if draft.channel == Channel.EMAIL:
        if isinstance(pitch, EmailPitch):
            subject = pitch.subject
            body = pitch.body
        elif isinstance(pitch, dict):
            subject = pitch.get("subject", "")
            body = pitch.get("body", "")
        else:
            subject = ""
            body = str(pitch)

        failures = []
        if len(subject) > EMAIL_SUBJECT_MAX_LENGTH:
            failures.append(
                f"Email subject length ({len(subject)}) exceeds limit of {EMAIL_SUBJECT_MAX_LENGTH} characters."
            )
        if len(body) > EMAIL_BODY_MAX_LENGTH:
            failures.append(
                f"Email body length ({len(body)}) exceeds limit of {EMAIL_BODY_MAX_LENGTH} characters."
            )

        if failures:
            return GuardrailVerdict(
                rule=RULE_NAME,
                passed=False,
                reason=" ".join(failures),
            )

    elif draft.channel == Channel.SMS:
        content = pitch if isinstance(pitch, str) else str(pitch)
        if len(content) > SMS_MAX_LENGTH:
            return GuardrailVerdict(
                rule=RULE_NAME,
                passed=False,
                reason=f"SMS length ({len(content)}) exceeds limit of {SMS_MAX_LENGTH} characters.",
            )

    elif draft.channel == Channel.WHATSAPP:
        content = pitch if isinstance(pitch, str) else str(pitch)
        if len(content) > WHATSAPP_MAX_LENGTH:
            return GuardrailVerdict(
                rule=RULE_NAME,
                passed=False,
                reason=f"WhatsApp message length ({len(content)}) exceeds limit of {WHATSAPP_MAX_LENGTH} characters.",
            )

    return GuardrailVerdict(
        rule=RULE_NAME,
        passed=True,
        reason="Pitch satisfies channel format and length limits.",
    )
