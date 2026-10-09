"""Phone number validation shared by every schema that accepts a phone field.

The rule is deliberately international-friendly: an optional leading ``+``,
then digits with optional spaces, dashes, dots or brackets, and 7 to 15 digits
in total (the E.164 maximum). Nepali mobile (98XXXXXXXX), landline
(01-XXXXXXX) and ``+977`` numbers all pass. The value is stored as typed.

Only *input* schemas use this type. Read schemas stay permissive so that a
record saved before this rule existed can still be returned.
"""

import re
from typing import Annotated

from pydantic import AfterValidator, BeforeValidator

PHONE_MAX_LENGTH = 30
_ALLOWED = re.compile(r"^\+?[0-9\s\-().]+$")
MIN_DIGITS = 7
MAX_DIGITS = 15


def _empty_to_none(value: object) -> object:
    if isinstance(value, str) and not value.strip():
        return None
    return value


def validate_phone(value: str | None) -> str | None:
    if value is None:
        return None
    phone = value.strip()
    if len(phone) > PHONE_MAX_LENGTH:
        raise ValueError(f"Phone number must be at most {PHONE_MAX_LENGTH} characters.")
    if not _ALLOWED.fullmatch(phone):
        raise ValueError("Phone number can only contain digits, spaces, + - ( ) and dots.")
    digits = sum(ch.isdigit() for ch in phone)
    if not MIN_DIGITS <= digits <= MAX_DIGITS:
        raise ValueError(f"Phone number must have {MIN_DIGITS} to {MAX_DIGITS} digits.")
    return phone


PhoneNumber = Annotated[
    str | None,
    BeforeValidator(_empty_to_none),
    AfterValidator(validate_phone),
]
