# Screening, evidence and action priority

Use this reference when screening a vacancy or fellowship or preparing a structured run. These are decision rules, not an automated determination of a person's qualifications.

## Evidence and unknowns

Keep four questions distinct:

1. Does the employer or funder confirm this particular vacancy or round?
2. Does the candidate meet each applicable mandatory requirement?
3. Can this candidate enter the current application stage?
4. How well does the research and method evidence match?

Resolve fields against their owning sources. Record the canonical notice or vacancy ID, check date, short source locator, and conflicts. An employer biography is evidence for a host's research, not for an open funded position. Indexed-only, inaccessible, secondary-only or conflicting sources remain provisional. Do not copy deadlines from aggregators into verified-deadline fields.

Deduplicate by vacancy ID where available; otherwise compare employer, role, location and source URL. Do not merge similar roles at different employers merely because the prose matches. Report a suspected identity conflict until its resolution is supported.

For every explicit requirement, compare source wording with candidate evidence:

| Result | Meaning |
|---|---|
| `pass` | Supported by the available evidence or the candidate's relevant disclosure; identify which. |
| `fail` | A confirmed conflict, such as a fixed degree deadline before the candidate's expected completion. |
| `unknown` | Missing evidence, ambiguous wording, or a potentially negotiable condition. |
| `not_applicable` | This is not a requirement for this record; give a reason. |

An omitted language, nationality or residence history is not a negative answer. For a date described as "available from", check whether later entry is possible before claiming a fixed start-date failure. Ask for a minimal private eligibility answer when needed. Do not publish exact residence dates or birth dates to make an example reproducible.

## Rounds and dates

Record each relevant stage separately: concept note, full proposal, nomination, host-institution submission and fellowship commencement. State which stage the candidate can enter. A passed first-stage deadline and an open invitation-only second stage are not an open call for new candidates. Prior submission or invitation is a private input, not an inference from a CV filename.

Preserve original date wording, timezone, and inclusive/exclusive phrasing. Where a sidebar and body disagree, keep both and explain the interpretation or leave the deadline uncertain. Record a future call as scheduled, and a closed programme round with a reopening notice as closed now. Do not invent a future deadline by extrapolating last year's calendar.

The helper below evaluates calendar dates only. Exact cutoff times need a separate timezone-aware check. On the cutoff date, the helper caps action priority until that time check is resolved; it never guarantees that a same-day application is still possible.

## Numerical match versus action

Scores are analyst judgments from 0 to 5, supported by fit evidence and gaps. Weights are topic 30, methods 25, eligibility 20, timing 10, location/conditions 10 and growth 5. Compute `sum(score * weight) / 5`, out of 100.

The numerical match bands are mutually exclusive: A >= 75; B >= 55 and < 75; C < 55. Missing scores produce no total. Do not rank partial totals as if all dimensions were known.

Apply action gates in this order:

| Condition | Action result |
|---|---|
| Potential host | `Host only`; assess research fit qualitatively, no vacancy score. |
| Confirmed mandatory failure, or a verified expired/closed vacancy | `Excluded`; do not compute a score. |
| Evidence is not verified; access is closed/unconfirmed; or invitation is not confirmed | At most C, regardless of score. |
| A future round, unresolved mandatory check, or unresolved same-day cutoff | At most B. |
| All applicable checks pass and access is open/confirmed invitation | A if score >= 75, B if >= 55, otherwise C. |
| Score incomplete | C for follow-up, with no numerical match band. |

Preserve both `match_band` and `action_priority` plus `action_reasons`. B may mean "verify eligibility" or "prepare for a future round", not "submit today". A closed fellowship round is a current access issue; it does not establish permanent candidate ineligibility. A verified closed advertised vacancy is excluded for this snapshot. State whether confidence concerns the source, the candidate evidence, or both.

## Structured helper

`scripts/evaluate_records.py` uses only the Python standard library. Supply a JSON list of normalized records and an explicit snapshot date:

```text
python scripts/evaluate_records.py examples/anonymous-trial-2026-11-18/normalized-records.json --as-of 2026-11-18 --out /tmp/postdoc-replay.json
python -m unittest discover -s tests -v
```

The first command is an offline rule replay of a saved snapshot. It does not refresh websites.

Required fields per record:

| Field | Values or meaning |
|---|---|
| `record_id` | Unique nonempty identifier. |
| `opportunity_type` | `advertised_job`, `fellowship`, `potential_host`. |
| `evidence_status` | `verified`, `indexed_only`, `secondary_only`, `conflicting`, `inaccessible`, `unconfirmed`. |
| `application_access` | `open`, `scheduled`, `invitation_only`, `closed`, `unconfirmed`, `not_applicable`. |
| `eligibility_checks` | Objects with unique `criterion`, `result`, nonempty `evidence`. |
| `scores` | Six numbers in the weight order above, or null. Boolean, nonfinite and out-of-range inputs are invalid. |

Additional fields:

- `required_checks`: defaults to `degree_timing`, `start_date`, `language`, `user_constraints`. Missing checks are treated as unknown. Extend this list for every explicit conditional rule, such as nationality, residence or host approval. Do not silently remove a check; use justified `not_applicable` when appropriate.
- `deadline_date`: ISO calendar date or null. `deadline_verified`: boolean, default false. A verified deadline requires `evidence_status: verified` and `source_url`.
- `deadline_source_wording`, `deadline_timezone`, `date_checked`, `source_locator`: retain source precision and provenance. These are not automatically verified by the helper.
- `invitation_confirmed`: true, false or null; relevant to `invitation_only`.
- `availability_closed`: boolean, default false, for a verified employer closure without a dated deadline.
- `source_url` and `date_checked`: needed for verified evidence. Each `fail` requires verified evidence and a source URL; unsupported failures must be unknown instead. A date before the snapshot remains a dated observation, not proof that the page is unchanged.

The helper validates shape, computes calendar-date expiration, retains explicit unknowns and applies gates. It trusts the supplied interpretation of evidence. It does not parse source prose, discover omitted conditions, prove international eligibility, or replace the candidate/employer's confirmation. Saved evidence may become stale.

## Reporting a trial

Publish the snapshot date, scope, generalized candidate input, assumptions and unknowns, counts by opportunity type, a few traceable results, and limitations. Preserve original mistakes and corrections explicitly. The 2026-11-18 example retains the original results and shows a separately labelled offline replay under revised rules.

Do not call these counts accuracy, recall or time saved. Those require an independently reviewed reference set and, for improvement claims, a comparable baseline. Keep historical case dates fixed; never silently refresh a README example into an apparently current recommendation.
