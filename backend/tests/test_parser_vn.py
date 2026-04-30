import pytest
from app.services.parser_vn import parse_number_word, parse_expression


@pytest.mark.parametrize("word,expected", [
    ("không", 0),
    ("một", 1),
    ("hai", 2),
    ("ba", 3),
    ("bốn", 4),
    ("năm", 5),
    ("sáu", 6),
    ("bảy", 7),
    ("tám", 8),
    ("chín", 9),
])
def test_parse_single_digits(word, expected):
    assert parse_number_word(word) == expected


@pytest.mark.parametrize("phrase,expected", [
    ("mười", 10),
    ("mười một", 11),
    ("mười hai", 12),
    ("mười lăm", 15),
    ("mười tám", 18),
])
def test_parse_teens(phrase, expected):
    assert parse_number_word(phrase) == expected
