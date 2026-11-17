import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "privacy_scan.py"
SPEC = importlib.util.spec_from_file_location("privacy_scan", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PhoneDateTests(unittest.TestCase):
    def test_valid_calendar_date_is_not_phone(self):
        self.assertIsNone(MODULE.PATTERNS["phone-like"].search(MODULE.phone_scan_text("Checked 2026-11-18")))

    def test_phone_on_same_line_is_retained(self):
        # Build a synthetic phone so publication scans do not flag test source.
        sample = "Checked 2026-11-18; phone +" + "1 " + "202 " + "555 " + "0123"
        self.assertIsNotNone(MODULE.PATTERNS["phone-like"].search(MODULE.phone_scan_text(sample)))

    def test_invalid_date_and_long_hyphenated_number_not_suppressed(self):
        for sample in ("-".join(("2026", "99", "99")), "-".join(("2026", "11", "18", "9999"))):
            self.assertIsNotNone(MODULE.PATTERNS["phone-like"].search(MODULE.phone_scan_text(sample)))


if __name__ == "__main__":
    unittest.main()
