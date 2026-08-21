import re
from typing import Any
from app.models.draft import Draft, EmailPitch, GuardrailVerdict

BARE_INTEGER_EXEMPTION_THRESHOLD = 10
RULE_NAME = "unsubstantiated_claims"

# Matches $, %, x/× multipliers, and numbers
CLAIM_REGEX = re.compile(
    r"(\$\s*\d+(?:,\d{3})*(?:\.\d+)?)|"  # Dollar amounts ($50,000, $500)
    r"(\b\d+(?:\.\d+)?\s*%)|"  # Percentages (40%, 3%)
    r"(\b\d+(?:\.\d+)?\s*[xX×])|"  # Multipliers (3x, 3×)
    r"(\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b|\b\d+(?:\.\d+)?\b)"  # Bare numbers (50,000, 25, 3)
)


def harvest_input_numbers(data: Any) -> set[float | int]:
    """Recursively extracts numeric values from dict/list structure via direct isinstance and text stringification."""
    numbers: set[float | int] = set()

    def _traverse(val: Any):
        if isinstance(val, bool):
            return
        elif isinstance(val, (int, float)):
            numbers.add(val)
            if isinstance(val, float) and val.is_integer():
                numbers.add(int(val))
        elif isinstance(val, str):
            for match in re.finditer(r"\d+(?:,\d{3})*(?:\.\d+)?", val):
                num_str = match.group().replace(",", "")
                try:
                    num_val = float(num_str) if "." in num_str else int(num_str)
                    numbers.add(num_val)
                    if isinstance(num_val, float) and num_val.is_integer():
                        numbers.add(int(num_val))
                except ValueError:
                    pass
        elif isinstance(val, dict):
            for v in val.values():
                _traverse(v)
        elif isinstance(val, (list, tuple, set)):
            for item in val:
                _traverse(item)

    _traverse(data)
    return numbers


def check_unsubstantiated_claims(draft: Draft) -> GuardrailVerdict:
    """Checks a Draft's generated_pitch for numeric claims that cannot be substantiated by input data."""
    pitch = draft.generated_pitch

    if isinstance(pitch, EmailPitch):
        pitch_text = f"{pitch.subject}\n{pitch.body}"
    elif isinstance(pitch, dict):
        pitch_text = f"{pitch.get('subject', '')}\n{pitch.get('body', '')}"
    else:
        pitch_text = str(pitch)

    # Harvest all numeric values present in inputs (campaign_brief and prospect_profile)
    input_numbers = harvest_input_numbers(draft.campaign_brief) | harvest_input_numbers(
        draft.prospect_profile
    )

    unsubstantiated: list[str] = []

    for match in CLAIM_REGEX.finditer(pitch_text):
        raw_claim = match.group().strip()
        is_marked = bool(re.search(r"[\$%xX×]", raw_claim))

        clean_str = re.sub(r"[\$%xX×,\s]", "", raw_claim)
        try:
            num_val = float(clean_str) if "." in clean_str else int(clean_str)
        except ValueError:
            continue

        # Bare integer exemption check
        if (
            not is_marked
            and isinstance(num_val, int)
            and num_val < BARE_INTEGER_EXEMPTION_THRESHOLD
        ):
            continue

        # Check if number is present in input numbers
        is_substantiated = (
            num_val in input_numbers
            or float(num_val) in input_numbers
            or (isinstance(num_val, float) and int(num_val) in input_numbers)
        )

        if not is_substantiated:
            unsubstantiated.append(raw_claim)

    if unsubstantiated:
        claims_str = ", ".join(unsubstantiated)
        return GuardrailVerdict(
            rule=RULE_NAME,
            passed=False,
            reason=f"Unsubstantiated numeric claim(s) detected: {claims_str}.",
        )

    return GuardrailVerdict(
        rule=RULE_NAME,
        passed=True,
        reason="All numeric claims in pitch are substantiated by input data.",
    )
