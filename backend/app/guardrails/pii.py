import re
from app.models.draft import Draft, EmailPitch, GuardrailVerdict

RULE_NAME = "pii"


def is_luhn_valid(card_number_str: str) -> bool:
    """Validates a numeric credit card string using the Luhn checksum algorithm."""
    digits = [int(d) for d in card_number_str if d.isdigit()]
    if not (13 <= len(digits) <= 19):
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for i, digit in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = digit * 2
            checksum += doubled - 9 if doubled > 9 else doubled
        else:
            checksum += digit
    return checksum % 10 == 0


def check_pii(draft: Draft) -> GuardrailVerdict:
    """Scans a Draft's generated_pitch for SSNs, emails, phone numbers, and Luhn-valid credit card numbers."""
    pitch = draft.generated_pitch

    if isinstance(pitch, EmailPitch):
        text = f"{pitch.subject}\n{pitch.body}"
    elif isinstance(pitch, dict):
        text = f"{pitch.get('subject', '')}\n{pitch.get('body', '')}"
    else:
        text = str(pitch)

    detected: list[tuple[int, str]] = []

    # 1. SSN (XXX-XX-XXXX)
    ssn_pattern = r"\b\d{3}-\d{2}-\d{4}\b"
    for m in re.finditer(ssn_pattern, text):
        detected.append((m.start(), f"SSN detected at character {m.start()}"))

    # 2. Email Address
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    for m in re.finditer(email_pattern, text):
        detected.append((m.start(), f"Email address detected at character {m.start()}"))

    # 3. Phone Number (North American & International)
    # Handles (555) 123-4567, 555-123-4567, +44 20 7946 0958
    phone_pattern = r"(?:\+\d{1,3}[\s.-]?(?:\d{2,4}[\s.-]?){2,4}|(?:(?<=\s)|^|\b)(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}\b)"
    for m in re.finditer(phone_pattern, text):
        if not re.fullmatch(ssn_pattern, m.group()):
            detected.append((m.start(), f"Phone number detected at character {m.start()}"))

    # 4. Credit Card Number (13-19 digits, Luhn validated)
    cc_pattern = r"\b(?:\d[ -]?){13,19}\b"
    for m in re.finditer(cc_pattern, text):
        raw = m.group()
        clean = re.sub(r"\D", "", raw)
        if 13 <= len(clean) <= 19 and is_luhn_valid(clean):
            if not any(d[0] == m.start() for d in detected):
                detected.append((m.start(), f"Credit card detected at character {m.start()}"))

    if detected:
        detected.sort(key=lambda x: x[0])
        reasons = [item[1] for item in detected]
        return GuardrailVerdict(
            rule=RULE_NAME,
            passed=False,
            reason=" ".join(reasons),
        )

    return GuardrailVerdict(
        rule=RULE_NAME,
        passed=True,
        reason="No PII detected in draft.",
    )
