"""Structured logging with redaction (constitution: no transcript text, no secrets in logs)."""

import logging
import re

_KEY_PARAM = re.compile(r"(key=)[^&\s'\"]+")
_FORBIDDEN_EXTRAS = ("text", "transcript", "unsaved_text", "audio")


class RedactionFilter(logging.Filter):
    def __init__(self, secrets: list[str] | None = None) -> None:
        super().__init__()
        self._secrets = [s for s in (secrets or []) if s]

    def _scrub(self, value: str) -> str:
        value = _KEY_PARAM.sub(r"\1***", value)
        for secret in self._secrets:
            value = value.replace(secret, "***")
        return value

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self._scrub(record.getMessage())
        record.args = None
        for name in _FORBIDDEN_EXTRAS:
            if name in record.__dict__:
                del record.__dict__[name]
        return True


def configure_logging(secrets: list[str] | None = None) -> None:
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format='{"t":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}',
        )
    redaction = RedactionFilter(secrets)
    for handler in root.handlers:
        if not any(isinstance(f, RedactionFilter) for f in handler.filters):
            handler.addFilter(redaction)
