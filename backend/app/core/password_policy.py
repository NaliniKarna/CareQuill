"""
Password strength policy for new passwords (sign-up, reset, change).

CareQuill stores sensitive health records, so a weak password such as
"12345678" must never be accepted. The rules are deliberately simple and
explainable to the user; the frontend mirrors them (`frontend/src/lib/password.ts`)
to give instant feedback, but this module is the enforcement point.

Existing accounts are not affected at login: only *new* passwords are checked.
"""
from __future__ import annotations

import re

MIN_LENGTH = 10
MAX_LENGTH = 128

# Passwords that appear at the top of every breach list, plus product words.
# Matched after lowercasing and stripping digits/symbols (see `_core`).
_COMMON = frozenset(
    {
        "password", "passw0rd", "passcode", "letmein", "welcome", "admin", "administrator",
        "qwerty", "qwertyuiop", "asdfgh", "asdfghjkl", "zxcvbn", "zxcvbnm", "iloveyou",
        "monkey", "dragon", "football", "baseball", "master", "sunshine", "princess",
        "superman", "batman", "shadow", "trustno", "login", "secret", "changeme",
        "carequill", "medqueue", "health", "doctor", "patient", "hospital", "nepal",
        "kathmandu", "namaste", "abcdef", "abcdefgh", "test", "testing", "default",
        "guest", "hello", "freedom", "whatever", "starwars", "cricket", "ronaldo",
    }
)

_SEQUENCES = (
    "0123456789",
    "9876543210",
    "abcdefghijklmnopqrstuvwxyz",
    "zyxwvutsrqponmlkjihgfedcba",
    "qwertyuiopasdfghjklzxcvbnm",
    "mnbvcxzlkjhgfdsapoiuytrewq",
)


class WeakPasswordError(ValueError):
    """Raised with a message that is safe to show to the user."""


def _has_long_run(value: str, size: int = 4) -> bool:
    """True for 4+ identical characters in a row ("aaaa", "1111")."""
    return re.search(rf"(.)\1{{{size - 1},}}", value) is not None


def _has_sequence(value: str, size: int = 5) -> bool:
    """True for keyboard/alphabet/number runs such as "12345" or "qwert"."""
    lowered = value.lower()
    for sequence in _SEQUENCES:
        for start in range(len(sequence) - size + 1):
            if sequence[start : start + size] in lowered:
                return True
    return False


def _core(value: str) -> str:
    """Letters only, lowercased, after undoing look-alike swaps
    ("P@ssw0rd!" -> "password")."""
    swapped = value.lower().translate(str.maketrans("@$0!1|3", "asoiiie"))
    return re.sub(r"[^a-z]", "", swapped)


def validate_password_strength(password: str, *, email: str | None = None) -> str:
    """Returns `password` unchanged when it is strong enough, otherwise raises
    `WeakPasswordError` describing what to fix."""
    if len(password) < MIN_LENGTH:
        raise WeakPasswordError(f"Use at least {MIN_LENGTH} characters.")
    if len(password) > MAX_LENGTH:
        raise WeakPasswordError(f"Use at most {MAX_LENGTH} characters.")

    missing = []
    if not re.search(r"[a-z]", password):
        missing.append("a lowercase letter")
    if not re.search(r"[A-Z]", password):
        missing.append("an uppercase letter")
    if not re.search(r"\d", password):
        missing.append("a number")
    if not re.search(r"[^A-Za-z0-9]", password):
        missing.append("a symbol such as ! @ # or ?")
    if missing:
        raise WeakPasswordError("Add " + ", ".join(missing) + ".")

    if len(set(password)) < 5 or _has_long_run(password):
        raise WeakPasswordError("Avoid repeated characters such as 1111 or aaaa.")
    if _has_sequence(password):
        raise WeakPasswordError("Avoid sequences such as 12345, abcde or qwerty.")

    core = _core(password)
    # A common word with at most 3 extra letters around it ("Password", "admin1")
    # is guessable; a longer phrase that merely contains one is fine.
    if any(word in core and len(core) - len(word) <= 3 for word in _COMMON):
        raise WeakPasswordError(
            "This password is too common or guessable. Choose something unique."
        )

    if email:
        local = re.sub(r"[^a-z]", "", email.split("@", 1)[0].lower())
        if len(local) >= 4 and local in core:
            raise WeakPasswordError("Do not use your email address in your password.")
    return password
