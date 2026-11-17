#!/usr/bin/env python3
"""Evaluate interpreted evidence; no browsing, CV parsing or source verification."""
import argparse
import json
import math
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

RULE_VERSION = "2026-11-18"
WEIGHTS = (30, 25, 20, 10, 10, 5)
BASE_CHECKS = ("degree_timing", "start_date", "language", "user_constraints")
TYPES = {"advertised_job", "fellowship", "potential_host"}
EVIDENCE = {"verified", "indexed_only", "secondary_only", "conflicting", "inaccessible", "unconfirmed"}
ACCESS = {"open", "scheduled", "invitation_only", "closed", "unconfirmed", "not_applicable"}
CHECK_RESULTS = {"pass", "fail", "unknown", "not_applicable"}


def iso_date(value):
    if not isinstance(value, str):
        raise ValueError("Date must be an ISO calendar-date string")
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("Use YYYY-MM-DD; keep exact cutoff wording separately")
    return parsed


def nonempty(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")
    return value


def evaluate_record(record, as_of):
    if not isinstance(record, dict):
        raise ValueError("Each record must be an object")
    as_of = iso_date(as_of) if isinstance(as_of, str) else as_of
    if not isinstance(as_of, date):
        raise ValueError("as_of must be a calendar date")
    record_id = nonempty(record.get("record_id"), "record_id")
    kind = record.get("opportunity_type")
    evidence = record.get("evidence_status")
    access = record.get("application_access")
    if kind not in TYPES or evidence not in EVIDENCE or access not in ACCESS:
        raise ValueError(f"{record_id}: invalid opportunity_type, evidence_status or application_access")
    if kind != "potential_host" and access == "not_applicable":
        raise ValueError(f"{record_id}: application access cannot be not_applicable for a job or fellowship")
    for key in ("deadline_verified", "availability_closed"):
        if key in record and not isinstance(record[key], bool):
            raise ValueError(f"{record_id}: {key} must be boolean")
    invitation = record.get("invitation_confirmed")
    if invitation is not None and not isinstance(invitation, bool):
        raise ValueError(f"{record_id}: invitation_confirmed must be boolean or null")
    if evidence == "verified":
        source = urlparse(nonempty(record.get("source_url"), "source_url"))
        if source.scheme not in {"https", "http"} or not source.netloc:
            raise ValueError(f"{record_id}: verified evidence needs an HTTP(S) source_url")
        iso_date(nonempty(record.get("date_checked"), "date_checked"))
    checked = record.get("date_checked")
    if checked and iso_date(checked) > as_of:
        raise ValueError(f"{record_id}: date_checked cannot be after the snapshot")
    deadline = iso_date(record["deadline_date"]) if record.get("deadline_date") else None
    if record.get("deadline_verified") and (deadline is None or evidence != "verified"):
        raise ValueError(f"{record_id}: verified deadline needs a date and verified source evidence")
    if record.get("availability_closed") and evidence != "verified":
        raise ValueError(f"{record_id}: a confirmed closure needs verified source evidence")
    scores = record.get("scores")
    if scores is not None:
        if (not isinstance(scores, list) or len(scores) != 6 or
                any(isinstance(x, bool) or not isinstance(x, (int, float)) or
                    not math.isfinite(x) or not 0 <= x <= 5 for x in scores)):
            raise ValueError(f"{record_id}: scores must be six finite numbers from 0 to 5, or null")
    checks = record.get("eligibility_checks", [])
    if not isinstance(checks, list):
        raise ValueError(f"{record_id}: eligibility_checks must be a list")
    normalized, seen = [], set()
    for check in checks:
        if not isinstance(check, dict):
            raise ValueError(f"{record_id}: each eligibility check must be an object")
        criterion = nonempty(check.get("criterion"), "criterion")
        if criterion in seen or check.get("result") not in CHECK_RESULTS:
            raise ValueError(f"{record_id}: duplicate criterion or invalid check result")
        nonempty(check.get("evidence"), "check evidence")
        if check["result"] == "fail" and evidence != "verified":
            raise ValueError(f"{record_id}: unsupported failure must be unknown until verified")
        seen.add(criterion)
        normalized.append(dict(check))
    required = record.get("required_checks", [])
    if not isinstance(required, list) or any(not isinstance(x, str) or not x.strip() for x in required):
        raise ValueError(f"{record_id}: required_checks must contain criterion names")
    output = dict(record, rule_version=RULE_VERSION, as_of=as_of.isoformat(),
                  weighted_score_100=None, match_band=None, action_priority=None,
                  eligibility_status="unknown", confirmed_blocker=False, action_reasons=[])
    if kind == "potential_host":
        output.update(action_priority="Host only", eligibility_status="not_assessed",
                      action_reasons=["Research target only; no verified vacancy is implied"])
        return output
    for criterion in dict.fromkeys((*BASE_CHECKS, *required)):
        if criterion not in seen:
            normalized.append({"criterion": criterion, "result": "unknown",
                               "evidence": "Required check absent from normalized input"})
    output["eligibility_checks"] = normalized
    failures = [c for c in normalized if c["result"] == "fail"]
    unknowns = [c for c in normalized if c["result"] == "unknown"]
    output["eligibility_status"] = "ineligible" if failures else "unknown" if unknowns else "eligible"
    expired = bool(deadline and record.get("deadline_verified") and deadline < as_of)
    vacancy_closed = kind == "advertised_job" and (expired or record.get("availability_closed", False))
    if failures or vacancy_closed:
        reasons = ["Confirmed failure: " + c["criterion"] for c in failures]
        if vacancy_closed:
            reasons.append("Verified vacancy expired or employer confirmed closure")
        output.update(action_priority="Excluded", confirmed_blocker=True, action_reasons=reasons)
        return output
    total = math.fsum(x * w for x, w in zip(scores, WEIGHTS)) / 5 if scores is not None else None
    band = None if total is None else "A" if total >= 75 else "B" if total >= 55 else "C"
    output.update(weighted_score_100=total, match_band=band)
    reasons = []
    cap = "A"
    if evidence != "verified":
        cap = "C"
        reasons.append("Availability evidence is " + evidence)
    if access in {"closed", "unconfirmed"} or expired:
        cap = "C"
        reasons.append("Current entry is closed, expired or unconfirmed")
    if access == "invitation_only" and invitation is not True:
        cap = "C"
        reasons.append("Required invitation is not confirmed")
    if access == "scheduled":
        if cap == "A":
            cap = "B"
        reasons.append("Future round; prepare rather than submit now")
    if unknowns:
        if cap == "A":
            cap = "B"
        reasons.append("Verify mandatory checks: " + ", ".join(c["criterion"] for c in unknowns))
    if deadline == as_of and record.get("deadline_verified"):
        if cap == "A":
            cap = "B"
        reasons.append("Same-day cutoff needs a separate time and timezone check")
    if total is None:
        priority = "C"
        reasons.append("Incomplete scores; no total or match band computed")
    else:
        priority = max((band, cap), key=lambda x: {"A": 0, "B": 1, "C": 2}[x])
    output.update(action_priority=priority, action_reasons=reasons or ["Verified accessible entry and all mandatory checks resolved"])
    return output


def evaluate_records(records, as_of):
    if not isinstance(records, list):
        raise ValueError("Input must be a JSON list")
    result, ids = [], set()
    for record in records:
        item = evaluate_record(record, as_of)
        if item["record_id"] in ids:
            raise ValueError("Duplicate record_id: " + item["record_id"])
        ids.add(item["record_id"])
        result.append(item)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--as-of", required=True, help="YYYY-MM-DD snapshot date; not a live refresh")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.input.resolve() == args.out.resolve():
        parser.error("Output must differ from the input snapshot")
    try:
        records = evaluate_records(json.loads(args.input.read_text(encoding="utf-8")), args.as_of)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    counts = {p: sum(r["action_priority"] == p for r in records) for p in ("A", "B", "C", "Excluded", "Host only")}
    print(json.dumps({"rule_version": RULE_VERSION, "records": len(records), "action_counts": counts}))


if __name__ == "__main__":
    main()
