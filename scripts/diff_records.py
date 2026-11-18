#!/usr/bin/env python3
"""Compare saved opportunity snapshots; this script does not revisit websites.

Identity is scoped by opportunity_type and uses employer_id+canonical_notice_id,
or a notice-specific source_url. record_id is only a local row label. A shared
listing URL, conflicting identity or conflicting duplicate requires human review.
Use source_url_is_notice=true/false to annotate a known notice/listing URL; this
annotation is an interpretation, not automatic source verification.

Only CONDITION_FIELDS below count as advertised-condition changes. Scores,
eligibility interpretations and action priorities are reported separately. Both
full snapshots are retained, including unlisted fields. A missing row never proves
closure. Verified expired deadlines are date-based deductions, distinct from an
explicit official closure; source dates and closure_basis preserve that distinction.
"""
import argparse
import copy
import json
from datetime import date
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

SCHEMA_VERSION = "2026-11-18.1"
TYPES = {"advertised_job", "fellowship", "potential_host"}
STATUSES = ("new", "unchanged", "conditions_changed", "closed",
            "closure_claim_unverified", "missing_unverified", "identity_review")
CONDITION_FIELDS = (
    "title", "institution", "application_access", "availability_closed",
    "deadline_date", "deadline_time", "deadline_timezone",
    "salary", "salary_min", "salary_max", "salary_currency", "salary_period",
    "contract_length", "start_date", "start_date_flexible", "location",
    "requirements", "mandatory_requirements", "application_url",
)
DECISION_FIELDS = (
    "scores", "weighted_score_100", "match_band", "action_priority",
    "eligibility_checks", "eligibility_status", "confirmed_blocker",
    "action_reasons", "required_checks", "rule_version", "invitation_confirmed",
)
EVIDENCE_FIELDS = ("evidence_status", "source_url", "source_locator", "date_checked", "deadline_verified")
TRACKING_KEYS = {"fbclid", "gclid", "msclkid", "mc_cid", "mc_eid"}
SECTION_ANCHORS = {"details", "apply", "description", "requirements", "overview", "top"}
LISTING_NAMES = {"", "jobs", "job", "careers", "career", "vacancies", "vacancy",
                 "opportunities", "opportunity", "recruitment", "listing", "search",
                 "index", "index.html", "index.htm", "index.php", "en", "en-us"}


def iso_date(value):
    if not isinstance(value, str):
        raise ValueError("Dates must be YYYY-MM-DD strings")
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("Dates must use YYYY-MM-DD")
    return parsed


