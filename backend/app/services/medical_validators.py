"""
Medical Document Validators

Validation helpers for Indian medical document fields, per the formats
described in sample_documents_guide.md (e.g. doctor registration numbers).
"""

import re
from typing import Optional, Tuple

# Indian state codes used in medical registration numbers (from the guide)
_STATE_CODES = {
    "KA", "MH", "DL", "TN", "GJ", "AP", "UP", "WB", "KL",
    # Common additional Indian state/UT medical-council codes
    "TS", "RJ", "MP", "BR", "OR", "OD", "PB", "HR", "JK", "AS",
    "CG", "JH", "UK", "GA", "HP", "CH", "PY", "AN",
}

# State registration: STATE/NUMBER/YEAR  e.g. KA/45678/2015
_STATE_REG = re.compile(r"^([A-Z]{2})/(\d{3,6})/(\d{4})$")

# Ayurveda (national): AYUR/STATE/NUMBER/YEAR  e.g. AYUR/KL/2345/2019
_AYUR_REG = re.compile(r"^AYUR/([A-Z]{2})/(\d{3,6})/(\d{4})$")


def validate_doctor_registration(reg_number: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Validate an Indian doctor registration number against the documented formats.

    Returns:
        (is_valid, note)
        - is_valid: True if the number matches a known format
        - note: explanation when invalid/unrecognized, else None
    """
    if not reg_number or not isinstance(reg_number, str):
        return False, "Registration number missing or unreadable."

    reg = reg_number.strip().upper().replace(" ", "")

    # Ayurveda national format
    ayur = _AYUR_REG.match(reg)
    if ayur:
        state = ayur.group(1)
        if state in _STATE_CODES:
            return True, None
        return True, f"Ayurveda registration uses uncommon state code '{state}'."

    # State format
    m = _STATE_REG.match(reg)
    if m:
        state = m.group(1)
        if state in _STATE_CODES:
            return True, None
        return False, f"Unrecognized state code '{state}' in registration number."

    return False, (
        f"Registration number '{reg_number}' does not match the expected format "
        f"(STATE/NUMBER/YEAR, e.g. KA/45678/2015, or AYUR/STATE/NUMBER/YEAR)."
    )
