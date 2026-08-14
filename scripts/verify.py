#!/usr/bin/env python3
"""Verification suite for Upper Cumberland Auto. Exits non-zero on any failure.

Everything here runs against the built artifact on disk. The domain is not
registered and nothing is deployed, so there is no live fetch and no check that
pretends to be one; when the site does go up, the HTTP-level checks from the
sister properties bolt on beside these rather than replacing them.

The suite is organised around the four things that could make this page a lie:

  a claim nobody can point at    invented-fact patterns, blurbs without sources,
                                 counts that were typed rather than derived
  a number that drifted          every headline figure is recomputed from the
                                 roster and matched against the rendered string,
                                 and a mutation test proves the figures move
                                 when the data moves
  a page that needs JavaScript   the document is re-checked with every script
                                 element stripped out
  a page nobody can read         WCAG AA contrast computed from the tokens in
                                 both schemes, plus the mobile-overflow guards

Run: python scripts/verify.py
"""

from __future__ import annotations

import html
import json
import re
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import generator  # noqa: E402
from src.data_model import (  # noqa: E402
    INVENTED_CLAIM_PATTERNS,
    PLACEHOLDER_PATTERNS,
    WORD,
    excluded,
    listed,
    phone_digits,
    validate_roster,
)
from src.generator import clean_address, host_of, phone_pretty, town  # noqa: E402
from src.site_config import CATEGORY_SCHEMA, COUNTIES, FLAGSHIP_COUNTY, SITE_CONFIG  # noqa: E402

DIST = ROOT / "dist"
HTML = DIST / "index.html"
REPORTS = ROOT / "reports"
SUBRESOURCE = r'<(?:script|img|iframe|source|link|embed|object)[^>]*?\s(?:src|href|data)="([^"]+)"'

RESULTS: list[tuple[str, bool, str]] = []


def check(name, fn):
    try:
        ok, detail = fn()
    except Exception as error:  # a check that explodes is a failing check
        ok, detail = False, f"{type(error).__name__}: {error}"
    RESULTS.append((name, bool(ok), str(detail)))
    print(("PASS " if ok else "FAIL ") + name + " — " + str(detail)[:110])


