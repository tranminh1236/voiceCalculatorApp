"""Vietnamese number-word parser — full implementation."""
from __future__ import annotations

import re

_DIGITS: dict[str, int] = {
    "không": 0, "một": 1, "hai": 2, "ba": 3, "bốn": 4,
    "năm": 5, "sáu": 6, "bảy": 7, "tám": 8, "chín": 9,
}

_UNIT_AFTER_MUOI: dict[str, int] = {**_DIGITS, "tư": 4, "lăm": 5, "mốt": 1}
_LE = {"lẻ", "linh"}

_SCALES: dict[str, int] = {
    "nghìn": 1_000, "ngàn": 1_000,
    "triệu": 1_000_000,
    "tỷ": 1_000_000_000, "tỉ": 1_000_000_000,
}

# Largest first for left-to-right parsing
_SCALE_ORDER = ["tỷ", "tỉ", "triệu", "nghìn", "ngàn"]


def _normalize(text: str) -> str:
    return " ".join(text.lower().strip().split())


def _parse_under_100(tokens: list[str]) -> int:
    if not tokens:
        raise ValueError("empty")
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
            raise ValueError(f"bad unit: {c!r}")
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


def _apply_ruoi(value: float, unit_token: str | None) -> float:
    """Add half of the named unit. unit_token in {nghìn,ngàn,triệu,tỷ,tỉ,trăm} or None for 0.5."""
    if unit_token is None:
        return value + 0.5
    halves = {
        "nghìn": 500, "ngàn": 500,
        "triệu": 500_000,
        "tỷ": 500_000_000, "tỉ": 500_000_000,
        "trăm": 50,
    }
    return value + halves[unit_token]


def _parse_positive(tokens: list[str]) -> float:
    """Parse positive number with possible scale words and 'rưỡi'/'phẩy'."""
    # Decimal point ('phẩy')
    if "phẩy" in tokens:
        idx = tokens.index("phẩy")
        whole = _parse_positive(tokens[:idx]) if tokens[:idx] else 0
        frac_tokens = tokens[idx + 1:]
        frac_str = ""
        for t in frac_tokens:
            if t in _DIGITS:
                frac_str += str(_DIGITS[t])
            else:
                raise ValueError(f"bad decimal digit: {t!r}")
        return whole + float(f"0.{frac_str}") if frac_str else float(whole)

    # Trailing 'rưỡi'
    if tokens and tokens[-1] == "rưỡi":
        body = tokens[:-1]
        unit = None
        for t in reversed(body):
            if t in _SCALES or t == "trăm":
                unit = t
                break
        base = _parse_positive(body)
        return _apply_ruoi(base, unit)

    # Recursive split by scale, largest first
    for scale in _SCALE_ORDER:
        if scale in tokens:
            idx = tokens.index(scale)
            head = tokens[:idx]
            tail = tokens[idx + 1:]
            head_val = _parse_under_1000(head) if head else 1
            tail_val = _parse_positive(tail) if tail else 0
            return head_val * _SCALES[scale] + tail_val

    return _parse_under_1000(tokens)


def parse_number_word(text: str) -> float:
    text = _normalize(text)
    if not text:
        raise ValueError("empty input")
    tokens = text.split()
    if tokens and tokens[0] == "âm":
        return -_parse_positive(tokens[1:])
    return _parse_positive(tokens)


_DELIMITERS = {"cộng", "+", "và", "với"}
_TERMINATORS = {"bằng", "=", "tổng", "kết", "thúc"}
_PUNCT_RE = re.compile(r"[,.!?;:]")


def parse_expression(text: str) -> tuple[list[float], float]:
    """Parse 'A cộng B cộng C bằng' into ([A,B,C], sum)."""
    text = _PUNCT_RE.sub(" ", text)
    text = _normalize(text)
    if not text:
        raise ValueError("empty expression")

    tokens = text.split()
    cut_idx = None
    for i, t in enumerate(tokens):
        if t in _TERMINATORS:
            cut_idx = i
            break
    if cut_idx is not None:
        tokens = tokens[:cut_idx]
    if not tokens:
        raise ValueError("no number tokens before terminator")

    parts: list[list[str]] = []
    current: list[str] = []
    for t in tokens:
        if t in _DELIMITERS:
            if current:
                parts.append(current)
                current = []
        else:
            current.append(t)
    if current:
        parts.append(current)

    if not parts:
        raise ValueError("no parseable parts")

    numbers: list[float] = []
    for part in parts:
        numbers.append(parse_number_word(" ".join(part)))
    return numbers, sum(numbers)
