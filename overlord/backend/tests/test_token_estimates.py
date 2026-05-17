import pytest

from services.token_estimates import parse_tokens_estimate


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("~1800", 1800),
        ("2400 tokens saved (75%)", 2400),
        ("~5000 (mock)", 5000),
        ("", 0),
        ("no digits", 0),
    ],
)
def test_parse_tokens_estimate(raw, expected):
    assert parse_tokens_estimate(raw) == expected