def normalize_url(value):
    """Remove known tracking data only; retain query IDs, blank values and case."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        url = urlsplit(value.strip())
        if url.scheme not in {"https", "http"} or not url.netloc or url.username or url.password:
            return None
        query = [(key, val) for key, val in parse_qsl(url.query, keep_blank_values=True)
                 if not key.lower().startswith("utm_") and key.lower() not in TRACKING_KEYS]
        # Query order is not changed: some servers assign it meaning.
        # Hash-based application routes may identify different vacancies.
        fragment = "" if url.fragment.lower() in SECTION_ANCHORS else url.fragment
        return urlunsplit((url.scheme.lower(), url.netloc.lower(), url.path or "/",
                           urlencode(query), fragment))
    except ValueError:
        return None


def _notice_url(record):
    url = normalize_url(record.get("source_url"))
    if not url or record.get("source_url_is_notice") is False:
        return None
    if record.get("source_url_is_notice") is True:
        return url
    parsed = urlsplit(url)
    # A URL with only a language/listing tail is deliberately not an identity.
    tail = parsed.path.rstrip("/").rsplit("/", 1)[-1].lower()
    if tail in LISTING_NAMES:
        return None
    return url


def _stable_id(record):
    employer, notice = record.get("employer_id"), record.get("canonical_notice_id")
    return (employer, notice) if employer and notice else None


def _validate(records, as_of, label):
    if not isinstance(records, list):
        raise ValueError(f"{label} must be a JSON list")
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"{label}[{index}] must be an object")
        if not isinstance(record.get("record_id"), str) or not record["record_id"].strip():
            raise ValueError(f"{label}[{index}] needs a record_id")
        if record.get("opportunity_type") not in TYPES:
            raise ValueError(f"{label}[{index}] has an invalid opportunity_type")
        for field in ("employer_id", "canonical_notice_id"):
            if field in record and (not isinstance(record[field], str) or not record[field].strip()):
                raise ValueError(f"{field} must be a nonempty string")
        if bool(record.get("employer_id")) != bool(record.get("canonical_notice_id")):
            raise ValueError("Use employer_id and canonical_notice_id together")
        for field in ("source_url_is_notice", "availability_closed", "deadline_verified"):
            if field in record and not isinstance(record[field], bool):
                raise ValueError(f"{field} must be boolean")
        if record.get("date_checked") and iso_date(record["date_checked"]) > as_of:
            raise ValueError("date_checked cannot be after as_of")
        if record.get("as_of") and iso_date(record["as_of"]) > as_of:
            raise ValueError("Snapshot as_of cannot be after comparison as_of")
        if record.get("deadline_date"):
            iso_date(record["deadline_date"])


def _differences(previous, current, fields):
    return {field: {"previous": copy.deepcopy(previous.get(field)),
                    "current": copy.deepcopy(current.get(field))}
            for field in fields if previous.get(field) != current.get(field)}


def _closure(record, as_of):
    if record.get("opportunity_type") == "potential_host":
        return None
    verified = (record.get("evidence_status") == "verified" and
                normalize_url(record.get("source_url")) is not None and
                bool(record.get("date_checked")))
    if not verified:
        return None
    if record.get("availability_closed") or record.get("application_access") == "closed":
        return {"basis": "official_closure_recorded", "evidence_date": record["date_checked"],
                "source_url": record["source_url"]}
    if (record.get("deadline_verified") and record.get("deadline_date") and
            iso_date(record["deadline_date"]) < as_of):
        return {"basis": "elapsed_verified_deadline", "evidence_date": record["date_checked"],
                "deadline_date": record["deadline_date"], "source_url": record["source_url"],
                "note": "Inferred from a previously verified cutoff, not a new website visit"}
    return None


def _closure_claim(record):
    return (record.get("opportunity_type") != "potential_host" and
            (record.get("availability_closed") or record.get("application_access") == "closed"))


def _duplicate_fingerprint(record):
    item = {key: value for key, value in record.items()
            if key not in {"record_id", "date_checked", "as_of"}}
    if "source_url" in item:
        item["source_url"] = normalize_url(item["source_url"])
    return json.dumps(item, sort_keys=True, ensure_ascii=False)


def _normalized_text(value):
    return " ".join(value.casefold().split()) if isinstance(value, str) else ""


def compare_records(previous, current, as_of):
    """Return a new JSON-serializable report without mutating either input list."""
    as_of = iso_date(as_of) if isinstance(as_of, str) else as_of
    if not isinstance(as_of, date):
        raise ValueError("as_of must be a calendar date")
    _validate(previous, as_of, "previous")
    _validate(current, as_of, "current")
    nodes = [("previous", index, record) for index, record in enumerate(previous)]
    nodes += [("current", index, record) for index, record in enumerate(current)]
    parents = list(range(len(nodes)))
    conflicts = []

    def find(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(left, right):
        parents[find(right)] = find(left)

    for left, (_, _, first) in enumerate(nodes):
        for right in range(left + 1, len(nodes)):
            second = nodes[right][2]
            if first["opportunity_type"] != second["opportunity_type"]:
                continue
            first_id, second_id = _stable_id(first), _stable_id(second)
            same_id = first_id is not None and first_id == second_id
            same_url = _notice_url(first) is not None and _notice_url(first) == _notice_url(second)
            if not (same_id or same_url):
                continue
            union(left, right)
            if same_url and first_id and second_id and first_id != second_id:
                conflicts.append((left, "Different canonical notice IDs share a URL"))
            elif same_url and not same_id:
                for field in ("title", "institution"):
                    a, b = _normalized_text(first.get(field)), _normalized_text(second.get(field))
                    if a and b and a != b:
                        conflicts.append((left, f"URL match has conflicting {field}; check for a shared listing"))

    groups = {}
    for index, node in enumerate(nodes):
        groups.setdefault(find(index), []).append(node)
    changes, duplicates = [], []
    for root, group in groups.items():
        old = [r for batch, _, r in group if batch == "previous"]
        new = [r for batch, _, r in group if batch == "current"]
        reasons = [reason for index, reason in conflicts if find(index) == root]
        identities = {_stable_id(r) for _, _, r in group if _stable_id(r)}
        if len(identities) > 1:
            reasons.append("Ambiguous canonical identity; no records were merged")
        has_identity = any(_stable_id(r) or _notice_url(r) for _, _, r in group)
        if not has_identity:
            reasons.append("No notice-specific identity; row ID alone cannot match snapshots")
        for batch, rows in (("previous", old), ("current", new)):
            if len(rows) > 1:
                contradictory = len({_duplicate_fingerprint(r) for r in rows}) > 1
                duplicates.append({"snapshot": batch, "records": copy.deepcopy(rows),
                                   "conflicting": contradictory})
                if contradictory:
                    reasons.append(f"Conflicting {batch} duplicate records")
        # Prefer the latest evidence only for otherwise equivalent duplicates.
        before = max(old, key=lambda r: r.get("date_checked") or "") if old else {}
        after = max(new, key=lambda r: r.get("date_checked") or "") if new else {}
        if (before.get("date_checked") and after.get("date_checked") and
                after["date_checked"] < before["date_checked"]):
            reasons.append("Stale current snapshot: date_checked precedes previous evidence")
        basis = "canonical_notice_id" if identities else "source_url" if has_identity else None
        event = {"status": None, "match_basis": basis,
                 "previous": copy.deepcopy(old), "current": copy.deepcopy(new),
                 "changed_fields": {}, "decision_changes": {}, "evidence_changes": {},
                 "closure_basis": None, "reason": None}
        if old and new:
            event["changed_fields"] = _differences(before, after, CONDITION_FIELDS)
            event["decision_changes"] = _differences(before, after, DECISION_FIELDS)
            event["evidence_changes"] = _differences(before, after, EVIDENCE_FIELDS)
        if reasons:
            event.update(status="identity_review", reason="; ".join(dict.fromkeys(reasons)))
        elif not new:
            event.update(status="missing_unverified",
                         reason="Absent from current input; recheck the official notice before judging availability")
        else:
            closure = _closure(after, as_of)
            previous_as_of = iso_date(before.get("as_of") or before.get("date_checked") or as_of.isoformat())
            prior_closure = _closure(before, previous_as_of) if before else None
            event["closure_basis"] = closure
            if closure and (not before or not prior_closure):
                event.update(status="closed", reason="Current input records closure; see closure_basis and its evidence date")
            elif _closure_claim(after) and not closure:
                event.update(status="closure_claim_unverified",
                             reason="Closure claim lacks verified dated official evidence; do not treat as confirmed")
            elif not old:
                event.update(status="new", reason="Notice-specific identity was not present in previous input")
            elif event["changed_fields"]:
                event.update(status="conditions_changed",
                             reason="Same notice; explicit condition fields differ. Compare the retained evidence")
            else:
                event.update(status="unchanged",
                             reason="Seen before; no listed advertised-condition field changed. Judgments may differ separately")
        changes.append(event)
    summary = {status: sum(item["status"] == status for item in changes) for status in STATUSES}
    summary.update(previous_records=len(previous), current_records=len(current),
                   duplicate_groups=len(duplicates),
                   matched_groups=sum(bool(item["previous"] and item["current"]) for item in changes))
    return {"schema_version": SCHEMA_VERSION, "as_of": as_of.isoformat(),
            "note": "Offline comparison of supplied snapshots; no source has been revisited",
            "summary": summary, "changes": changes, "duplicates": duplicates}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("previous", type=Path)
    parser.add_argument("current", type=Path)
    parser.add_argument("--as-of", required=True, help="YYYY-MM-DD comparison date; not a live refresh")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.out.resolve() in {args.previous.resolve(), args.current.resolve()}:
        parser.error("Output must differ from both input snapshots")
    try:
        report = compare_records(json.loads(args.previous.read_text(encoding="utf-8")),
                                 json.loads(args.current.read_text(encoding="utf-8")), args.as_of)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(json.dumps(report["summary"]))


if __name__ == "__main__":
    main()
