import re
from app.models.draft import Draft, EmailPitch, GuardrailVerdict

# Starter deny-list of banned phrases (per PRD section 2, G2)
BANNED_PHRASES: list[str] = [
    "guaranteed ROI",
    "risk-free",
    "100% success rate",
    "no obligation",
    "act now",
    "limited time offer",
    "as seen in every major outlet",
    "trusted by industry leaders",
]

RULE_NAME = "banned_phrases"


def check_banned_phrases(draft: Draft) -> GuardrailVerdict:
    """Checks a Draft's generated_pitch for banned phrases using word-boundary-aware matching."""
    pitch = draft.generated_pitch

    if isinstance(pitch, EmailPitch):
        text = f"{pitch.subject}\n{pitch.body}"
    elif isinstance(pitch, dict):
        text = f"{pitch.get('subject', '')}\n{pitch.get('body', '')}"
    else:
        text = str(pitch)

    matched_phrases = []
    for phrase in BANNED_PHRASES:
        pattern = rf"\b{re.escape(phrase)}\b"
        if re.search(pattern, text, re.IGNORECASE):
            matched_phrases.append(phrase)

    if matched_phrases:
        phrases_str = ", ".join(matched_phrases)
        return GuardrailVerdict(
            rule=RULE_NAME,
            passed=False,
            reason=f"Draft contains banned phrase(s): {phrases_str}.",
        )

    return GuardrailVerdict(
        rule=RULE_NAME,
        passed=True,
        reason="No banned phrases detected in draft.",
    )
