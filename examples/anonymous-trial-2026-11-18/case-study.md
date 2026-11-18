# Global search trial on 2026-11-18

## Purpose and input

The task was to run Global Postdoc Finder on an anonymized candidate CV, after the candidate explicitly chose worldwide scope. See [candidate input summary](candidate-profile.md). The trial assumed an earliest start in July 2027 after expected PhD completion in June; missing private eligibility information remained unresolved.

The original Skill SHA-256 and output hashes are recorded in [run-manifest.json](run-manifest.json). This identifies the historical rules used. The original trial already included manual conservative action overrides, so it is not a clean baseline for a later Skill version.

## Search and interpretation

The model generated role/domain/method queries, searched in seven regional groups, opened employer, funder and host pages, and normalized the findings. The 35 keyword queries included soil physics, structure, compaction, erosion, hydraulic properties, CT imaging and adjacent modelling terms, with regional and institution variants. Browsing and interpretation were performed by Codex and its tools, not a standalone crawler in this repository.

Field-level checks retained source URLs and locators, source quality, dates, qualification gaps and the next action. An employer's group page was not treated as proof of a funded vacancy. Multiple aggregator pages referring to the same role were combined; an apparent employer-name conflict remained explicit. Scores came from model judgments on six dimensions; arithmetic was checked with a script and workbook formulas.

This was a first pass across Europe; the US and Canada; Latin America and the Caribbean; East/South/Southeast Asia; the Middle East and North Africa; Sub-Saharan Africa; and Australia/New Zealand. It was not exhaustive: Brazilian funding dominated Latin American retained results, Saudi funding dominated Middle Eastern coverage, and no suitable New Zealand notice was retained. Countries did not receive equal search effort.

## Original results

- 18 records involving 13 countries: 11 job notices/leads, 4 fellowships and 3 potential hosts.
- 5 records marked Excluded at the time: three expired job notices, one degree-deadline conflict, and one absence of mandatory language evidence in the CV.
- 0 vacancies had all candidate eligibility and arrival conditions confirmed for direct application.
- Notable preparation paths were the CAAS three-dimensional soil-structure role, JSPS FY2027 second recruitment and a FAPESP host-based proposal.

Read the [original structured results](original-results.json), [HTML report](Global_Postdoc_Trial_Report.html), and [Excel tracker](Global_Postdoc_Trial_Tracker.xlsx). The HTML and workbook are preserved byte-for-byte from the original trial, including the language-evidence screening error and conservative manual action overrides. They are historical artifacts, not current vacancy recommendations.

## Findings that changed the Skill

| Observed issue | Revised behavior |
|---|---|
| WUR's language requirement lacked CV evidence and was counted as exclusion. | Missing evidence becomes unknown; only a confirmed failure becomes ineligible. This corrects the original overstrict decision. |
| A high-scoring fellowship lacked a confirmed host and private eligibility facts. | Preserve numerical match separately from action readiness; unknown mandatory conditions prevent action A. |
| A Singapore role had NUS in a secondary listing and NTU in employer-indexed evidence. | Keep the employer-field conflict visible; do not adopt the secondary deadline or infer current openness. |
| A future KAUST full-proposal deadline could look like a new application opportunity. | Track entry stage and actual invitation, not just the latest date. |
| An early advertised start preceded graduation but might be negotiable. | Ask about flexibility; do not invent either a guaranteed extension or an absolute failure. |
| Anonymous input omitted age, residence and recent-publication dates needed by some opportunities. | Request only relevant private eligibility answers and keep them separate from public research profiles. |
| Search results contained old but highly relevant CT/soil-physics advertisements. | Screen verified dates and degree timing before computing scores. |

## Offline replay under revised rules

[normalized-records.json](normalized-records.json) is a manual interpretation of the already-saved evidence using the revised schema. In this conservative replay, unconfirmed language/start conditions remain unknown. Normalization itself is not an independent gold-standard review.

Run from the repository root:

```text
python scripts/evaluate_records.py examples/anonymous-trial-2026-11-18/normalized-records.json --as-of 2026-11-18 --out replay.json
```

The saved [replayed-results.json](replayed-results.json) contains 0 action A, 4 B, 7 C, 4 Excluded and 3 Host only. E01 changes from the historical Excluded label to unknown eligibility with action C pending evidence/scoring. The three hosts lose employment-like A/B labels and are explicitly marked Host only; their research fit remains in the original narrative.

The replay now identifies rule revision `2026-11-18.1`, which also excludes a verified closed advertised vacancy when `application_access` is `closed` and the auxiliary closure flag is absent or false. None of these 18 interpreted inputs change action priority under that fix. The original HTML, workbook and first-run results remain unchanged. The [README preview](report-preview.png) is an actual browser capture of the saved HTML, with no changes to its report content.

This replay did not refresh URLs or obtain new candidate answers. It demonstrates deterministic handling of the interpreted snapshot, not improved search accuracy, vacancy availability, or success in applications.

## Validation and limitations

The original run checked unique record IDs, scoring arithmetic, expired dates, summary/formula consistency, local report links, workbook display and direct candidate identifiers. New unit tests exercise the revised arithmetic and decision gates. These checks do not independently validate candidate credentials or the model's source interpretation.

No independently labelled reference set, repeated multi-candidate study or matched-budget comparison with a basic prompt was run. Precision, recall, time savings and comparative improvement are therefore not measured.

Public files contain reviewed candidate summaries and result artifacts, not the original CV, private eligibility responses, browser data or query history. Pattern scanning is supplemented by inspection of Office package metadata and links. The retained research details can still be linkable to public information; anonymity is not guaranteed.
