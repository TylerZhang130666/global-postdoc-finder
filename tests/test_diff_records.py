import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "diff_records.py"
SPEC = importlib.util.spec_from_file_location("diff_records", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
AS_OF = "2026-11-18"


def record(row="old", notice="soil-2026"):
    return {"record_id": row, "opportunity_type": "advertised_job",
            "title": "Synthetic soil postdoc", "institution": "Example University",
            "source_url": f"https://university.example/jobs/{notice}",
            "evidence_status": "verified", "date_checked": "2026-11-17",
            "application_access": "open"}


def compare(previous, current):
    return MODULE.compare_records(previous, current, AS_OF)


class DiffTests(unittest.TestCase):
    def test_row_label_change_is_repeat_not_new_and_inputs_are_preserved(self):
        before = record(); after = record("new")
        after["date_checked"] = AS_OF
        original = copy.deepcopy([before, after])
        result = compare([before], [after])
        self.assertEqual(result["summary"]["unchanged"], 1)
        self.assertEqual(result["summary"]["new"], 0)
        self.assertEqual(result["changes"][0]["previous"], [before])
        self.assertEqual(result["changes"][0]["current"], [after])
        self.assertEqual([before, after], original)

    def test_reused_row_label_does_not_merge_different_notices(self):
        result = compare([record("same", "one")], [record("same", "two")])
        self.assertEqual((result["summary"]["new"], result["summary"]["missing_unverified"]), (1, 1))

    def test_missing_notice_is_not_closed(self):
        result = compare([record()], [])
        self.assertEqual(result["summary"]["missing_unverified"], 1)
        self.assertEqual(result["summary"]["closed"], 0)
        self.assertIsNone(result["changes"][0]["closure_basis"])

    def test_deadline_change_and_old_decision_are_retained_separately(self):
        before = record(); before.update(deadline_date="2026-12-01", action_priority="B")
        after = copy.deepcopy(before); after.update(deadline_date="2026-12-15", action_priority="A")
        event = compare([before], [after])["changes"][0]
        self.assertEqual(event["status"], "conditions_changed")
        self.assertEqual(event["changed_fields"]["deadline_date"],
                         {"previous": "2026-12-01", "current": "2026-12-15"})
        self.assertEqual(event["decision_changes"]["action_priority"], {"previous": "B", "current": "A"})

    def test_score_or_eligibility_revision_does_not_invent_condition_change(self):
        before = record(); before.update(scores=[3]*6, eligibility_checks=[{"criterion": "language", "result": "unknown"}])
        after = copy.deepcopy(before); after.update(scores=[4]*6, eligibility_checks=[{"criterion": "language", "result": "pass"}])
        event = compare([before], [after])["changes"][0]
        self.assertEqual(event["status"], "unchanged")
        self.assertFalse(event["changed_fields"])
        self.assertEqual(set(event["decision_changes"]), {"scores", "eligibility_checks"})

    def test_tracking_and_fragments_do_not_duplicate_but_job_query_is_retained(self):
        before = record(); before["source_url"] = "https://university.example/notice?id=123&utm_source=social#details"
        after = record("new"); after["source_url"] = "https://university.example/notice?id=123"
        self.assertEqual(compare([before], [after])["summary"]["unchanged"], 1)
        after["source_url"] = "https://university.example/notice?id=456"
        self.assertEqual(compare([before], [after])["summary"]["new"], 1)

    def test_invitation_and_deadline_verification_are_not_employer_condition_changes(self):
        before = record(); before.update(opportunity_type="fellowship", invitation_confirmed=False,
                                         deadline_date="2026-12-15", deadline_verified=False)
        after = copy.deepcopy(before); after.update(invitation_confirmed=True, deadline_verified=True)
        event = compare([before], [after])["changes"][0]
        self.assertEqual(event["status"], "unchanged")
        self.assertEqual(event["changed_fields"], {})
        self.assertEqual(event["decision_changes"]["invitation_confirmed"], {"previous": False, "current": True})
        self.assertEqual(event["evidence_changes"]["deadline_verified"], {"previous": False, "current": True})

    def test_listing_url_and_row_id_are_insufficient_identity(self):
        for url in ("https://university.example/", "https://university.example/jobs/"):
            before = record(); before["source_url"] = url
            event = compare([before], [copy.deepcopy(before)])["changes"][0]
            self.assertEqual(event["status"], "identity_review")
        before = record(); before["source_url_is_notice"] = False
        self.assertEqual(compare([before], [before])["summary"]["identity_review"], 2)

    def test_hash_based_job_routes_are_not_stripped(self):
        before = record(); before["source_url"] = "https://university.example/portal#/jobs/123"
        after = record(); after["source_url"] = "https://university.example/portal#/jobs/456"
        result = compare([before], [after])
        self.assertEqual((result["summary"]["new"], result["summary"]["missing_unverified"]), (1, 1))

    def test_different_titles_on_shared_url_require_review(self):
        before = record(); after = copy.deepcopy(before); after["title"] = "Different synthetic vacancy"
        event = compare([before], [after])["changes"][0]
        self.assertEqual(event["status"], "identity_review")
        self.assertIn("conflicting title", event["reason"])

    def test_canonical_identity_survives_url_change_and_title_correction(self):
        before = record(); before.update(employer_id="example-u", canonical_notice_id="R123")
        after = copy.deepcopy(before)
        after.update(source_url="https://jobs.university.example/details/R123", title="Corrected synthetic title")
        event = compare([before], [after])["changes"][0]
        self.assertEqual((event["status"], event["match_basis"]), ("conditions_changed", "canonical_notice_id"))

    def test_conflicting_notice_ids_on_one_url_are_not_silently_merged(self):
        before = record(); before.update(employer_id="example-u", canonical_notice_id="R123")
        after = copy.deepcopy(before); after["canonical_notice_id"] = "R456"
        event = compare([before], [after])["changes"][0]
        self.assertEqual(event["status"], "identity_review")
        self.assertIn("Different canonical notice IDs", event["reason"])

    def test_types_are_kept_separate_even_with_identical_url(self):
        before = record(); after = copy.deepcopy(before); after["opportunity_type"] = "fellowship"
        report = compare([before], [after])
        self.assertEqual((report["summary"]["new"], report["summary"]["missing_unverified"]), (1, 1))

    def test_duplicate_batch_is_reported_and_conflicting_duplicate_requires_review(self):
        one = record(); two = record("copy")
        report = compare([], [one, two])
        self.assertEqual(report["summary"]["new"], 1)
        self.assertEqual(report["summary"]["duplicate_groups"], 1)
        self.assertFalse(report["duplicates"][0]["conflicting"])
        two["deadline_date"] = "2026-12-15"
        report = compare([], [one, two])
        self.assertEqual(report["summary"]["identity_review"], 1)
        self.assertTrue(report["duplicates"][0]["conflicting"])

    def test_explicit_closure_needs_dated_verified_evidence(self):
        before = record(); after = copy.deepcopy(before); after["application_access"] = "closed"
        event = compare([before], [after])["changes"][0]
        self.assertEqual(event["status"], "closed")
        self.assertEqual(event["closure_basis"]["basis"], "official_closure_recorded")
        for field, value in (("evidence_status", "secondary_only"), ("date_checked", None), ("source_url", None)):
            item = copy.deepcopy(after); item[field] = value
            report = compare([], [item])
            if field == "source_url":
                # No URL or canonical ID means identity must be resolved first.
                self.assertEqual(report["summary"]["identity_review"], 1)
            else:
                self.assertEqual(report["summary"]["closure_claim_unverified"], 1)

    def test_elapsed_deadline_is_labeled_as_deduction_from_recorded_evidence(self):
        before = record(); before.update(date_checked="2026-11-10", deadline_date="2026-11-15", deadline_verified=True)
        after = copy.deepcopy(before); after["date_checked"] = AS_OF
        event = compare([before], [after])["changes"][0]
        self.assertEqual(event["status"], "closed")
        self.assertEqual(event["closure_basis"]["basis"], "elapsed_verified_deadline")
        self.assertIn("not a new website visit", event["closure_basis"]["note"])
        after["deadline_verified"] = False
        self.assertNotEqual(compare([before], [after])["changes"][0]["status"], "closed")

    def test_stale_current_snapshot_is_not_allowed_to_replace_later_evidence(self):
        before = record(); before["date_checked"] = AS_OF
        after = copy.deepcopy(before); after.update(date_checked="2026-11-16", application_access="closed")
        event = compare([before], [after])["changes"][0]
        self.assertEqual(event["status"], "identity_review")
        self.assertIn("Stale current snapshot", event["reason"])

    def test_invalid_future_dates_and_partial_canonical_id_are_rejected(self):
        for field, value in (("date_checked", "2026-11-19"), ("as_of", "2026-11-19"),
                             ("deadline_date", "-".join(("2026", "02", "30"))), ("employer_id", "example-u")):
            item = record(); item[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                compare([], [item])

    def test_unverified_without_date_can_still_be_compared(self):
        before = record(); before.pop("date_checked"); before["evidence_status"] = "secondary_only"
        self.assertEqual(compare([before], [before])["summary"]["unchanged"], 1)

    def test_cli_refuses_overwriting_either_input(self):
        with tempfile.TemporaryDirectory() as folder:
            old, new = Path(folder) / "old.json", Path(folder) / "new.json"
            old.write_text(json.dumps([record()]), encoding="utf-8")
            new.write_text(json.dumps([record()]), encoding="utf-8")
            for output in (old, new):
                result = subprocess.run([sys.executable, str(SCRIPT), str(old), str(new),
                                         "--as-of", AS_OF, "--out", str(output)], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Output must differ", result.stderr)
            self.assertEqual(json.loads(old.read_text(encoding="utf-8")), [record()])

    def test_saved_anonymous_records_repeat_without_becoming_new(self):
        rows = json.loads((ROOT / "examples/anonymous-trial-2026-11-18/normalized-records.json").read_text(encoding="utf-8"))
        report = compare(rows, copy.deepcopy(rows))
        self.assertEqual(report["summary"]["new"], 0)
        self.assertEqual(report["summary"]["missing_unverified"], 0)
        self.assertEqual(report["summary"]["previous_records"], 18)

    def test_synthetic_example_replays_exactly(self):
        folder = ROOT / "examples/list-refresh-demo"
        previous = json.loads((folder / "previous.json").read_text(encoding="utf-8"))
        current = json.loads((folder / "current.json").read_text(encoding="utf-8"))
        expected = json.loads((folder / "expected-diff.json").read_text(encoding="utf-8"))
        self.assertTrue(all(row["dataset_kind"] == "synthetic" for row in previous + current))
        self.assertEqual(compare(previous, current), expected)


if __name__ == "__main__":
    unittest.main()
