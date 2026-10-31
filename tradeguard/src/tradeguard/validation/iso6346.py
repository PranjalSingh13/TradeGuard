"""ISO 6346 container number validation and generation (owner code + category + serial + check digit)."""
import random
import string


def _letter_values() -> dict[str, int]:
    vals, v = {}, 10
    for ch in string.ascii_uppercase:
        if v % 11 == 0:  # values that are multiples of 11 are skipped
            v += 1
        vals[ch] = v
        v += 1
    return vals


LETTER = _letter_values()


def iso6346_check_digit(first10: str) -> int:
    """Compute the ISO 6346 check digit for the 10-character prefix."""
    first10 = first10.replace(" ", "").upper()
    total = 0
    for i, ch in enumerate(first10):
        val = LETTER[ch] if ch.isalpha() else int(ch)
        total += val * (2 ** i)
    return (total % 11) % 10


def is_valid_container(num: str) -> bool:
    """Verify if an 11-character container number follows the ISO 6346 specification."""
    num = num.replace(" ", "").upper()
    if len(num) != 11 or not num[:3].isalpha() or num[3] not in "UJZ" or not num[4:].isdigit():
        return False
    return iso6346_check_digit(num[:10]) == int(num[10])


def generate_container_number(
    owner_prefix: str | None = None,
    category: str = "U",
    rng: random.Random | None = None,
) -> str:
    """Generate a valid 11-character ISO 6346 container number."""
    r = rng or random.Random()
    if not owner_prefix:
        owner_prefix = "".join(r.choice(string.ascii_uppercase) for _ in range(3))
    else:
        owner_prefix = owner_prefix.upper()[:3]
    category = category.upper()
    if category not in ("U", "J", "Z"):
        category = "U"
    serial = "".join(str(r.randint(0, 9)) for _ in range(6))
    first10 = f"{owner_prefix}{category}{serial}"
    check_digit = iso6346_check_digit(first10)
    return f"{first10}{check_digit}"
