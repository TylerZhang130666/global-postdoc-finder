---
name: global-postdoc-finder
description: Build an evidence-based global postdoc search system from a candidate's CV, research profile, constraints, and goals. Use when Codex needs to discover and verify postdoctoral or adjacent research roles worldwide, compare countries and regions, create multilingual keyword banks, score vacancies and research groups, maintain a job tracker, identify skill gaps, plan outreach, or tailor application materials for any academic discipline while protecting personal data.
---

# Global Postdoc Finder

Build a reproducible search and decision system. Treat candidate documents as private inputs; never copy identifying information into public artifacts, search queries, or examples unless essential and explicitly approved.

## 1. Collect the candidate profile

Ask only for missing information. Accept a CV, publication list, or answers to `assets/candidate-profile-template.md`. Extract research topics, methods, tools, strongest outputs, target roles and locations, timing, work-authorization constraints, languages, exclusions, and preferences.

Treat the user's geographic priorities as binding search instructions:

1. If the user names priority countries, regions, cities, institutions, or sectors, search them first and allocate most effort there in the order given.
2. If the user names acceptable but secondary locations, search them only after completing the priority scope.
3. If the user excludes a location, do not search or recommend it.
4. If no geographic preference is provided, ask for it before a large search. Do not silently choose Europe, North America, prestigious universities, or any other default.
5. Search all regions only when the user explicitly says worldwide, global, no location preference, or equivalent.
6. When a user gives unordered locations, treat them as equal priority unless the user indicates otherwise.

Keep a private profile in the user's workspace and a separate search profile. Exclude name, email, phone, home address, IDs, birth date, and unrelated personal details from the search profile. Do not infer protected traits, immigration eligibility, or constraints the user did not provide.

Separate research evidence from private eligibility facts. An anonymized CV may omit residence history, nationality, language evidence, publication dates, or whether the candidate already passed a fellowship stage. Ask only the minimum question needed for a relevant requirement; a private eligibility answer is usually sufficient without identity documents, a full birth date, or a home address. Missing CV evidence means **unknown**, not failure. Label an assumed earliest start date and distinguish degree completion, defence, and award dates when the notice does.

## 2. Create positioning and keywords

Write a two-sentence positioning statement covering current expertise, evidence, intended direction, and contribution. Do not overstate skills.

Build keyword families for role titles, domain concepts, methods/tools, outputs, and project or funding language. Add local-language role terms from the country guidance when useful. Combine one role term with one or two topic/method terms. Derive terms from real evidence and repeated wording in representative vacancies.

## 3. Search current sources

For live opportunities, browse the web and record the search date. Search official employer, funder, project, national, and regional portals first; use reputable aggregators for discovery; use PI/team pages for fit and future outreach targets. Read `references/global-postdoc-resources.md` for regional source guidance.

Cover only regions compatible with the candidate's preferences and preserve their priority order in search effort and output. When scope is explicitly worldwide, search in regional batches: Europe; United States and Canada; Latin America and the Caribbean; East, South, and Southeast Asia; Middle East and North Africa; Sub-Saharan Africa; Australia and New Zealand. Include international research organizations when relevant.

Account for regional title differences such as postdoctoral fellow, postdoctoral associate, research fellow, research associate, research scientist, project researcher, and fixed-term researcher. Compare salary only when authoritative figures are available, retaining currency, pay period, gross/net status, and cost-of-living uncertainty.

Search advertised jobs, fellowships, and potential hosts as separate channels. Never call a fellowship an existing job or call a role open unless an authoritative page shows a future deadline or active status. Mark uncertain, undated, inaccessible, and aggregator-only records accordingly. Do not invent salary, visa eligibility, funding, deadlines, or contact details.

Verify individual fields, not just the institution. An official group page confirms a group, not a vacancy; a search-indexed employer page does not establish current availability. A retained Apply button does not override an expired deadline. Record conflicting employer names, dates, or duties; leave unresolved fields unknown instead of borrowing the most convenient value. Deduplicate using employer, role and vacancy ID or canonical notice URL.

For fellowships, identify the specific round, entry stage, invitation or nomination requirement, host requirement, and applicant versus host-institution deadline. A future second-stage deadline does not make the first stage open. Keep source date wording, timezone and precision. A negotiable or unspecified start date is not a confirmed conflict. Report searched regions and gaps; a global first pass is not an exhaustive global search.

