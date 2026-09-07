"""Conservative text cleanup and lightweight section detection."""

import re


def clean_text(text: str) -> str:
    """Normalize OCR whitespace while preserving paragraph boundaries."""
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    cleaned = []
    previous_blank = False
    for line in lines:
        if not line:
            if not previous_blank and cleaned:
                cleaned.append("")
            previous_blank = True
            continue
        cleaned.append(line)
        previous_blank = False
    return "\n".join(cleaned).strip()


def detect_section(text: str) -> str:
    """Return the last obvious numbered or title-style section heading."""
    for line in clean_text(text).splitlines():
        if re.match(r"^(?:\d+(?:\.\d+)*[.)]?\s+|section\s+)\S+", line, re.IGNORECASE):
            return line
    return ""