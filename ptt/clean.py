"""Shared post-content cleaning utilities for PTT scrapers."""

import re

_CUT = re.compile(
    r"\n※\s*(?:[a-zA-Z]\.|八卦板務|編輯|發信站)"
    r"|\n--\s*(?:\n|$)",
    re.DOTALL,
)
_NOISE      = re.compile(r"(?:※|◆)[^\n]*\n?")
_SEPARATORS = re.compile(r"[-─═=]{3,}")
_URLS       = re.compile(r"https?://\S+")
_SENT_FROM  = re.compile(r"Sent from \S[^\n]*\n?", re.IGNORECASE)
_BLANKS     = re.compile(r"\n{3,}")


def clean_content(text: str) -> str:
    """Clean PTT post body: cut signatures, remove noise/separators/URLs/app banners."""
    m = _CUT.search(text)
    body = text[: m.start()] if m else text
    body = _NOISE.sub("", body)
    body = _SEPARATORS.sub("", body)
    body = _URLS.sub("", body)
    body = _SENT_FROM.sub("", body)
    body = _BLANKS.sub("\n\n", body)
    return body.strip()
