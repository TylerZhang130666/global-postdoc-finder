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

## 2. Create positioning and keywords

Write a two-sentence positioning statement covering current expertise, evidence, intended direction, and contribution. Do not overstate skills.

Build keyword families for role titles, domain concepts, methods/tools, outputs, and project or funding language. Add local-language role terms from the country guidance when useful. Combine one role term with one or two topic/method terms. Derive terms from real evidence and repeated wording in representative vacancies.

## 3. Search current sources

For live opportunities, browse the web and record the search date. Search official employer, funder, project, national, and regional portals first; use reputable aggregators for discovery; use PI/team pages for fit and future outreach targets. Read `references/global-postdoc-resources.md` for regional source guidance.

Cover only regions compatible with the candidate's preferences and preserve their priority order in search effort and output. When scope is explicitly worldwide, search in regional batches: Europe; United States and Canada; Latin America and the Caribbean; East, South, and Southeast Asia; Middle East and North Africa; Sub-Saharan Africa; Australia and New Zealand. Include international research organizations when relevant.

Account for regional title differences such as postdoctoral fellow, postdoctoral associate, research fellow, research associate, research scientist, project researcher, and fixed-term researcher. Compare salary only when authoritative figures are available, retaining currency, pay period, gross/net status, and cost-of-living uncertainty.

Search advertised jobs, fellowships, and potential hosts as separate channels. Never call a fellowship an existing job or call a role open unless an authoritative page shows a future deadline or active status. Mark uncertain, undated, inaccessible, and aggregator-only records accordingly. Do not invent salary, visa eligibility, funding, deadlines, or contact details.

## 4. Normalize and screen records

Use `assets/job-tracker-template.csv`. Capture title, institution, group/PI, country, URL, date checked, deadline, status, criteria, fit dimensions, evidence, gaps, uncertainties, and next action.

Apply hard filters before scoring: deadline, degree timing, location, career stage, explicit eligibility, language, work authorization or sponsorship where stated, and candidate exclusions. Keep a rejection reason to prevent repeated reconsideration.

## 5. Score transparently

Score each remaining opportunity from 0 to 5 on research/topic fit (30%), methods and evidence (25%), career-stage and eligibility (20%), timing (10%), location/conditions (10%), and strategic growth value (5%). Calculate a weighted score out of 100.

Lower confidence when facts are unknown. Label A for 75–100 with no known hard blocker, B for 55–74 or one manageable gap, C for lower or speculative targets, and Excluded for a confirmed hard blocker. Explain scores with evidence. Prestige is not a scoring category.

## 6. Produce the decision package

Return search scope and date, the user's stated geographic priority order, candidate positioning, keyword bank, ranked vacancy table with direct links and confidence, a separate future PI/group list, top gaps with concrete proof items, and next actions ordered by deadline and expected value. Group results by the user's priority tiers before sorting by fit inside each tier. Offer to save records in the tracker. Do not overwrite original documents.

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

The scanner is a warning system, not proof of anonymity.