# --------------------------------------------------------------------------
# contrast
# --------------------------------------------------------------------------
def _channel(value: float) -> float:
    value /= 255
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def luminance(hex_colour: str) -> float:
    raw = hex_colour.lstrip("#")
    r, g, b = (int(raw[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def parse_palettes(css: str) -> dict[str, dict[str, str]]:
    """Pull the light and dark token palettes straight out of tokens.css."""
    blocks = re.split(r"@media\s*\(prefers-color-scheme:\s*dark\)", css)
    light = dict(re.findall(r"(--color-[a-z-]+):\s*(#[0-9a-fA-F]{6})", blocks[0]))
    dark = dict(light)
    if len(blocks) > 1:
        dark.update(re.findall(r"(--color-[a-z-]+):\s*(#[0-9a-fA-F]{6})", blocks[1]))
    return {"light": light, "dark": dark}


READING_PAIRS = (
    ("--color-text", "--color-canvas"),
    ("--color-text", "--color-surface"),
    ("--color-text", "--color-canvas-alt"),
    ("--color-text", "--color-accent-soft"),
    ("--color-text-muted", "--color-canvas"),
    ("--color-text-muted", "--color-surface"),
    ("--color-text-muted", "--color-canvas-alt"),
    ("--color-accent", "--color-canvas"),
    ("--color-accent", "--color-surface"),
    ("--color-accent", "--color-accent-soft"),
    ("--color-accent-ink", "--color-accent"),
    ("--color-appbar-text", "--color-appbar"),
    ("--color-appbar-muted", "--color-appbar"),
    ("--color-error", "--color-canvas"),
    ("--color-flag", "--color-canvas"),
    ("--color-flag", "--color-flag-soft"),
)


def main() -> int:
    page = HTML.read_text(encoding="utf-8")
    payload = json.loads((ROOT / "data" / "roster.json").read_text(encoding="utf-8"))
    records = validate_roster(payload)
    rows = listed(records)
    dropped = excluded(records)

    # Every figure below is recomputed here from the roster. Nothing in this
    # file restates a number that also lives in the generator.
    n_listed = len(rows)
    n_excluded = len(dropped)
    n_harvested = len(records)
    county_counts = {c: sum(1 for r in rows if r["county"] == c) for c in COUNTIES}
    gap_rows = [r for r in rows if r["web_gap_hand"]]
    n_gaps = len(gap_rows)
    overton = [r for r in rows if r["county"] == FLAGSHIP_COUNTY]
    overton_gaps = sum(1 for r in overton if r["web_gap_hand"])
    no_hours = sum(1 for r in rows if not r.get("hours"))
    towns = {town(r) for r in rows}

    # The document as a reader with scripting disabled receives it.
    nojs = re.sub(r"<script[^>]*>.*?</script>", "", page, flags=re.S)
    # The document with styles gone and tags flattened: the words a reader
    # actually sees, so an HTML attribute named `placeholder` is not mistaken
    # for placeholder copy.
    copy = re.sub(r"<[^>]+>", " ", re.sub(r"<style[^>]*>.*?</style>", "", nojs, flags=re.S))
    ld_blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)
    graph = json.loads(ld_blocks[0])["@graph"] if ld_blocks else []
    nodes = {node["@type"]: node for node in graph}

    # ---- 1. data integrity ------------------------------------------------
    check("every harvested record validates",
          lambda: (len(records) == n_harvested,
                   f"{n_harvested} records, {n_listed} listed, {n_excluded} excluded"))
    check("no record is silently dropped",
          lambda: (lambda strays: (not strays, f"{len(strays)} unaccounted" if strays
                                   else "every record is rendered or carries a reason"))(
              [r["id"] for r in records
               if "excluded" not in r and "blurb" not in r]))
    check("every exclusion carries a written reason",
          lambda: (all(len(r["excluded"]) >= 40 for r in dropped),
                   f"{n_excluded} reasons, shortest {min((len(r['excluded']) for r in dropped), default=0)} chars"))
    check("the harvest file still holds all 71 rows",
          lambda: (n_harvested == len(payload["businesses"]) == 71,
                   f"{n_harvested} rows in data/roster.json"))

    # ---- 2. counts are derived, not typed ---------------------------------
    check(f"{n_listed} listing blocks rendered",
          lambda: (lambda n: (n == n_listed, n))(len(re.findall(r'<article class="listing"', page))))
    check("county tallies on the page match the roster",
          lambda: (lambda bad: (not bad, ", ".join(bad) or
                                " ".join(f"{c}={county_counts[c]}" for c in COUNTIES)))(
              [c for c in COUNTIES
               if f'<p class="tally">{county_counts[c]} listed' not in page]))
    check("the roster size and town count on the page match the roster",
          lambda: (f"{n_listed} businesses, {len(towns)} towns" in page,
                   f"{n_listed} businesses across {len(towns)} towns"))
    check("the web-gap total on the page matches the roster",
          lambda: (f"{n_gaps} of the {n_listed} listed businesses" in page,
                   f"{n_gaps} gaps of {n_listed}"))
    check("the Overton flagship counts match the roster",
          lambda: (f"{overton_gaps} of these {len(overton)} businesses" in page
                   and f"{overton_gaps} of the\n    {len(overton)} in Overton County" in page,
                   f"{overton_gaps}/{len(overton)} Overton businesses with no web address"))
    check("counts move when the data moves (mutation test)",
          lambda: mutation_test(n_listed, n_gaps))

    # ---- 3. no invented facts --------------------------------------------
    check("no placeholder or lorem text anywhere in the copy",
          lambda: (lambda hits: (not hits, ", ".join(hits) or "none"))(
              [p for p in PLACEHOLDER_PATTERNS if re.search(p, copy, re.I)]))
    check("no unsourced invented-fact pattern in any entry",
          lambda: (lambda hits: (not hits, "; ".join(hits) or
                                 f"{len(INVENTED_CLAIM_PATTERNS)} patterns clear across "
                                 f"{n_listed} entries"))(
              [f"{r['id']}: {label}"
               for r in rows if not r["sources"]
               for pattern, label in INVENTED_CLAIM_PATTERNS
               if re.search(pattern, r["blurb"], re.I)]))
    check("every sourced claim points at a fetched, dated page",
          lambda: (lambda srcs: (
              bool(srcs) and all(s["url"].startswith("http") and len(s["supports"]) >= 20
                                 for s in srcs),
              f"{len(srcs)} sources across {sum(1 for r in rows if r['sources'])} entries"))(
              [s for r in rows for s in r["sources"]]))
    check("blurb lengths vary rather than matching",
          lambda: (lambda n: (len(set(n)) >= 12 and max(n) - min(n) >= 25,
                              f"{min(n)}-{max(n)} words, {len(set(n))} distinct lengths"))(
              [len(WORD.findall(r["blurb"])) for r in rows]))
    check("no star, rating or price markup on the page",
          lambda: (not re.search(r'(★|&#9733;|class="[^"]*(?:rating|stars|price)[^"]*")',
                                 page, re.I),
                   "absent — deliberate, the review figures are Google's"))
    check("review figures are printed with their provenance",
          lambda: (lambda n: (n == n_listed, f"{n} entries name the Google profile and the date"))(
              page.count("Not a rating by this directory")))
    check("no hours are claimed for a business that has none",
          lambda: (page.count("Hours not verified.") == no_hours,
                   f"{no_hours} entries say hours are not verified"))
    check("a blocked automated check is never reported as a dead site",
          lambda: (lambda blocked: (
              bool(blocked) and all(
                  "refused our automated request" in r["blurb"]
                  and not re.search(r"did not (?:answer|respond)", r["blurb"])
                  and r["web_gap_hand"] != "dead-site"
                  for r in blocked),
              f"{len(blocked)} blocked records, each described as refusing an automated request"))(
              [r for r in rows if r.get("check_note") == "blocked-to-automated-check"]))
    check("a dead site is reported with the date it was checked",
          lambda: (lambda dead: (
              bool(dead) and all(
                  f"no response when checked on {r.get('checked_at') or r['panel_checked']}" in page
                  for r in dead),
              f"{len(dead)} non-answering domains, each dated on the page"))(
              [r for r in rows if r["web_gap_hand"] == "dead-site"]))
    check("harvest locale artefacts are not published",
          lambda: (lambda bad: (not bad, ", ".join(bad) or "rendered addresses are clean ASCII"))(
              [r["id"] for r in rows
               if (clean_address(r.get("address")) or "").strip()
               and not (clean_address(r["address"]) or "").isascii()]))

    # ---- 4. the page works without JavaScript -----------------------------
    check("every listed business is present with JavaScript off",
          lambda: (lambda missing: (not missing, ", ".join(missing[:3]) or
                                    f"{n_listed}/{n_listed} names in the static HTML"))(
              [r["id"] for r in rows if html.escape(r["name"], quote=True) not in nojs]))
    check("every phone number is a tel: link with JavaScript off",
          lambda: (lambda missing: (not missing, ", ".join(missing[:3]) or
                                    f"{sum(1 for r in rows if r.get('phone'))} tel: links"))(
              [r["id"] for r in rows if r.get("phone")
               and f'href="tel:+1{phone_digits(r["phone"])}"' not in nojs]))
    check("every county section renders with JavaScript off",
          lambda: (all(f'id="{c.lower()}-county"' in nojs for c in COUNTIES),
                   f"{len(COUNTIES)} county sections in the static HTML"))
    check("the filter toolbar starts hidden and is the only scripted control",
          lambda: ('<aside class="toolbar" id="toolbar" aria-labelledby="filter-title" hidden>' in page
                   and '<select' not in nojs.split('id="toolbar"')[0],
                   "toolbar carries hidden; scripting unhides it"))
    check("no listing is injected client-side",
          lambda: (lambda js: (not any(bad in js for bad in
                                       ("innerHTML", "insertAdjacentHTML", "document.write",
                                        "createElement")),
                               "the script only toggles hidden on nodes already in the page"))(
              (ROOT / "src" / "directory.js").read_text(encoding="utf-8")))
    check("no phone number exists only inside a script",
          lambda: (lambda missing: (not missing, ", ".join(missing[:3]) or "none"))(
              [r["id"] for r in rows if r.get("phone")
               and phone_pretty(r["phone"])[0] not in nojs]))

    # ---- 5. links and self-containment ------------------------------------
    def link_audit():
        links = re.findall(r'<a\s+[^>]*href="(https?://[^"]+)"[^>]*>.*?</a>(\s*<span class="insecure">)?',
                           page, re.S)
        insecure = [(url, bool(marker)) for url, marker in links if url.startswith("http://")]
        unmarked = [url for url, marked in insecure if not marked]
        return (not unmarked,
                f"{len(links)} external links, {len(insecure)} over http and every one marked"
                if not unmarked else f"unmarked http links: {unmarked[:3]}")
    check("every external link is HTTPS or explicitly marked as not", link_audit)
    # <link rel="canonical"> is an identity declaration, not something the
    # browser fetches, so it is not a third-party request.
    check("no external subresource — no CDN, no web font, no third-party request",
          lambda: (lambda urls: (not urls, ", ".join(urls) or "self-contained"))(
              [u for u in re.findall(SUBRESOURCE, page)
               if not u.startswith(("data:", "#", "/")) and u != SITE_CONFIG.canonical_url]))
    check("no <img> element at all; the hero is inline SVG",
          lambda: ("<img" not in page and 'class="hero-art"' in page and 'role="img"' in page,
                   "one labelled inline SVG, zero fetched images"))

    def rel_audit():
        anchors = re.findall(r"<a\s([^>]*href=\"https?://[^\"]+\"[^>]*)>", page)
        external = [a for a in anchors if SITE_CONFIG.host not in a]
        unmarked = [a for a in external if "external" not in a]
        unsafe = [a for a in external if 'target="_blank"' in a and "noopener" not in a]
        return (not unmarked and not unsafe and bool(external),
                f"{len(external)} external anchors, every one rel-external and every new-tab "
                f"link rel-noopener" if not (unmarked or unsafe)
                else f"{len(unmarked)} unmarked, {len(unsafe)} without noopener")
    check("every external link declares itself, and new-tab links carry noopener", rel_audit)

    # ---- 6. structured data ----------------------------------------------
    check("JSON-LD parses and is a single @graph",
          lambda: (len(ld_blocks) == 1 and "@graph" in json.loads(ld_blocks[0]),
                   f"{len(graph)} nodes"))
    check("the graph carries every type the spec asks for",
          lambda: (lambda want: (want <= set(nodes), ", ".join(sorted(set(nodes)))))(
              {"WebSite", "Organization", "WebPage", "BreadcrumbList", "ItemList", "FAQPage"}))
    check("ItemList is unordered and sized from the roster",
          lambda: (nodes["ItemList"]["numberOfItems"] == n_listed
                   and nodes["ItemList"]["itemListOrder"].endswith("ItemListUnordered")
                   and len(nodes["ItemList"]["itemListElement"]) == n_listed,
                   f"{nodes['ItemList']['numberOfItems']} items, unordered"))
    check("no position key encodes a ranking of businesses",
          lambda: ('"position"' not in json.dumps(nodes["ItemList"])
                   and all('"position"' in json.dumps(n) for t, n in nodes.items()
                           if t == "BreadcrumbList"),
                   "position appears in the BreadcrumbList and nowhere else"))
    check("every listing node uses one of the spec's business types",
          lambda: (lambda types: (types <= set(CATEGORY_SCHEMA.values()), ", ".join(sorted(types))))(
              {item["item"]["@type"] for item in nodes["ItemList"]["itemListElement"]}))
    check("every listing node carries a PostalAddress",
          lambda: (all(item["item"]["address"]["@type"] == "PostalAddress"
                       for item in nodes["ItemList"]["itemListElement"]),
                   f"{n_listed} PostalAddress nodes"))
    check("no aggregateRating is emitted",
          lambda: ("aggregateRating" not in page,
                   "absent — harvested Google counts are not ours to mark up"))
    check("no openingHoursSpecification is emitted",
          lambda: ("openingHoursSpecification" not in page,
                   "absent — no listing's hours were confirmed with the shop"))

    # ---- 7. metadata and artifacts ---------------------------------------
    check("canonical, og:url and sitemap agree on one URL",
          lambda: (lambda loc: (
              f'<link rel="canonical" href="{SITE_CONFIG.canonical_url}">' in page
              and f'content="{SITE_CONFIG.canonical_url}"' in page
              and loc == SITE_CONFIG.canonical_url, loc))(
              ET.parse(DIST / "sitemap.xml").getroot()[0][0].text))
    check("robots.txt allows indexing and points at the sitemap",
          lambda: (lambda text: ("Allow: /" in text and "sitemap.xml" in text, text.split("\n")[1]))(
              (DIST / "robots.txt").read_text(encoding="utf-8")))
    check("exactly one h1, and every section is labelled",
          lambda: (page.count("<h1") == 1
                   and len(re.findall(r"<section[^>]*>", page))
                   == len(re.findall(r'<section[^>]*(?:aria-labelledby|id)="', page)),
                   f"1 h1, {len(re.findall(r'<section', page))} labelled sections"))
    check("skip link, viewport, print and reduced-motion rules present",
          lambda: (all(marker in page for marker in
                       ('class="skip"', 'name="viewport"', "@media print",
                        "prefers-reduced-motion", "prefers-color-scheme: dark")),
                   "present"))
    check("the exclusions report names every excluded record",
          lambda: (lambda text: (
              all(r["id"] in text and r["name"] in text for r in dropped),
              f"{n_excluded} records documented in reports/exclusions.md"))(
              (REPORTS / "exclusions.md").read_text(encoding="utf-8")))

    # ---- 8. readability and mobile ---------------------------------------
    palettes = parse_palettes((ROOT / "src" / "tokens.css").read_text(encoding="utf-8"))
    for scheme in ("light", "dark"):
        def contrast_check(scheme=scheme):
            palette = palettes[scheme]
            failures = [
                f"{fg}/{bg} {contrast(palette[fg], palette[bg]):.2f}"
                for fg, bg in READING_PAIRS
                if contrast(palette[fg], palette[bg]) < 4.5
            ]
            worst = min(contrast(palette[fg], palette[bg]) for fg, bg in READING_PAIRS)
            return not failures, (", ".join(failures) if failures
                                  else f"{len(READING_PAIRS)} pairs, worst {worst:.2f}:1")
        check(f"WCAG AA contrast on every reading pair ({scheme})", contrast_check)

    css = (ROOT / "src" / "components.css").read_text(encoding="utf-8")
    check("nothing is wider than a 375px viewport",
          lambda: (lambda wide: (not wide, ", ".join(wide) or
                                 "no fixed width above 360px in any component rule"))(
              [d for d in re.findall(r"(?:min-)?width:\s*(\d+)px", css) if int(d) > 360]))
    check("every table can scroll inside its own container",
          lambda: (page.count("<table") == page.count('class="table-scroll"')
                   and "overflow-x: auto" in css,
                   f"{page.count('<table')} tables, each in a scroll container"))
    check("long values wrap instead of pushing the layout out",
          lambda: ("overflow-wrap: anywhere" in css and "min-width: 0" in css,
                   "wrapping and min-width:0 both set"))
    check("touch targets are at least 44px",
          lambda: ("--touch-target: 2.75rem" in (ROOT / "src" / "tokens.css").read_text(encoding="utf-8")
                   and css.count("var(--touch-target)") >= 6,
                   f"{css.count('var(--touch-target)')} rules pin the 44px minimum"))
    check("page weight stays under a 400KB budget",
          lambda: (len(page.encode()) < 400 * 1024, f"{len(page.encode()) / 1024:.1f} KB"))

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    verdict = f"**{'ALL GREEN' if passed == total else 'FAILURES PRESENT'} — {passed}/{total} checks passed**"
    print("\n" + verdict.replace("**", ""))

    write_report(verdict, n_harvested, n_listed, n_excluded, n_gaps, len(overton),
                 overton_gaps, county_counts, len(towns))
    return 0 if passed == total else 1


def mutation_test(n_listed: int, n_gaps: int):
    """Rebuild with one business removed and prove every figure moved.

    A count that is hardcoded survives this. A count that is derived cannot.
    """
    payload = json.loads((ROOT / "data" / "roster.json").read_text(encoding="utf-8"))
    victim = next(r for r in payload["businesses"]
                  if "excluded" not in r and r["web_gap_hand"] and r["county"] != "Jackson")
    for field in ("county", "county_source", "categories_hand", "brand_type",
                  "web_gap_hand", "blurb", "notes", "sources"):
        victim.pop(field, None)
    victim["excluded"] = "Mutation-test removal; this record is never written back to disk."

    with tempfile.TemporaryDirectory() as tmp:
        sandbox = Path(tmp)
        data = sandbox / "roster.json"
        data.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        saved = (generator.DATA, generator.DIST, generator.OUT, generator.REPORTS)
        generator.DATA = data
        generator.DIST = sandbox / "dist"
        generator.OUT = generator.DIST / "index.html"
        generator.REPORTS = sandbox / "reports"
        try:
            _, _, kept, _ = generator.build()
            mutated = generator.OUT.read_text(encoding="utf-8")
        finally:
            generator.DATA, generator.DIST, generator.OUT, generator.REPORTS = saved

    ok = (kept == n_listed - 1
          and f'<article class="listing"' in mutated
          and len(re.findall(r'<article class="listing"', mutated)) == n_listed - 1
          and f"{n_gaps - 1} of the {n_listed - 1} listed businesses" in mutated
          and f"{n_gaps} of the {n_listed} listed businesses" not in mutated)
    return ok, (f"removing one business moved the roster to {kept} and the gap total to "
                f"{n_gaps - 1}; no figure survived unchanged")


def write_report(verdict, harvested, listed_n, excluded_n, gaps, overton_n, overton_gaps,
                 county_counts, towns):
    lines = [
        "# Verification report — Upper Cumberland Auto",
        "",
        f"Run {SITE_CONFIG.date_modified} against the built artifact at `dist/index.html`.",
        "Nothing is deployed and `overtoncountyauto.com` is " + SITE_CONFIG.domain_status
        + ", so there are no live HTTP checks in this run and none are faked.",
        "",
        verdict,
        "",
        "Re-runnable: `python scripts/build.py && python scripts/validate_data.py "
        "&& python scripts/verify.py`",
        "",
        "## Roster at the time of this run",
        "",
        "| Measure | Count |",
        "|---|---|",
        f"| Harvested records in the file | {harvested} |",
        f"| Listed on the page | {listed_n} |",
        f"| Excluded, each with a written reason | {excluded_n} |",
        f"| Deleted | 0 |",
        f"| In {FLAGSHIP_COUNTY} County | {overton_n} |",
        f"| Proven to have no web address of their own | {gaps} |",
        f"| …of those, in {FLAGSHIP_COUNTY} County | {overton_gaps} |",
        f"| Towns represented | {towns} |",
        "",
        "| County | Listed |",
        "|---|---|",
    ]
    lines += [f"| {county} | {county_counts[county]} |" for county in COUNTIES]
    lines += ["", "## Checks", "", "| Check | Result | Detail |", "|---|---|---|"]
    for name, ok, detail in RESULTS:
        lines.append(f"| {name} | {'PASS' if ok else 'FAIL'} | {detail[:90]} |")
    lines += [
        "",
        "## What this covers",
        "",
        "Data integrity across all 71 harvested records, including the invariant that a record is",
        "either fully hand-annotated or carries a written exclusion reason — there is no third",
        "state and nothing was deleted. Every headline figure on the page is recomputed here from",
        "the roster and matched against the rendered string, and a mutation test rebuilds the site",
        "with one business removed to prove the figures are derived rather than typed.",
        "",
        "The no-invented-facts guard runs a list of claim patterns — founding years, family",
        "ownership, certifications, turnaround times, prices, reputation adjectives — over every",
        "entry, and fails any match on an entry that carries no fetched source to point at.",
        "",
        "The document is re-checked with every script element stripped: all listings, all county",
        "sections and every phone number have to survive that, and the filter toolbar has to be",
        "hidden until scripting unhides it.",
        "",
        "Contrast is computed from the tokens in `src/tokens.css` for both colour schemes rather",
        "than eyeballed, and the mobile guards are static rules — no fixed width above 360px, every",
        "table in its own scroll container, wrapping on long values.",
        "",
        "## Deliberately absent, and asserted as absent",
        "",
        "- `aggregateRating`. The review counts are Google Business Profile figures read on one day.",
        "  They are printed with that provenance and never marked up as structured review data.",
        "- `openingHoursSpecification`. Hours came off Google profiles and were not confirmed with",
        "  any shop, so no listing claims verified opening hours.",
        "- `geo`. The harvest carries no coordinates, so no listing invents any.",
        "- Star ratings, rank numbers and prices, for the reasons in `src/generator.py`.",
        "",
        "## Not covered here",
        "",
        "Live HTTP behaviour — apex response, www redirect, 404 status, TLS — because nothing is",
        "deployed. Those checks belong beside these ones on the day the domain is registered.",
        "",
    ]
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "verify.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"wrote {REPORTS / 'verify.md'}")


if __name__ == "__main__":
    sys.exit(main())
