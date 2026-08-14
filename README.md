# Upper Cumberland Auto

A single-page, statically generated roster of the auto repair, tire, body, diesel,
transmission and towing businesses of Overton, Putnam, Fentress, Clay, Pickett and Jackson
counties, Tennessee, with Overton County as the flagship. Published by
[Barnraised](https://barnraised.design/).

Canonical URL: `https://overtoncountyauto.com/` — **not registered.** Nothing here is
deployed, and the canonical is declared in `src/site_config.py` so every absolute reference
on the page agrees with the address the site will eventually answer on.

## Rebuild

```
python scripts/build.py          # writes dist/ and reports/exclusions.md
python scripts/validate_data.py  # validates all 71 harvested records
python scripts/verify.py         # 49 checks, writes reports/verify.md
```

All three exit 0 on a clean tree. Python 3.10+, no dependencies, no build tooling. Run them
from the repository root so `src/` is importable.

There is a fourth script, `scripts/annotate_roster.py`, which applies the hand pass to
`data/roster.json`. It has already been run and is idempotent; run it again after editing
its tables to re-apply exclusions, counties, categories, blurbs and sources.

## What is where

```
data/roster.json             71 harvested records plus the hand pass. The source of truth.
data/roster.harvest.bak.json the sweep exactly as it arrived, for diffing.
src/site_config.py           site identity, the six counties, the category vocabulary
src/data_model.py            record validation and the cross-record invariants
src/generator.py             the page, the JSON-LD graph, robots.txt, sitemap.xml
src/tokens.css               design tokens, light and dark
src/components.css           components
src/directory.js             the filter toolbar. The only script on the page.
scripts/annotate_roster.py   the hand pass, as data
scripts/build.py             build entry point
scripts/validate_data.py     data gate
scripts/verify.py            verification suite
dist/                        the deployable artifact: index.html, robots.txt, sitemap.xml
reports/exclusions.md        every excluded record and why
reports/verify.md            the last verification run
```

## The rule this project is built around

The site's only competitive claim is that its roster is real. So a listing may state exactly
two kinds of thing:

1. what is in the harvested record, and
2. what was read on the business's own website, recorded in that record's `sources` array
   with the URL, the date it was fetched, and what it is being used to support.

Nothing else. No founding years, no family histories, no "serving the community since", no
capability lists nobody fetched, no certifications, no turnaround times, no prices, no
testimonials. `src/data_model.py` enforces this with a list of claim patterns that a
generated directory reaches for by reflex; a blurb matching one of them fails validation
unless the record carries a source.

Two related rules:

- **Nothing is deleted.** Records that do not belong get an `excluded` field carrying the
  reason and are filtered at render time. The harvest file still holds all 71 rows, and
  `validate_data.py` fails if any record is neither rendered nor given a written reason.
- **Somebody else's numbers stay somebody else's.** The review counts and ratings are Google
  Business Profile figures read on 2026-08-13. They are printed with that provenance and the
  date attached, never sorted on, never turned into stars, and never emitted as
  `aggregateRating`. Hours come from the same place and were not confirmed with any shop,
  which is why no `openingHoursSpecification` is emitted either.

## Changing the roster

Adding a business, or correcting one:

1. Add or edit the record in `data/roster.json`.
2. Give it a hand pass in `scripts/annotate_roster.py` — county, county source, categories,
   brand type, web gap, and a blurb written for that business rather than filled in.
3. `python scripts/annotate_roster.py && python scripts/build.py && python
   scripts/validate_data.py && python scripts/verify.py`.

Every count on the page derives from the roster at build time. `verify.py` proves it with a
mutation test: it rebuilds the site into a temporary directory with one business removed and
fails if any figure survives unchanged. Nothing needs editing in two places, and nothing in
the verification suite needs editing when the roster grows.

## What the suite covers, and what it does not

`reports/verify.md` carries the full list. The 49 checks cover data integrity across all 71
records, the derived-count invariant and its mutation test, the no-invented-facts guard,
completeness with JavaScript disabled, external-link policy, self-containment, the JSON-LD
graph, WCAG AA contrast computed from the tokens in both colour schemes, and the mobile
overflow guards.

It does **not** cover live HTTP behaviour — apex response, www redirect, 404 status, TLS —
because nothing is deployed. Those checks belong beside these ones on the day the domain is
registered, in the pattern of the sister property at `C:\dev\mtn-printers`.

## Known gaps in the roster itself

Stated on the page as well as here, because they are real limitations rather than to-dos
somebody forgot:

- The local pack returns at most three businesses per query, so 59 is a floor and not a
  census. Walking the county-road frontage would find more.
- Jackson County returned two businesses in the entire sweep. That is a harvest failure, not
  a fact about Gainesboro.
- The towing sweep is known to be short.
- Two Celina records share a phone number and neither is resolved; both say so.
- Kent's Wholesale Tire is placed in Clarkrange by Google and in Rickman by the harvest.
  Both are in scope, so the conflict is printed rather than decided.
