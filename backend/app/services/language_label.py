"""Language label for a saved entry: pinned > service-reported > script-derived > unknown."""

import unicodedata

# (first, last) code point -> language label used for the script fallback (data-model.md).
_SCRIPT_RANGES: tuple[tuple[int, int, str], ...] = (
    (0x0900, 0x097F, "hi"),  # Devanagari (Marathi shares it; see research R6)
    (0x0980, 0x09FF, "bn"),
    (0x0A80, 0x0AFF, "gu"),
    (0x0B80, 0x0BFF, "ta"),
    (0x0C00, 0x0C7F, "te"),
    (0x0C80, 0x0CFF, "kn"),
    (0x0D00, 0x0D7F, "ml"),
)
MIN_LETTERS = 2


def _script_of(ch: str) -> str | None:
    if not ch.isalpha():
        return None
    code = ord(ch)
    for first, last, label in _SCRIPT_RANGES:
        if first <= code <= last:
            return label
    if unicodedata.name(ch, "").startswith("LATIN"):
        return "en"
    return None


def scripts_in(text: str) -> list[str]:
    counts: dict[str, int] = {}
    order: list[str] = []
    for ch in text:
        label = _script_of(ch)
        if label is None:
            continue
        if label not in counts:
            counts[label] = 0
            order.append(label)
        counts[label] += 1
    return [label for label in order if counts[label] >= MIN_LETTERS]


def derive_languages(text: str, pinned: str | None, reported: list[str] | None) -> list[str]:
    if pinned and pinned != "auto":
        return [pinned]
    if reported:
        return list(reported)
    return scripts_in(text) or ["unknown"]
