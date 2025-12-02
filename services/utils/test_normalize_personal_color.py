import os
import pytest

# ensure utils.shared import won't fail due to missing OPENAI_API_KEY during tests
os.environ.setdefault("OPENAI_API_KEY", "test-placeholder-key")

from utils.shared import normalize_personal_color


@pytest.mark.parametrize(
    "primary,sub,expected",
    [
        (None, None, ("웜", "봄")),
        ("Bright Warm", None, ("웜", "봄")),
        ("Warm - Autumn", None, ("웜", "가을")),
        (None, "봄 웜톤", ("웜", "봄")),
        ("cool", "vivid", ("쿨", "겨울")),
        ("bluebase", "", ("쿨", "여름")),
        ("Warm", "Autumn", ("웜", "가을")),
        ("쿨톤", "여름", ("쿨", "여름")),
    ],
)
def test_normalize_personal_color_variants(primary, sub, expected):
    res = normalize_personal_color(primary, sub)
    assert isinstance(res, tuple) and len(res) == 2
    assert res == expected


def test_normalize_handles_unusual_inputs():
    # numeric, empty, and unexpected strings should not crash
    assert normalize_personal_color(123, 456) in [("웜", "봄"), ("쿨", "여름")]
    assert normalize_personal_color("", "") in [("웜", "봄"), ("쿨", "여름")]
