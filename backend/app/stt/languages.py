from dataclasses import dataclass


@dataclass(frozen=True)
class LanguageInfo:
    code: str
    name: str
    script: str | None
    gemini_code: str | None
    pinnable: bool


LANGUAGES: tuple[LanguageInfo, ...] = (
    LanguageInfo("auto", "Auto-detect (Hindi + English)", None, None, True),
    LanguageInfo("hi", "Hindi", "Devanagari", "hi-IN", True),
    LanguageInfo("en", "English", "Latin", "en-IN", True),
    LanguageInfo("bn", "Bengali", "Bengali", "bn-IN", True),
    LanguageInfo("mr", "Marathi", "Devanagari", "mr-IN", True),
    LanguageInfo("gu", "Gujarati", "Gujarati", "gu-IN", True),
    LanguageInfo("kn", "Kannada", "Kannada", "kn-IN", True),
    LanguageInfo("ml", "Malayalam", "Malayalam", "ml-IN", True),
    LanguageInfo("te", "Telugu", "Telugu", "te-IN", True),
    # Not in Google's published list, but verified working when pinned (research U6).
    LanguageInfo("ta", "Tamil", "Tamil", "ta-IN", True),
)

_BY_CODE = {lang.code: lang for lang in LANGUAGES}


def get_language(code: str) -> LanguageInfo | None:
    return _BY_CODE.get(code)


def pinnable_codes() -> set[str]:
    return {lang.code for lang in LANGUAGES if lang.pinnable}


def gemini_language_codes(code: str) -> list[str]:
    lang = _BY_CODE.get(code)
    if lang is None or lang.gemini_code is None:
        return []
    return [lang.gemini_code]
