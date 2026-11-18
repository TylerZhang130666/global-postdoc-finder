import copy
import importlib.util
import json
import math
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "evaluate_records.py"
SPEC = importlib.util.spec_from_file_location("evaluate_records", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
AS_OF = "2026-11-18"


def record():
    return {"record_id": "sample", "opportunity_type": "advertised_job",
            "evidence_status": "verified", "source_url": "https://example.org/vacancy",
            "date_checked": AS_OF, "application_access": "open", "scores": [4, 4, 4, 4, 4, 4],
            "eligibility_checks": [{"criterion": name, "result": "pass", "evidence": "Supported example evidence"}
                                   for name in MODULE.BASE_CHECKS]}


class EvaluationTests(unittest.TestCase):
    def test_weighted_score_and_ready_priority(self):
        result = MODULE.evaluate_record(record(), AS_OF)
        self.assertEqual((result["weighted_score_100"], result["match_band"], result["action_priority"]), (80, "A", "A"))

    def test_band_boundaries_are_unambiguous(self):
        for score, expected in [(2.749, "C"), (2.75, "B"), (3.74999, "B"), (3.75, "A")]:
            item = record(); item["scores"] = [score] * 6
            self.assertEqual(MODULE.evaluate_record(item, AS_OF)["match_band"], expected)

    def test_absent_language_is_unknown_not_failure(self):
        item = record(); item["eligibility_checks"] = [c for c in item["eligibility_checks"] if c["criterion"] != "language"]
        result = MODULE.evaluate_record(item, AS_OF)
        self.assertEqual((result["eligibility_status"], result["action_priority"], result["confirmed_blocker"]), ("unknown", "B", False))

    def test_confirmed_degree_failure_precedes_score(self):
        item = record(); item["scores"] = [5] * 6; item["eligibility_checks"][0]["result"] = "fail"
        result = MODULE.evaluate_record(item, AS_OF)
        self.assertEqual(result["action_priority"], "Excluded")
        self.assertIsNone(result["weighted_score_100"])

    def test_verified_expired_vacancy_is_excluded(self):
        item = record(); item.update(deadline_date="2026-11-17", deadline_verified=True)
        self.assertEqual(MODULE.evaluate_record(item, AS_OF)["action_priority"], "Excluded")

    def test_verified_closed_access_job_is_excluded_before_scoring(self):
        for closure_flag in (None, False):
            with self.subTest(availability_closed=closure_flag):
                item = record(); item.update(application_access="closed", scores=[5] * 6)
                if closure_flag is not None:
                    item["availability_closed"] = closure_flag
                result = MODULE.evaluate_record(item, AS_OF)
                self.assertEqual(result["action_priority"], "Excluded")
                self.assertTrue(result["confirmed_blocker"])
                self.assertIsNone(result["weighted_score_100"])
                self.assertIsNone(result["match_band"])

    def test_unverified_closed_access_is_not_confirmed_exclusion(self):
        item = record(); item.update(application_access="closed", evidence_status="secondary_only")
        result = MODULE.evaluate_record(item, AS_OF)
        self.assertEqual(result["action_priority"], "C")
        self.assertFalse(result["confirmed_blocker"])

    def test_unverified_aggregator_deadline_does_not_exclude(self):
        item = record(); item.update(evidence_status="secondary_only", deadline_date="2026-11-17", deadline_verified=False)
        result = MODULE.evaluate_record(item, AS_OF)
        self.assertEqual((result["action_priority"], result["confirmed_blocker"]), ("C", False))

    def test_unsupported_failure_is_rejected(self):
        item = record(); item["evidence_status"] = "indexed_only"; item["eligibility_checks"][0]["result"] = "fail"
        with self.assertRaises(ValueError): MODULE.evaluate_record(item, AS_OF)

    def test_invitation_stage_requires_confirmation(self):
        item = record(); item.update(opportunity_type="fellowship", application_access="invitation_only")
        for invitation in (None, False, True):
            item["invitation_confirmed"] = invitation
            self.assertEqual(MODULE.evaluate_record(item, AS_OF)["action_priority"], "A" if invitation is True else "C")

    def test_scheduled_round_is_preparation_not_ready(self):
        item = record(); item.update(opportunity_type="fellowship", application_access="scheduled")
        self.assertEqual(MODULE.evaluate_record(item, AS_OF)["action_priority"], "B")

    def test_closed_round_does_not_imply_permanent_ineligibility(self):
        item = record(); item.update(opportunity_type="fellowship", application_access="closed")
        result = MODULE.evaluate_record(item, AS_OF)
        self.assertEqual((result["action_priority"], result["eligibility_status"], result["confirmed_blocker"]), ("C", "eligible", False))

    def test_missing_scores_stay_unavailable(self):
        item = record(); item["scores"] = None
        result = MODULE.evaluate_record(item, AS_OF)
        self.assertIsNone(result["weighted_score_100"])
        self.assertIsNone(result["match_band"])

    def test_invalid_scores_and_boolean_flags_are_rejected(self):
        for scores in ([True] * 6, [math.nan] * 6, [math.inf] * 6, [6] * 6, [1] * 5):
            item = record(); item["scores"] = scores
            with self.assertRaises(ValueError): MODULE.evaluate_record(item, AS_OF)
        item = record(); item["deadline_verified"] = "false"
        with self.assertRaises(ValueError): MODULE.evaluate_record(item, AS_OF)

    def test_potential_host_does_not_become_vacancy(self):
        item = record(); item.update(opportunity_type="potential_host", application_access="not_applicable", scores=None)
        result = MODULE.evaluate_record(item, AS_OF)
        self.assertEqual(result["action_priority"], "Host only")
        self.assertIsNone(result["weighted_score_100"])

    def test_same_day_cutoff_needs_time_check(self):
        item = record(); item.update(deadline_date=AS_OF, deadline_verified=True)
        self.assertEqual(MODULE.evaluate_record(item, AS_OF)["action_priority"], "B")

    def test_verified_source_and_deadline_require_provenance(self):
        item = record(); del item["source_url"]
        with self.assertRaises(ValueError): MODULE.evaluate_record(item, AS_OF)
        item = record(); del item["date_checked"]
        with self.assertRaises(ValueError): MODULE.evaluate_record(item, AS_OF)
        item = record(); item.update(evidence_status="secondary_only", deadline_date="2026-12-01", deadline_verified=True)
        with self.assertRaises(ValueError): MODULE.evaluate_record(item, AS_OF)

    def test_duplicate_ids_and_criteria_rejected(self):
        with self.assertRaises(ValueError): MODULE.evaluate_records([record(), record()], AS_OF)
        item = record(); item["eligibility_checks"].append(copy.deepcopy(item["eligibility_checks"][0]))
        with self.assertRaises(ValueError): MODULE.evaluate_record(item, AS_OF)

    def test_no_mutation_and_extra_required_check_unknown(self):
        item = record(); item["required_checks"] = ["residence"]
        original = copy.deepcopy(item)
        result = MODULE.evaluate_record(item, AS_OF)
        self.assertEqual(item, original)
        self.assertEqual(result["action_priority"], "B")
        self.assertTrue(any(c["criterion"] == "residence" and c["result"] == "unknown" for c in result["eligibility_checks"]))

    def test_saved_trial_replays_with_current_rules(self):
        folder = SCRIPT.parents[1] / "examples" / "anonymous-trial-2026-11-18"
        inputs = json.loads((folder / "normalized-records.json").read_text(encoding="utf-8"))
        expected = json.loads((folder / "replayed-results.json").read_text(encoding="utf-8"))
        self.assertEqual(MODULE.evaluate_records(inputs, AS_OF), expected)


if __name__ == "__main__":
    unittest.main()
