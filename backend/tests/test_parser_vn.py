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


@pytest.mark.parametrize("phrase,expected", [
    ("hai mươi", 20),
    ("hai mươi ba", 23),
    ("hai mươi tư", 24),
    ("hai mươi bốn", 24),
    ("hai mươi lăm", 25),
    ("hai mươi mốt", 21),
    ("ba mươi", 30),
    ("chín mươi chín", 99),
])
def test_parse_tens(phrase, expected):
    assert parse_number_word(phrase) == expected


@pytest.mark.parametrize("phrase,expected", [
    ("một trăm", 100),
    ("hai trăm", 200),
    ("một trăm lẻ năm", 105),
    ("một trăm linh năm", 105),
    ("trăm lẻ năm", 105),
    ("một trăm hai mươi ba", 123),
    ("chín trăm chín mươi chín", 999),
    ("một trăm mười", 110),
    ("một trăm mười tám", 118),
])
def test_parse_hundreds(phrase, expected):
    assert parse_number_word(phrase) == expected


@pytest.mark.parametrize("phrase,expected", [
    ("một nghìn", 1000),
    ("một nghìn không trăm năm mươi", 1050),
    ("một nghìn không trăm lẻ năm", 1005),
    ("hai nghìn rưỡi", 2500),
    ("ba trăm rưỡi", 350),
    ("mười rưỡi", 10.5),
    ("một triệu", 1_000_000),
    ("một tỷ", 1_000_000_000),
    ("hai phẩy năm", 2.5),
    ("không phẩy một", 0.1),
    ("âm năm", -5),
])
def test_parse_thousands_and_specials(phrase, expected):
    assert parse_number_word(phrase) == pytest.approx(expected)


def test_parse_expression_basic():
    nums, total = parse_expression("hai mươi ba cộng năm cộng mười hai bằng")
    assert nums == [23, 5, 12]
    assert total == 40


def test_parse_expression_with_hundreds_and_terminator():
    nums, total = parse_expression("hai mươi ba cộng năm cộng mười hai cộng trăm lẻ năm cộng mười tám bằng")
    assert nums == [23, 5, 12, 105, 18]
    assert total == 163


def test_parse_expression_no_terminator():
    nums, total = parse_expression("một cộng hai cộng ba")
    assert nums == [1, 2, 3]
    assert total == 6


def test_parse_expression_terminator_tong():
    nums, total = parse_expression("một cộng hai tổng")
    assert nums == [1, 2]
    assert total == 3


def test_parse_expression_terminator_equal_sign():
    nums, total = parse_expression("một cộng hai =")
    assert nums == [1, 2]
    assert total == 3


def test_parse_expression_punctuation_stripped():
    nums, total = parse_expression("một, cộng. hai!")
    assert nums == [1, 2]
    assert total == 3


def test_parse_expression_repeated_for_2a_rule():
    """Group rule '2a + 2c' is read as repeating the value twice."""
    nums, total = parse_expression("hai mươi ba cộng hai mươi ba cộng mười hai cộng mười hai bằng")
    assert nums == [23, 23, 12, 12]
    assert total == 70


def test_parse_expression_empty_raises():
    with pytest.raises(ValueError):
        parse_expression("")
