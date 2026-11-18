import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "privacy_scan.py"
SPEC = importlib.util.spec_from_file_location("privacy_scan", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PhoneDateTests(unittest.TestCase):
    def test_json_title_cohort_years_do_not_mask_adjacent_phone(self):
        title='"title": "Postdoctoral positions '+' - '.join(('2026','2027'))+'"'
        self.assertIsNone(MODULE.PATTERNS['phone-like'].search(MODULE.phone_scan_text(title)))
        self.assertIsNotNone(MODULE.PATTERNS['phone-like'].search(MODULE.phone_scan_text(title+' +'+'1 202 '+'555 0123')))
    def test_public_job_id_is_not_phone_but_adjacent_phone_is_retained(self):
        url = 'https://jobs.csiro.au/job/example/' + ''.join(('12345', '67890')) + '/'
        self.assertIsNone(MODULE.PATTERNS['phone-like'].search(MODULE.phone_scan_text(url)))
        phone = '+' + '1 ' + '202 ' + '555 ' + '0123'
        self.assertIsNotNone(MODULE.PATTERNS['phone-like'].search(MODULE.phone_scan_text(url + ' ' + phone)))

    def test_unknown_host_and_url_query_phone_remain_visible(self):
        phone = ''.join(('12345', '67890'))
        for url in ('https://unknown.example/' + phone, 'https://jobs.csiro.au/job/example/1/?phone=' + phone):
            self.assertIsNotNone(MODULE.PATTERNS['phone-like'].search(MODULE.phone_scan_text(url)))

    def test_svg_geometry_is_not_phone(self):
        self.assertIsNone(MODULE.PATTERNS['phone-like'].search(MODULE.phone_scan_text('<svg viewBox="0 0 24 24">')))

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