## 4. Normalize and screen records

Use `assets/job-tracker-template.csv`. Capture title, institution, group/PI, country, URL, date checked, deadline, status, criteria, fit dimensions, evidence, gaps, uncertainties, and next action.

Apply hard filters before scoring: deadline, degree timing, location, career stage, explicit eligibility, language, work authorization or sponsorship where stated, and candidate exclusions. Keep a rejection reason to prevent repeated reconsideration.

Read [screening and scoring](references/screening-and-scoring.md) before classifying records. For each applicable requirement, record `pass`, `fail`, `unknown`, or justified `not_applicable`, with evidence. Exclude only a confirmed failure or a verified expired vacancy. For example, a stated mandatory language absent from the CV requires clarification; it does not prove the candidate cannot speak it. Keep vacancy availability, candidate eligibility, source confidence, and application-stage access as separate fields.

## 5. Score transparently

Score each remaining opportunity from 0 to 5 on research/topic fit (30%), methods and evidence (25%), career-stage and eligibility (20%), timing (10%), location/conditions (10%), and strategic growth value (5%). Calculate a weighted score out of 100.

Preserve the numerical match band separately from the action priority. A match band is A at 75–100, B at 55–less than 75, and C below 55. Action priority is A only when the score is at least 75, the vacancy or round is verified and accessible now, and all applicable mandatory checks pass. Unknown mandatory eligibility or a published future round caps priority at B; unverified/conflicting availability or an inaccessible entry stage caps it at C. Confirmed failure is Excluded before scoring. Record the reason whenever action priority differs from the match band. An incomplete score remains unavailable, not zero. Prestige is not a scoring category.

Use `scripts/evaluate_records.py` for repeatable arithmetic and action gates when recording a structured run. It consumes interpreted JSON evidence; it does not browse, parse CVs, validate source claims, or estimate admission probability. Potential hosts receive a separate qualitative research-fit assessment, never a vacancy-readiness score. The schema and CLI are in the screening reference.

## 6. Produce the decision package

Return search scope and date, the user's stated geographic priority order, candidate positioning, keyword bank, ranked vacancy table with direct links and confidence, a separate future PI/group list, top gaps with concrete proof items, and next actions ordered by deadline and expected value. Group results by the user's priority tiers before sorting by fit inside each tier. Offer to save records in the tracker. Do not overwrite original documents.

Distinguish total records, advertised-job leads, verified current vacancies, fellowships, hosts, confirmed exclusions, and unresolved checks. A result with zero fully confirmed direct-application options is valid. If saving a trial, preserve the input assumptions, source check date, field evidence, calculation inputs, rule version, and limitations. Treat a static replay of old records separately from a fresh live search. Do not report precision, recall, time savings, or superiority to a basic prompt without an appropriate independent evaluation and comparator.

## 7. Tailor outreach and materials

Draft outreach only after reading the specific group's work. Include timing, relevant evidence, a precise fit sentence, intended direction, and a modest request. Distinguish networking from applying to an advertised vacancy.

Use only supported claims, map evidence to explicit criteria, retain publication status accurately, and flag missing facts with placeholders. Do not send emails or submit applications without explicit confirmation.

## 8. Protect privacy before publication

Before packaging, sharing, committing, or uploading:

1. exclude CVs, letters, trackers, browser profiles, downloaded pages, and search histories by default
2. replace candidate-specific examples with neutral placeholders
3. run `scripts/privacy_scan.py <skill-directory>`
4. manually review names, emails, phone numbers, paths, IDs, and organization-specific details
5. inspect archive contents after packaging

For an explicitly authorized anonymous case, export a reviewed summary and allowlisted results rather than copying the private working directory. Remove exact publication titles/DOIs, institution/mentor combinations, grant identifiers, hidden metadata, local paths and other reidentification clues as needed. Preserve job-source institutions as public evidence, distinct from the candidate's affiliations. Explain any generalization of the input and retain historical run results, including mistakes and manual overrides, without presenting them as a new-version benchmark.

The scanner checks common patterns in supported text files; it cannot reliably identify names, inspect PDF/Office contents, or prove anonymity. Inspect binary artifacts and semantic identifiers separately. Public examples may still be linkable from their research details.
