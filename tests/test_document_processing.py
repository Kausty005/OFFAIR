import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from document.cleaner import clean_text, detect_section


def test_cleaner_normalizes_ocr_whitespace():
    assert clean_text("HR POLICY\n\nEmployee    leave   policy\n\n\n26 weeks") == (
        "HR POLICY\n\nEmployee leave policy\n\n26 weeks"
    )


def test_section_detection_preserves_heading():
    assert detect_section("1. Maternity Leave\nEmployees receive 26 weeks") == "1. Maternity Leave"