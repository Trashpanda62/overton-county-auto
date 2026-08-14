# Verification report — Upper Cumberland Auto

Run 2026-08-14 against the built artifact at `dist/index.html`.
Nothing is deployed and `overtoncountyauto.com` is not yet registered, so there are no live HTTP checks in this run and none are faked.

**ALL GREEN — 50/50 checks passed**

Re-runnable: `python scripts/build.py && python scripts/validate_data.py && python scripts/verify.py`

## Roster at the time of this run

| Measure | Count |
|---|---|
| Harvested records in the file | 71 |
| Listed on the page | 59 |
| Excluded, each with a written reason | 12 |
| Deleted | 0 |
| In Overton County | 20 |
| Proven to have no web address of their own | 45 |
| …of those, in Overton County | 15 |
| Towns represented | 11 |

| County | Listed |
|---|---|
| Overton | 20 |
| Putnam | 17 |
| Fentress | 13 |
| Clay | 4 |
| Pickett | 3 |
| Jackson | 2 |

## Checks

| Check | Result | Detail |
|---|---|---|
| every harvested record validates | PASS | 71 records, 59 listed, 12 excluded |
| no record is silently dropped | PASS | every record is rendered or carries a reason |
| every exclusion carries a written reason | PASS | 12 reasons, shortest 154 chars |
| the harvest file still holds all 71 rows | PASS | 71 rows in data/roster.json |
| 59 listing blocks rendered | PASS | 59 |
| county tallies on the page match the roster | PASS | Overton=20 Putnam=17 Fentress=13 Clay=4 Pickett=3 Jackson=2 |
| the roster size and town count on the page match the roster | PASS | 59 businesses across 11 towns |
| the web-gap total on the page matches the roster | PASS | 45 gaps of 59 |
| the Overton flagship counts match the roster | PASS | 15/20 Overton businesses with no web address |
| counts move when the data moves (mutation test) | PASS | removing one business moved the roster to 58 and the gap total to 44; no figure survived u |
| no placeholder or lorem text anywhere in the copy | PASS | none |
| no unsourced invented-fact pattern in any entry | PASS | 17 patterns clear across 59 entries |
| every sourced claim points at a fetched, dated page | PASS | 10 sources across 10 entries |
| blurb lengths vary rather than matching | PASS | 5-67 words, 30 distinct lengths |
| no star, rating or price markup on the page | PASS | absent — deliberate, the review figures are Google's |
| review figures are printed with their provenance | PASS | 59 entries name the Google profile and the date |
| no hours are claimed for a business that has none | PASS | 12 entries say hours are not verified |
| a blocked automated check is never reported as a dead site | PASS | 2 blocked records, each described as refusing an automated request |
| a dead site is reported with the date it was checked | PASS | 4 non-answering domains, each dated on the page |
| harvest locale artefacts are not published | PASS | rendered addresses are clean ASCII |
| every listed business is present with JavaScript off | PASS | 59/59 names in the static HTML |
| every phone number is a tel: link with JavaScript off | PASS | 55 tel: links |
| every county section renders with JavaScript off | PASS | 6 county sections in the static HTML |
| the filter toolbar starts hidden and is the only scripted control | PASS | toolbar carries hidden; scripting unhides it |
| no listing is injected client-side | PASS | the script only toggles hidden on nodes already in the page |
| no phone number exists only inside a script | PASS | none |
| every external link is HTTPS or explicitly marked as not | PASS | 39 external links, 8 over http and every one marked |
| no external subresource — no CDN, no web font, no third-party request | PASS | self-contained |
| no <img> element at all; the hero is inline SVG | PASS | one labelled inline SVG, zero fetched images |
| every external link declares itself, and new-tab links carry noopener | PASS | 39 external anchors, every one rel-external and every new-tab link rel-noopener |
| JSON-LD parses and is a single @graph | PASS | 6 nodes |
| the graph carries every type the spec asks for | PASS | BreadcrumbList, FAQPage, ItemList, Organization, WebPage, WebSite |
| ItemList is unordered and sized from the roster | PASS | 59 items, unordered |
| no position key encodes a ranking of businesses | PASS | position appears in the BreadcrumbList and nowhere else |
| every listing node uses one of the spec's business types | PASS | AutoBodyShop, AutoRepair, AutomotiveBusiness, TireShop, TowingService |
| every listing node carries a PostalAddress | PASS | 59 PostalAddress nodes |
| no aggregateRating is emitted | PASS | absent — harvested Google counts are not ours to mark up |
| no openingHoursSpecification is emitted | PASS | absent — no listing's hours were confirmed with the shop |
| canonical, og:url and sitemap agree on one URL | PASS | https://overtoncountyauto.com/ |
| robots.txt allows indexing and points at the sitemap | PASS | User-agent: * |
| exactly one h1, and every section is labelled | PASS | 1 h1, 16 labelled sections |
| skip link, viewport, print and reduced-motion rules present | PASS | present |
| the exclusions report names every excluded record | PASS | 12 records documented in reports/exclusions.md |
| WCAG AA contrast on every reading pair (light) | PASS | 16 pairs, worst 5.53:1 |
| WCAG AA contrast on every reading pair (dark) | PASS | 16 pairs, worst 7.39:1 |
| nothing is wider than a 375px viewport | PASS | no fixed width above 360px in any component rule |
| every table can scroll inside its own container | PASS | 3 tables, each in a scroll container |
| long values wrap instead of pushing the layout out | PASS | wrapping and min-width:0 both set |
| touch targets are at least 44px | PASS | 8 rules pin the 44px minimum |
| page weight stays under a 400KB budget | PASS | 195.9 KB |

## What this covers

Data integrity across all 71 harvested records, including the invariant that a record is
either fully hand-annotated or carries a written exclusion reason — there is no third
state and nothing was deleted. Every headline figure on the page is recomputed here from
the roster and matched against the rendered string, and a mutation test rebuilds the site
with one business removed to prove the figures are derived rather than typed.

The no-invented-facts guard runs a list of claim patterns — founding years, family
ownership, certifications, turnaround times, prices, reputation adjectives — over every
entry, and fails any match on an entry that carries no fetched source to point at.

The document is re-checked with every script element stripped: all listings, all county
sections and every phone number have to survive that, and the filter toolbar has to be
hidden until scripting unhides it.

Contrast is computed from the tokens in `src/tokens.css` for both colour schemes rather
than eyeballed, and the mobile guards are static rules — no fixed width above 360px, every
table in its own scroll container, wrapping on long values.

## Deliberately absent, and asserted as absent

- `aggregateRating`. The review counts are Google Business Profile figures read on one day.
  They are printed with that provenance and never marked up as structured review data.
- `openingHoursSpecification`. Hours came off Google profiles and were not confirmed with
  any shop, so no listing claims verified opening hours.
- `geo`. The harvest carries no coordinates, so no listing invents any.
- Star ratings, rank numbers and prices, for the reasons in `src/generator.py`.

## Not covered here

Live HTTP behaviour — apex response, www redirect, 404 status, TLS — because nothing is
deployed. Those checks belong beside these ones on the day the domain is registered.
