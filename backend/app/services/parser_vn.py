"""Vietnamese number-word parser. Built incrementally over Tasks 9-13."""
from __future__ import annotations


_DIGITS: dict[str, int] = {
    "không": 0, "một": 1, "hai": 2, "ba": 3, "bốn": 4,
    "năm": 5, "sáu": 6, "bảy": 7, "tám": 8, "chín": 9,
}

_UNIT_AFTER_MUOI: dict[str, int] = {
    **_DIGITS,
    "tư": 4,
    "lăm": 5,
    "mốt": 1,
}


def _normalize(text: str) -> str:
    return " ".join(text.lower().strip().split())


def parse_number_word(text: str) -> float:
    """Parse a Vietnamese number phrase (no operators) into a number."""
    text = _normalize(text)
    if not text:
        raise ValueError("empty input")
    tokens = text.split()
    return _parse_tokens(tokens)


def _parse_tokens(tokens: list[str]) -> float:
    if len(tokens) == 1:
        t = tokens[0]
        if t in _DIGITS:
            return _DIGITS[t]
        if t == "mười":
            return 10
        raise ValueError(f"unknown token: {t!r}")

    if len(tokens) == 2:
        a, b = tokens
        if a == "mười":
            if b == "lăm":
                return 15
            if b in _DIGITS:
                return 10 + _DIGITS[b]
            raise ValueError(f"unknown unit after 'mười': {b!r}")
        if b == "mươi":
            if a in _DIGITS and _DIGITS[a] >= 2:
                return _DIGITS[a] * 10
            raise ValueError(f"invalid tens prefix: {a!r}")

    if len(tokens) == 3 and tokens[1] == "mươi":
        a, _, c = tokens
        if a not in _DIGITS or _DIGITS[a] < 2:
            raise ValueError(f"invalid tens prefix: {a!r}")
        tens = _DIGITS[a] * 10
        unit = _UNIT_AFTER_MUOI.get(c)
        if unit is None:
            raise ValueError(f"unknown unit after '{a} mươi': {c!r}")
        return tens + unit

    raise ValueError(f"cannot parse: {tokens!r}")


def parse_expression(text: str) -> tuple[list[float], float]:
    """Parse expression. Implemented in Task 13."""
    raise NotImplementedError
