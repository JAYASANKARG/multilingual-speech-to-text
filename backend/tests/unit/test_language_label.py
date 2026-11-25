import pytest

from app.services.language_label import derive_languages


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("कल meeting है at 10 AM", ["hi", "en"]),
        ("meeting at ten", ["en"]),
        ("नमस्ते दोस्तों", ["hi"]),
        ("hello नमस्ते", ["en", "hi"]),  # order by first appearance
        ("வணக்கம் hello", ["ta", "en"]),
        ("నమస్కారం", ["te"]),
        ("ನಮಸ್ಕಾರ", ["kn"]),
        ("നമസ്കാരം", ["ml"]),
        ("નમસ્તે", ["gu"]),
        ("নমস্কার", ["bn"]),
    ],
)
def test_script_fallback(text: str, expected: list[str]) -> None:
    assert derive_languages(text, pinned=None, reported=None) == expected


def test_script_needs_at_least_two_letters() -> None:
    assert derive_languages("हिंदी word क", pinned=None, reported=None) == ["hi", "en"]
    assert derive_languages("hello क", pinned=None, reported=None) == ["en"]


def test_digits_and_punctuation_ignored() -> None:
    assert derive_languages("123 ... !!!", pinned=None, reported=None) == ["unknown"]
    assert derive_languages("   ", pinned=None, reported=None) == ["unknown"]


def test_pinned_language_wins() -> None:
    assert derive_languages("नमस्ते दोस्तों", pinned="mr", reported=["hi"]) == ["mr"]


def test_service_reported_beats_script() -> None:
    assert derive_languages("नमस्ते दोस्तों", pinned=None, reported=["mr"]) == ["mr"]


def test_auto_is_not_a_pin() -> None:
    assert derive_languages("hello", pinned="auto", reported=None) == ["en"]
