"""Vietnamese number-word parser. Built incrementally over Tasks 9-13."""
from __future__ import annotations


_DIGITS: dict[str, int] = {
    "không": 0, "một": 1, "hai": 2, "ba": 3, "bốn": 4,
    "năm": 5, "sáu": 6, "bảy": 7, "tám": 8, "chín": 9,
}


def _normalize(text: str) -> str:
    return " ".join(text.lower().strip().split())


_UNIT_AFTER_MUOI: dict[str, int] = {**_DIGITS, "tư": 4, "lăm": 5, "mốt": 1}
_LE = {"lẻ", "linh"}


def _parse_under_100(tokens: list[str]) -> int:
    if not tokens:
        raise ValueError("empty under-100 token list")
    if len(tokens) == 1:
        t = tokens[0]
        if t in _DIGITS:
            return _DIGITS[t]
        if t == "mười":
            return 10
        raise ValueError(f"unknown 0-9 token: {t!r}")
    if len(tokens) == 2:
        a, b = tokens
        if a == "mười":
            if b == "lăm":
                return 15
            if b in _DIGITS:
                return 10 + _DIGITS[b]
            raise ValueError(f"bad teen unit: {b!r}")
        if b == "mươi":
            if a in _DIGITS and _DIGITS[a] >= 2:
                return _DIGITS[a] * 10
            raise ValueError(f"bad tens prefix: {a!r}")
    if len(tokens) == 3 and tokens[1] == "mươi":
        a, _, c = tokens
        if a not in _DIGITS or _DIGITS[a] < 2:
            raise ValueError(f"bad tens prefix: {a!r}")
        unit = _UNIT_AFTER_MUOI.get(c)
        if unit is None:
            raise ValueError(f"bad unit after '{a} mươi': {c!r}")
        return _DIGITS[a] * 10 + unit
    raise ValueError(f"under-100 cannot parse: {tokens!r}")


def _parse_under_1000(tokens: list[str]) -> int:
    if "trăm" not in tokens:
        return _parse_under_100(tokens)

    idx = tokens.index("trăm")
    head, tail = tokens[:idx], tokens[idx + 1:]

    if not head:
        hundreds = 1
    elif len(head) == 1 and head[0] in _DIGITS:
        hundreds = _DIGITS[head[0]]
    else:
        raise ValueError(f"bad hundreds prefix: {head!r}")

    if not tail:
        return hundreds * 100

    if tail[0] in _LE:
        rest = tail[1:]
        if len(rest) != 1 or rest[0] not in _DIGITS:
            raise ValueError(f"bad 'lẻ' tail: {tail!r}")
        return hundreds * 100 + _DIGITS[rest[0]]

    return hundreds * 100 + _parse_under_100(tail)


def parse_number_word(text: str) -> float:
    text = _normalize(text)
    if not text:
        raise ValueError("empty input")
    tokens = text.split()
    return _parse_under_1000(tokens)


def parse_expression(text: str) -> tuple[list[float], float]:
    raise NotImplementedError
