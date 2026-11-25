from app.stt.languages import LANGUAGES, gemini_language_codes, get_language, pinnable_codes

EXPECTED = {
    "hi": "hi-IN", "en": "en-IN", "bn": "bn-IN", "mr": "mr-IN",
    "gu": "gu-IN", "kn": "kn-IN", "ml": "ml-IN", "te": "te-IN", "ta": "ta-IN",
}  # fmt: skip


def test_registry_has_auto_plus_nine_languages() -> None:
    codes = {lang.code for lang in LANGUAGES}
    assert codes == {"auto", *EXPECTED}
    assert len(LANGUAGES) == 10


def test_tamil_is_pinnable_with_ta_in() -> None:
    ta = get_language("ta")
    assert ta is not None
    assert ta.pinnable is True
    assert gemini_language_codes("ta") == ["ta-IN"]
    assert "ta" in pinnable_codes()


def test_gemini_codes() -> None:
    for code, bcp47 in EXPECTED.items():
        assert gemini_language_codes(code) == [bcp47]
    assert gemini_language_codes("auto") == []


def test_unknown_language() -> None:
    assert get_language("xx") is None
    assert "auto" in pinnable_codes()
