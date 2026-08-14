#!/usr/bin/env python3
"""Generate the Upper Cumberland Auto directory page.

One page. Every listing, phone number, address and county section is in the
initial HTML; the filter toolbar is the only scripted thing on it and it starts
hidden, so a reader with JavaScript off never sees a control that does nothing.

Three conventions this page could have had and does not:

  * rank numbers. The roster is unranked and inclusion is free, so numbering it
    would invent an order the research does not support.
  * star ratings. The review counts in the file are Google Business Profile
    figures read once, on 2026-08-13. They are printed with that provenance
    attached and never converted into a score, a sort order or an
    aggregateRating node. They are not ours to republish as structured review
    data and we could not stand behind them if they were.
  * a stat strip. It would hold the review count, the rating and the county.
    Two of those are somebody else's numbers and the third is in the heading.

What the page has instead is a flag: one rust marker meaning this business has
no real web address of its own. That is the finding the whole property exists
to carry, and it is derived from the recorded host on every render rather than
typed in anywhere.

Entry lengths vary on purpose, from five words to nearly seventy. Descriptions
of matching length are the loudest signal on a directory page that it was
generated rather than written, and these businesses genuinely do not warrant
equal wordcount: some have a fetched service list from their own site, and some
are a road name and a phone number.

Run: python scripts/build.py
"""

from __future__ import annotations

import html
import json
import re
import shutil
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from src.data_model import excluded, listed, phone_digits, validate_roster
from src.site_config import (
    CATEGORIES,
    CATEGORY_LABELS,
    CATEGORY_SCHEMA,
    COUNTIES,
    FLAGSHIP_COUNTY,
    SITE_CONFIG,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "roster.json"
DIST = ROOT / "dist"
OUT = DIST / "index.html"
REPORTS = ROOT / "reports"
TOKENS = ROOT / "src" / "tokens.css"
COMPONENTS = ROOT / "src" / "components.css"
SCRIPT = ROOT / "src" / "directory.js"

CANONICAL = SITE_CONFIG.canonical_url
UPDATED = SITE_CONFIG.date_human
HARVEST = SITE_CONFIG.harvest_date_human

WEB_GAP_LABELS = {
    "no-website": "No website",
    "facebook-only": "Facebook only",
    "rented-subdomain": "Rented web address",
    "aggregator-only": "Listings site only",
    "dead-site": "Site did not answer",
    "domain-for-sale": "Domain for sale",
}
# Gaps whose recorded URL is still the business's real presence, so the link is
# worth following. The rest are named in text and not linked: sending a reader
# to a listings farm or a domain broker on the strength of a Google panel field
# would be doing the thing this directory exists to complain about.
LINKABLE_GAPS = {None, "facebook-only", "rented-subdomain"}

DISCLOSURE = (
    "<strong>Unranked, unrated, unpaid.</strong> Businesses appear alphabetically inside their "
    "county. Nothing on this page is numbered, scored or sold, no listing was purchased, and no "
    "business reviewed its entry before publication. This is not the Overton County Chamber of "
    "Commerce, and neither is any national site with a chamber-sounding domain name."
)

METHOD = (
    ("Where the names came from",
     "A Google local-pack sweep of {queries} town-and-category queries across the six counties on "
     "{harvest}, then a per-record check of the website each Google profile pointed at. The local "
     "pack returns at most three businesses per query, so this is a seed roster from a fixed "
     "query grid and not a census. The real six-county count is certainly higher."),
    ("What a listing is allowed to say",
     "Only what the harvested record contains, or what was read on the business's own website and "
     "recorded as a source with the date it was read. There are no founding years on this page, no "
     "family histories, no capability lists that nobody fetched, no turnaround times and no "
     "prices, because none of that was researched. {sourced} of the {listed} entries carry a "
     "fetched source; the rest say less, on purpose."),
    ("Why the review counts look like that",
     "They are Google Business Profile figures, read once on {harvest} and not re-checked since. "
     "They are printed with that provenance attached, never sorted on, never turned into stars, "
     "and never emitted as structured review data. They belong to Google and to the customers who "
     "wrote them."),
    ("Why some hours are missing",
     "{no_hours} of the {listed} businesses have no hours in the record, and those entries say so "
     "rather than guessing. Where hours are shown they came off the Google profile on the date "
     "printed beside them and have not been confirmed with the shop, which is why no opening-hours "
     "markup is emitted for any listing."),
    ("What a failed check does and does not prove",
     "A site that returned no answer is reported as exactly that, with the date. A site that "
     "refused our automated request is reported as refusing an automated request, because that is "
     "usually a bot filter and the page is very likely fine in a browser. Neither is described as "
     "broken."),
    ("Who was left off, and why",
     "{excluded} of the {harvested} harvested records are not rendered. None was deleted: each "
     "carries a written reason in the data file, and the full list is published in "
     "reports/exclusions.md. Most were the local pack resolving a town name to the wrong state or "
     "the wrong county."),
)

FAQ = (
    ("Is this the Chamber of Commerce?",
     "No. Upper Cumberland Auto is published by Barnraised, an independent studio. The Overton "
     "County Chamber's own site had no working business directory when this was built, and the "
     "national sites with chamber-sounding domain names are not chambers either."),
    ("How do I get my shop added, changed or removed?",
     "Email the address in the corrections section. Listing is free, removal is free, and neither "
     "one costs or earns anybody anything. A correction is checked against a primary source before "
     "the public record changes."),
    ("Why is there no rating or ranking?",
     "Because we have not driven a car into any of these shops. The only quality signal in the "
     "data is a Google review count harvested on a single day, and turning that into a rank would "
     "dress somebody else's snapshot up as our judgement."),
    ("Why does a shop I know is open say 'no website'?",
     "That flag means no web address of its own, not closed and not unreachable. Most of the "
     "businesses marked this way are busy and well reviewed. It is a note about the internet, not "
     "about the shop."),
    ("What counts as being in the Upper Cumberland here?",
     "A physical service address in Overton, Putnam, Fentress, Clay, Pickett or Jackson County, "
     "Tennessee. A mobile mechanic qualifies if it is based in one of the six and publishes a "
     "service area. A shop twenty miles outside the line does not get in because a customer might "
     "drive to it."),
    ("Is the roster finished?",
     "No. It is a floor, not a finding. The query grid missed roads that no local pack returns, "
     "Jackson County came back nearly empty, and the towing sweep is known to be short. Additions "
     "are welcome and cost nothing."),
)

# Inline SVG rather than a photograph. A stock picture of "a garage" would be a
# photograph of a business that is not on this list, on a page whose entire
# claim is that nothing here is faked. What it draws is a wheel section, a
# tread band, and the six counties as tiles with the flagship filled.
HERO_SVG = """<svg class="hero-art" viewBox="0 0 660 220" role="img"
     aria-label="Diagram of a wheel and tire section, a tread band, and the six Upper Cumberland counties drawn as tiles with the flagship county filled"
     preserveAspectRatio="xMidYMid meet" focusable="false">
  <defs>
    <pattern id="grit" width="14" height="14" patternUnits="userSpaceOnUse">
      <circle cx="7" cy="7" r="1.2" fill="currentColor" opacity=".14"/>
    </pattern>
  </defs>
  <rect width="660" height="220" fill="url(#grit)"/>

  <!-- wheel: tire carcass, rim, hub, five lugs -->
  <g transform="translate(112,110)">
    <circle r="86" fill="none" stroke="currentColor" stroke-width="26" opacity=".92"/>
    <circle r="86" fill="none" stroke="var(--color-accent)" stroke-width="3"/>
    <circle r="60" fill="none" stroke="var(--color-accent)" stroke-width="7"/>
    <circle r="20" fill="var(--color-accent)"/>
    <g fill="currentColor">
      <circle cx="0" cy="-38" r="6"/>
      <circle cx="36" cy="-12" r="6"/>
      <circle cx="22" cy="31" r="6"/>
      <circle cx="-22" cy="31" r="6"/>
      <circle cx="-36" cy="-12" r="6"/>
    </g>
  </g>

  <!-- tread band -->
  <g transform="translate(232,60)" stroke="currentColor" fill="none" stroke-width="7" opacity=".55">
    <path d="M0 0 L22 22 L0 44"/><path d="M34 0 L56 22 L34 44"/><path d="M68 0 L90 22 L68 44"/>
    <path d="M102 0 L124 22 L102 44"/><path d="M136 0 L158 22 L136 44"/>
  </g>
  <g transform="translate(232,124)" stroke="currentColor" fill="none" stroke-width="7" opacity=".3">
    <path d="M0 0 L22 22 L0 44"/><path d="M34 0 L56 22 L34 44"/><path d="M68 0 L90 22 L68 44"/>
    <path d="M102 0 L124 22 L102 44"/><path d="M136 0 L158 22 L136 44"/>
  </g>

  <!-- six counties, flagship filled -->
  <g transform="translate(430,52)" stroke="var(--color-accent)" stroke-width="3">
    <rect x="0" y="0" width="66" height="52" fill="var(--color-accent)"/>
    <rect x="76" y="0" width="66" height="52" fill="none"/>
    <rect x="152" y="0" width="66" height="52" fill="none"/>
    <rect x="0" y="64" width="66" height="52" fill="none"/>
    <rect x="76" y="64" width="66" height="52" fill="none"/>
    <rect x="152" y="64" width="66" height="52" fill="none"/>
  </g>
</svg>"""


def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def clean_address(raw):
    """Trim the harvest's locale artefacts without touching the street line.

    One record came back with a Thai-script rendering of 'United States' welded
    onto the end of the address. Trailing non-ASCII words are cut, and the
    country is dropped because every business on this page is in Tennessee.
    """
    if not raw:
        return None
    text = str(raw).strip()
    text = re.sub(r"(?:\s+[^\x00-\x7F]\S*)+\s*$", "", text).strip()
    text = re.sub(r",\s*(?:United States|USA|US)\s*$", "", text, flags=re.I).strip()
    return text.rstrip(",").strip() or None


ADDRESS_TOWN = re.compile(r",\s*([A-Za-z][A-Za-z .'\-]+),\s*TN\s*\d{5}\s*$")


def town(record) -> str:
    """The town this roster stands behind, in the same order as the county.

    A hand correction from the shop's own site wins, then the town inside the
    harvested street address, then the city the local pack filed it under. The
    last of those is the least reliable: the sweep filed a shop on Palestine
    Road in Allons under Livingston, and a Jamestown diesel shop under
    Livingston too.
    """
    if record.get("town"):
        return record["town"]
    match = ADDRESS_TOWN.search(clean_address(record.get("address")) or "")
    return match.group(1).strip() if match else record["city"]


def phone_pretty(raw):
    digits = phone_digits(raw)
    if len(digits) != 10:
        return None, None
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}", digits


def host_of(url):
    return re.sub(r"^https?://(?:www\.)?", "", url or "").rstrip("/").split("/")[0]


def anchor(record) -> str:
    return record["id"]


def category_labels(record) -> list[str]:
    return [CATEGORY_LABELS[key] for key in record["categories_hand"]]


def schema_type(record) -> str:
    return CATEGORY_SCHEMA[record["categories_hand"][0]]


def hours_block(record) -> str:
    hours = record.get("hours")
    if not hours:
        return ('<p class="facts quiet"><span class="role">Hours</span>'
                '<span>Hours not verified.</span></p>')
    rows = "".join(
        f"<dt>{esc(day)}</dt><dd>{esc(value)}</dd>" for day, value in hours.items()
    )
    checked = record.get("hours_checked")
    return f"""<details class="hours-table">
          <summary>Hours as published on the Google profile</summary>
          <dl class="hours-list">{rows}</dl>
          <p class="no-js-note">Read from the Google Business Profile on {esc(checked)}. Not confirmed with the shop.</p>
        </details>"""


INSECURE_MARKER = '<span class="insecure">http, not encrypted</span>'


def outbound(url: str) -> str:
    """One link out, with the scheme stated when it is not encrypted.

    Every external href on this page goes through here, so "is this link
    https, and if not does it say so" is a property of one function rather
    than of however many call sites remembered.
    """
    marker = INSECURE_MARKER if url.startswith("http://") else ""
    return (f'<a href="{esc(url)}" rel="noopener nofollow external" target="_blank">'
            f'{esc(host_of(url))}</a>{marker}')


def checked_on(record) -> str:
    return record.get("checked_at") or record["panel_checked"]


def website_row(record) -> str:
    gap = record["web_gap_hand"]
    site = record.get("site")
    if gap is None and site:
        return f'<dt>Website</dt><dd>{outbound(site)}</dd>'
    label = WEB_GAP_LABELS[gap]
    if gap == "no-website" or not site:
        return f'<dt>Website</dt><dd><span class="flag">{esc(label)}</span></dd>'
    if gap in LINKABLE_GAPS:
        return (f'<dt>Website</dt><dd><span class="flag">{esc(label)}</span> '
                f'{outbound(site)}</dd>')
    if gap == "dead-site":
        tail = f"no response when checked on {checked_on(record)}"
    else:
        tail = "recorded on the Google profile, not linked from here"
    return (f'<dt>Website</dt><dd><span class="flag">{esc(label)}</span> '
            f'<span class="quiet">{esc(host_of(site))} — {esc(tail)}</span></dd>')


def sources_row(record) -> str:
    if not record["sources"]:
        return ""
    items = " ".join(
        f'{outbound(s["url"])} <span class="quiet">({esc(s["checked"])}, '
        f'{esc(s["supports"])})</span>'
        for s in record["sources"]
    )
    return f'<dt>Sources</dt><dd>{items}</dd>'


def listing_block(record) -> str:
    pretty, digits = phone_pretty(record.get("phone"))
    address = clean_address(record.get("address"))
    gap = record["web_gap_hand"]
    flags = ""
    if record["brand_type"] == "chain":
        flags += '<span class="tag">Chain or multi-location brand</span>'
    if gap:
        flags += f'<span class="flag">{esc(WEB_GAP_LABELS[gap])}</span>'
    chips = "".join(f'<li class="chip">{esc(label)}</li>' for label in category_labels(record))
    notes = ""
    if record["notes"]:
        notes = ('<ul class="notes">'
                 + "".join(f"<li>{esc(note)}</li>" for note in record["notes"])
                 + "</ul>")
    tel = (f'<a class="act act-tel" href="tel:+1{digits}">{esc(pretty)}</a>' if pretty
           else '<span class="act act-none">No phone on the profile</span>')
    search_key = " ".join(filter(None, [
        record["name"], town(record), record["city"], record["county"], address or "",
        " ".join(category_labels(record)),
    ]))
    reviews = (f'{record["reviews"]:,} reviews, {record["rating"]} average'
               if record["reviews"] else "no reviews recorded")
    return f"""        <article class="listing" id="{esc(anchor(record))}" data-county="{esc(record['county'])}" data-categories="{esc(' '.join(record['categories_hand']))}" data-gap="{'1' if gap else ''}" data-search="{esc(search_key)}">
          <p class="eyebrow">{esc(', '.join(category_labels(record)))}{flags}</p>
          <h4 class="listing-name">{esc(record['name'])}</h4>
          <p class="listing-where">{esc(town(record))}, {esc(record['county'])} County</p>
          <p class="blurb">{esc(record['blurb'])}</p>
          {notes}
          <ul class="chips">{chips}</ul>
          <dl class="facts">
            <dt>Address</dt><dd>{esc(address) if address else '<span class="quiet">No street address on the profile</span>'}</dd>
            {website_row(record)}
            <dt>Google profile</dt><dd class="quiet">{esc(reviews)}, read {esc(record['panel_checked'])}. Not a rating by this directory.</dd>
            {sources_row(record)}
          </dl>
          {hours_block(record)}
          <p class="actions">{tel}</p>
        </article>"""


def county_block(county: str, records: list) -> str:
    gaps = sum(1 for r in records if r["web_gap_hand"])
    flagship = county == FLAGSHIP_COUNTY
    note = ""
    if flagship:
        note = (f'<p class="flagship-note">Overton County is the flagship of this roster and is '
                f'listed first. {gaps} of these {len(records)} businesses have no web address of '
                f'their own — which is the entire reason this page exists.</p>')
    entries = "\n".join(listing_block(record) for record in records)
    return f"""      <section class="county-block{' is-flagship' if flagship else ''}" id="{esc(county.lower())}-county" aria-labelledby="{esc(county.lower())}-county-title">
        <div class="county-head">
          <h3 id="{esc(county.lower())}-county-title">{esc(county)} County</h3>
          <p class="tally">{len(records)} listed · {gaps} with no web address of their own</p>
        </div>
        {note}
        <div class="listings">
{entries}
        </div>
      </section>"""


EXCLUSIONS_PREAMBLE = """# Exclusions

Twelve of the {harvested} harvested records are not rendered on the site. None of them was
deleted. Each one is still in `data/roster.json` exactly as it was harvested, with an
`excluded` field carrying the reason, and the generator filters on that field at render
time. Anyone can diff the file against the original sweep and see that the row count never
moved.

Four things caused all twelve.

**The local pack resolved a town name to the wrong place.** Six of the twelve. The Upper
Cumberland shares town names with the rest of the country and with the rest of Tennessee,
and a query for `auto repair|Celina` will happily return Celina, Texas. Monroe is worse: it
is both a community in Overton County and a county in East Tennessee, so two separate
records came back from Madisonville and Sweetwater. In every one of these cases the
harvested address disagrees with the town the query asked for, and the address is the thing
that can be checked.

**The business is not an auto business.** Two. One is the Town of Monterey's farmers-market
page, which a tire query resolved to. One is a parts counter, which the scope rule excludes
alongside dealerships, car washes, detailers, salvage and rental.

**Nothing in the record can be verified.** Two, both mobile or profile-only operators with
no street address. One of them was settled by fetching the business's own website, which
turned out to describe a company based 140 miles away.

**It is the same business twice.** One duplicate, kept as the record that carries the
address and the phone number.

## Chains

The harvest set `is_chain` to `false` on all {harvested} records, which is wrong. Three
listed businesses are locations of a chain or multi-location brand:

{chain_list}

They stay listed, because a franchise oil-change bay on West Main is a real place a real
person can drive to, and leaving it out would make the roster less complete without making
it more honest. What they do not get is to look like independent local shops: each carries
a "Chain or multi-location brand" tag on its entry, and the link on each one goes to a
corporate location page rather than to anything the local store controls. That distinction
matters for the only thing this site is for — a shop owner reading it should be able to see
instantly which of their neighbours are actually their neighbours.

One more, Christian Brothers Automotive, is a franchise too, but it is excluded on
geography rather than on brand and would have been excluded if it were a one-man garage.

## Judgement calls that went the other way

Three records could reasonably have been excluded and were not.

- **Johnson's Auto Parts & Shop**, Gainesboro. The name reads as both a parts counter and a
  repair shop. It has no Google category to settle it and it surfaced on an auto repair
  query. It is one of only two Jackson County records in the entire sweep, so it is listed
  with the ambiguity printed on the entry rather than dropped.
- **Uncle E's Cycle's and Automotive Repair**, Gainesboro. Google files it as a motorcycle
  shop; the business name says automotive repair as well. Listed, with both readings shown.
- **Kent's Wholesale Tire**. The Google category places it in Clarkrange (Fentress County)
  and the harvested city says Rickman (Overton County). Both are in scope, so the record
  stays under the city it was harvested with and the conflict is printed on the entry
  instead of being quietly resolved in Overton's favour.

Two records were corrected rather than excluded, because the business's own website
disagreed with the harvest about which town it is in: Doug Freeman Tire (harvested Rickman,
own site says Cookeville) and Hales Repair Group (harvested Gainesboro, own site says
Cookeville). Both moved to Putnam County. A third, Independent Auto and Diesel Repair,
carried the Overton flag while its own site gives a Jamestown address, so it is listed under
Fentress. The site's Overton County count is {overton} rather than the {overton_naive} the
raw `in_overton` flags would have produced, and the difference is entirely these
corrections.

## The excluded records

"""


def write_exclusions_report(records, rows, dropped) -> Path:
    chains = [r for r in rows if r["brand_type"] == "chain"]
    naive_overton = sum(1 for r in records if "excluded" not in r and r.get("in_overton"))
    lines = [EXCLUSIONS_PREAMBLE.format(
        harvested=len(records),
        chain_list="\n".join(
            f"- **{r['name']}**, {town(r)} — {host_of(r['site']) if r['site'] else 'no site'}"
            for r in sorted(chains, key=lambda r: r["name"].lower())
        ),
        overton=sum(1 for r in rows if r["county"] == FLAGSHIP_COUNTY),
        overton_naive=naive_overton,
    )]
    for record in dropped:
        lines.append(f"### {record['name']}")
        lines.append("")
        lines.append(f"`{record['id']}` · harvested as {record['city']} · "
                     f"found by `{record['found_by']}` · "
                     f"{record['reviews']:,} Google reviews read {record['panel_checked']}")
        lines.append("")
        lines.append(record["excluded"])
        lines.append("")
    lines.append(f"---")
    lines.append("")
    lines.append(f"{len(records)} harvested · {len(rows)} listed · {len(dropped)} excluded · "
                 f"0 deleted. Regenerate with `python scripts/build.py`.")
    path = REPORTS / "exclusions.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return path


def build():
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    records = validate_roster(payload)
    rows = listed(records)
    dropped = excluded(records)

    by_county = {county: [r for r in rows if r["county"] == county] for county in COUNTIES}
    county_counts = {county: len(items) for county, items in by_county.items()}
    category_counts = Counter(c for r in rows for c in r["categories_hand"])
    gap_counts = Counter(r["web_gap_hand"] for r in rows if r["web_gap_hand"])
    total_gaps = sum(gap_counts.values())
    overton = by_county[FLAGSHIP_COUNTY]
    overton_gaps = sum(1 for r in overton if r["web_gap_hand"])
    towns = sorted({town(r) for r in rows})
    sourced = sum(1 for r in rows if r["sources"])
    no_hours = sum(1 for r in rows if not r.get("hours"))
    towing = [r for r in rows if "towing" in r["categories_hand"]]
    chains = [r for r in rows if r["brand_type"] == "chain"]

    facts = {
        "listed": len(rows), "excluded": len(dropped), "harvested": len(records),
        "queries": len(payload.get("_done", [])), "harvest": HARVEST,
        "sourced": sourced, "no_hours": no_hours,
    }

    county_picks = "".join(
        f'<li><a href="#{county.lower()}-county">{esc(county)} County'
        f'<span class="tally">{county_counts[county]}</span></a></li>'
        for county in COUNTIES
    )
    # These carry the filter state in the query string, which the script reads
    # on load. With scripting off the link still lands on the roster, which is
    # complete anyway — it just does not narrow.
    category_picks = "".join(
        f'<li><a href="?category={esc(key)}#directory">{esc(label)}'
        f'<span class="tally">{category_counts[key]}</span></a></li>'
        for key, label, _ in CATEGORIES
    )
    toc = (
        ("The roster", "directory"),
        ("Towing and wrecker services", "towing"),
        ("Businesses with no web address", "web-gaps"),
        ("How this roster was built", "method"),
        ("What is in scope", "scope"),
        ("Corrections and removals", "corrections"),
        ("Questions", "faq"),
    )
    toc_html = "".join(f'<li><a href="#{i}">{esc(t)}</a></li>' for t, i in toc)

    county_opts = "".join(
        f'<option value="{esc(c)}">{esc(c)} County ({county_counts[c]})</option>'
        for c in COUNTIES
    )
    category_opts = "".join(
        f'<option value="{esc(k)}">{esc(label)} ({category_counts[k]})</option>'
        for k, label, _ in CATEGORIES
    )
    blocks = "\n".join(county_block(c, by_county[c]) for c in COUNTIES)

    towing_rows = "".join(
        f"""<tr>
          <th scope="row"><a href="#{esc(anchor(r))}">{esc(r['name'])}</a></th>
          <td>{esc(town(r))}<span class="td-sub">{esc(r['county'])} County</span></td>
          <td>{esc(phone_pretty(r.get('phone'))[0] or 'No phone on the profile')}</td>
          <td>{esc(WEB_GAP_LABELS[r['web_gap_hand']] if r['web_gap_hand'] else host_of(r['site']))}</td>
        </tr>""" for r in sorted(towing, key=lambda r: r["name"].lower())
    )
    gap_rows = "".join(
        f"""<tr>
          <th scope="row"><a href="#{esc(anchor(r))}">{esc(r['name'])}</a></th>
          <td>{esc(town(r))}<span class="td-sub">{esc(r['county'])} County</span></td>
          <td>{esc(', '.join(category_labels(r)))}</td>
          <td>{esc(WEB_GAP_LABELS[r['web_gap_hand']])}</td>
        </tr>""" for r in sorted((r for r in rows if r["web_gap_hand"]),
                                 key=lambda r: (COUNTIES.index(r["county"]), r["name"].lower()))
    )
    gap_breakdown = "".join(
        f'<li>{esc(WEB_GAP_LABELS[key])}: <strong>{count}</strong></li>'
        for key, count in sorted(gap_counts.items(), key=lambda kv: -kv[1])
    )
    method_rows = "".join(
        f'<tr><th scope="row">{esc(title)}</th><td>{esc(body.format(**facts))}</td></tr>'
        for title, body in METHOD
    )
    faq_html = "".join(
        f'<h3 class="faq-q">{esc(q)}</h3><p>{esc(a)}</p>' for q, a in FAQ
    )
    network_html = "".join(
        f'<li><a href="{esc(url)}" rel="external">{esc(label)}</a></li>'
        for label, url in SITE_CONFIG.network_sites
    )

    # ---- structured data -------------------------------------------------
    def item_node(record):
        address = clean_address(record.get("address"))
        node = {
            "@type": schema_type(record),
            "@id": f"{CANONICAL}#{anchor(record)}",
            "name": record["name"],
            "url": (record["site"] if record["web_gap_hand"] is None and record["site"]
                    else f"{CANONICAL}#{anchor(record)}"),
            "address": {
                "@type": "PostalAddress",
                "addressLocality": town(record),
                "addressRegion": "TN",
                "addressCountry": "US",
                **({"streetAddress": address} if address else {}),
            },
            "areaServed": {"@type": "AdministrativeArea",
                           "name": f"{record['county']} County, Tennessee"},
        }
        if record.get("phone"):
            node["telephone"] = record["phone"]
        if record["web_gap_hand"] in {"facebook-only", "rented-subdomain"} and record["site"]:
            node["sameAs"] = [record["site"]]
        if len(record["categories_hand"]) > 1:
            node["additionalType"] = [CATEGORY_SCHEMA[k] for k in record["categories_hand"][1:]]
        return node

    graph = [
        {
            "@type": "WebSite",
            "@id": f"{CANONICAL}#website",
            "url": CANONICAL,
            "name": SITE_CONFIG.name,
            "description": SITE_CONFIG.description,
            "inLanguage": SITE_CONFIG.locale,
            "publisher": {"@id": f"{CANONICAL}#publisher"},
        },
        {
            "@type": "Organization",
            "@id": f"{CANONICAL}#publisher",
            "name": SITE_CONFIG.publisher_name,
            "url": SITE_CONFIG.publisher_url,
            "email": SITE_CONFIG.correction_email,
        },
        {
            "@type": "WebPage",
            "@id": CANONICAL,
            "url": CANONICAL,
            "name": SITE_CONFIG.title,
            "description": SITE_CONFIG.description,
            "inLanguage": SITE_CONFIG.locale,
            "datePublished": SITE_CONFIG.date_published,
            "dateModified": SITE_CONFIG.date_modified,
            "isPartOf": {"@id": f"{CANONICAL}#website"},
            "publisher": {"@id": f"{CANONICAL}#publisher"},
            "mainEntity": {"@id": f"{CANONICAL}#roster"},
            "about": {"@type": "Thing",
                      "name": "Auto repair, tire, body and towing businesses of the Upper Cumberland"},
            "spatialCoverage": [
                {"@type": "AdministrativeArea", "name": f"{county} County, Tennessee"}
                for county in COUNTIES
            ],
        },
        {
            "@type": "BreadcrumbList",
            "@id": f"{CANONICAL}#breadcrumbs",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": SITE_CONFIG.name, "item": CANONICAL},
                {"@type": "ListItem", "position": 2, "name": "The roster",
                 "item": f"{CANONICAL}#directory"},
            ],
        },
        {
            "@type": "ItemList",
            "@id": f"{CANONICAL}#roster",
            "name": "Upper Cumberland auto repair, tire, body and towing businesses",
            "description": (
                "An unranked roster of auto businesses with a physical service address in "
                "Overton, Putnam, Fentress, Clay, Pickett or Jackson County, Tennessee."
            ),
            "numberOfItems": len(rows),
            "itemListOrder": "https://schema.org/ItemListUnordered",
            "itemListElement": [{"@type": "ListItem", "item": item_node(r)} for r in rows],
        },
        {
            "@type": "FAQPage",
            "@id": f"{CANONICAL}#faq",
            "mainEntity": [
                {"@type": "Question", "name": q,
                 "acceptedAnswer": {"@type": "Answer", "text": a}}
                for q, a in FAQ
            ],
        },
    ]
    ld = {"@context": "https://schema.org", "@graph": graph}

    tokens_css = TOKENS.read_text(encoding="utf-8")
    components_css = COMPONENTS.read_text(encoding="utf-8")
    directory_js = SCRIPT.read_text(encoding="utf-8")

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(SITE_CONFIG.title)}</title>
<meta name="description" content="{esc(SITE_CONFIG.description)}">
<link rel="canonical" href="{CANONICAL}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{esc(SITE_CONFIG.name)}">
<meta property="og:title" content="{esc(SITE_CONFIG.name)}">
<meta property="og:description" content="{esc(SITE_CONFIG.social_description)}">
<meta property="og:url" content="{CANONICAL}">
<meta property="og:locale" content="en_US">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{esc(SITE_CONFIG.name)}">
<meta name="twitter:description" content="{esc(SITE_CONFIG.social_description)}">
<meta name="theme-color" content="{SITE_CONFIG.theme_color}">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">
<style>
{tokens_css}
</style>
<style>
{components_css}
</style>
</head>
<body>
<a class="skip" href="#directory">Skip to the roster</a>

<header class="appbar" id="top">
  <div class="wrap-wide appbar-inner">
    <a class="brand" href="#top">{esc(SITE_CONFIG.name)}<span>Overton · Putnam · Fentress · Clay · Pickett · Jackson</span></a>
    <nav class="primary-nav" aria-label="Primary">
      <a href="#overton-county">Overton County</a>
      <a href="#directory">The roster</a>
      <a href="#web-gaps">No web address</a>
      <a href="#method">Method</a>
      <a href="#corrections">Corrections</a>
    </nav>
  </div>
</header>

<main>
  <section class="wrap-wide intro" aria-labelledby="page-title">
    <div class="intro-copy">
      <p class="kicker">Upper Cumberland, Tennessee · Auto repair, tire, body, diesel, transmission, towing</p>
      <h1 id="page-title">{esc(SITE_CONFIG.h1)}</h1>
      <p class="standfirst">{len(rows)} businesses across six counties, {county_counts[FLAGSHIP_COUNTY]} of them in
      Overton County. Every one is here because a harvested record survived a hand check, and every
      claim on this page can be traced back to that record or to a page somebody fetched and dated.
      {total_gaps} of them have no web address of their own.</p>
      <div class="byline">
        <div class="who"><span class="role">Roster</span><span class="name">{len(rows)} businesses, {len(towns)} towns</span></div>
        <div class="who"><span class="role">Records checked</span><span class="name">{esc(UPDATED)}</span></div>
        <div class="who"><span class="role">Harvested</span><span class="name">{esc(HARVEST)}</span></div>
        <div class="who"><span class="role">Published by</span><a class="name" href="{SITE_CONFIG.publisher_url}" rel="publisher external">Barnraised</a></div>
      </div>
      <p class="disclosure">{DISCLOSURE}</p>
    </div>
    <div class="intro-art">{HERO_SVG}</div>
  </section>

  <div class="wrap-wide orientation">
    <section aria-labelledby="jump-title">
      <h2 id="jump-title">Jump to a county</h2>
      <p class="lede">Overton County leads because this directory is Overton-flagged by design. The
      other five are in the order the counties ring it.</p>
      <ul class="picks">{county_picks}</ul>
      <h2 id="cats-title">By category</h2>
      <p class="lede">A business can sit in more than one, so these do not add up to {len(rows)}.</p>
      <ul class="picks">{category_picks}</ul>
    </section>
    <section aria-labelledby="contents-title">
      <h2 id="contents-title">On this page</h2>
      <ul class="toc">{toc_html}</ul>
    </section>
  </div>

  <div class="wrap-wide directory-shell" id="directory">
    <aside class="toolbar" id="toolbar" aria-labelledby="filter-title" hidden>
      <div class="toolbar-inner">
        <h2 id="filter-title">Narrow the roster</h2>
        <div class="field">
          <label for="f-county">County</label>
          <select id="f-county"><option value="">All six counties ({len(rows)})</option>{county_opts}</select>
        </div>
        <div class="field">
          <label for="f-category">Category</label>
          <select id="f-category"><option value="">Any category</option>{category_opts}</select>
        </div>
        <div class="field">
          <label for="f-text">Search</label>
          <input id="f-text" type="search" placeholder="Name, town or street" autocomplete="off">
        </div>
        <label class="check" for="f-gap">
          <input type="checkbox" id="f-gap"> Only businesses with no web address
        </label>
        <button id="f-reset" class="btn" type="button">Reset</button>
        <p id="count" role="status" aria-live="polite">Showing all {len(rows)} businesses</p>
        <p class="filter-error" id="filter-error" role="alert" hidden>Filters could not be applied, so every business is shown.</p>
      </div>
    </aside>

    <section id="roster" aria-labelledby="roster-title">
      <h2 id="roster-title">The roster</h2>
      <p class="lede">Alphabetical inside each county. Every entry carries its address, its phone
      number if the profile had one, what the shop's web presence actually is, and the Google
      figures with the date they were read. Filtering is optional: this list is complete in the page
      whether or not scripting runs.</p>
{blocks}
      <p class="empty" id="empty">No business matches those filters.
        <button class="btn" id="empty-reset" type="button">Clear filters</button></p>
      <p class="to-top-row"><a class="to-top" href="#directory">Back to the top of the roster</a></p>
    </section>
  </div>

  <section class="wrap-wide" id="towing">
    <h2>Towing and wrecker services</h2>
    <p class="lede">{len(towing)} operators, listed because a roster of auto businesses that leaves
    out the wrecker is incomplete. There is no towing guide here and there will not be one: a
    breakdown is a phone call, not a browsing session. The known gap is that this sweep did not
    catch every wrecker in six counties, and the ones it missed are worth adding.</p>
    <div class="table-scroll">
      <table>
        <caption>Towing and wrecker operators in the roster, alphabetical.</caption>
        <thead><tr><th scope="col">Operator</th><th scope="col">Town</th><th scope="col">Phone</th><th scope="col">Web</th></tr></thead>
        <tbody>{towing_rows}</tbody>
      </table>
    </div>
  </section>

  <section class="wrap-wide" id="web-gaps">
    <h2>Businesses with no web address of their own</h2>
    <p class="lede">{total_gaps} of the {len(rows)} listed businesses, and {overton_gaps} of the
    {len(overton)} in Overton County. This is the finding, not a sales list: a shop with no site is
    usually busy, well reviewed and entirely fine. It just cannot be found by anybody who starts
    with a search box instead of a neighbour.</p>
    <ul class="method-list">{gap_breakdown}</ul>
    <p>A Facebook page, a builder subdomain, a third-party listings page and a parked domain all
    count as gaps here for the same reason: none of them is an address the business controls. Where
    the harvest recorded one of those as "has a site", the entry says so on its own line rather than
    quietly disagreeing with the file.</p>
    <div class="table-scroll">
      <table>
        <caption>Every listed business with no web address of its own, by county.</caption>
        <thead><tr><th scope="col">Business</th><th scope="col">Town</th><th scope="col">Category</th><th scope="col">What it has instead</th></tr></thead>
        <tbody>{gap_rows}</tbody>
      </table>
    </div>
  </section>

  <section class="wrap-wide" id="method">
    <h2>How this roster was built</h2>
    <p class="lede">{len(records)} records were harvested. {len(rows)} are listed, {len(dropped)}
    are not, and none was deleted. {len(chains)} listed businesses are locations of a chain or
    multi-location brand and are labelled as such, because presenting a franchise bay as an
    independent local shop would be the same kind of lie as inventing a founding year.</p>
    <div class="table-scroll">
      <table>
        <thead><tr><th scope="col">Decision</th><th scope="col">What it meant in practice</th></tr></thead>
        <tbody>{method_rows}</tbody>
      </table>
    </div>
  </section>

  <section class="wrap" id="scope">
    <h2>What is in scope</h2>
    <p>A business belongs here if its physical service address is in Overton, Putnam, Fentress,
    Clay, Pickett or Jackson County, Tennessee. Mobile mechanics belong if they are based in one of
    the six and publish a service area. A shop twenty miles outside the line does not get in because
    a customer might drive to it.</p>
    <p>Listed: general auto repair, tire, auto body and collision, diesel repair, transmission
    repair, and towing or wrecker service. Not listed: dealerships, parts counters, car washes,
    detailers, salvage yards and rental.</p>
    <p>Where the harvest and a business's own website disagreed about which town a shop is in, the
    business's own website won and the entry says so. Where the harvest disagreed with itself and
    nothing could settle it, both readings are printed and neither is resolved.</p>
  </section>

  <section class="wrap" id="corrections">
    <h2>Corrections and removals</h2>
    <p>Listing is free. Removal is free. Neither costs or earns anybody anything, and no position on
    this page has ever been for sale.</p>
    <p>If an entry is wrong — a phone number, an address, a county, a website that exists and is not
    shown here — email <span class="email-contact">steve<span>@</span>barnraised.design</span> and it
    gets checked against a primary source before the public record changes. If you own one of the
    businesses above and want it gone, say so and it goes, with no argument and no follow-up.</p>
    <p>Records were last checked on {esc(UPDATED)}. The underlying harvest ran on {esc(HARVEST)},
    and every Google figure on this page dates from that sweep rather than from today.</p>
  </section>

  <section class="wrap prose" id="faq">
    <h2>Questions</h2>
{faq_html}
  </section>
</main>

<footer>
  <div class="wrap-wide">
    <ul class="network">{network_html}</ul>
    <p><strong>{esc(SITE_CONFIG.name)}</strong> — an unranked roster of the auto repair, tire, body,
    diesel, transmission and towing businesses of Overton, Putnam, Fentress, Clay, Pickett and
    Jackson counties, Tennessee. Researched and published by
    <a href="{SITE_CONFIG.publisher_url}" rel="publisher external">Barnraised</a>. No listing on this
    page was purchased and no listed business is affiliated with this directory. Last checked
    {esc(UPDATED)}.</p>
  </div>
</footer>

<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<script>
{directory_js}
</script>
</body>
</html>
"""

    # Clear the contents rather than removing dist itself. On Windows, deleting a
    # directory fails with WinError 32 whenever anything holds a handle on it --
    # a preview server, Explorer, or the search indexer -- while unlinking the
    # files inside always works. Removing the directory buys nothing here.
    DIST.mkdir(parents=True, exist_ok=True)
    for entry in DIST.iterdir():
        if entry.is_dir():
            shutil.rmtree(entry, ignore_errors=True)
        else:
            entry.unlink(missing_ok=True)
    OUT.write_text(page, encoding="utf-8", newline="\n")
    (DIST / "robots.txt").write_text(
        "# Policy: allow indexing and cited AI answers; reserve model-training rights.\n"
        "User-agent: *\n"
        "Content-Signal: search=yes, ai-input=yes, ai-train=no\n"
        "Allow: /\n\n"
        f"Sitemap: {SITE_CONFIG.url('sitemap.xml')}\n",
        encoding="utf-8", newline="\n",
    )
    urlset = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    url = ET.SubElement(urlset, "url")
    ET.SubElement(url, "loc").text = CANONICAL
    ET.SubElement(url, "lastmod").text = SITE_CONFIG.date_modified
    ET.SubElement(url, "changefreq").text = "monthly"
    ET.indent(urlset, space="  ")
    ET.ElementTree(urlset).write(DIST / "sitemap.xml", encoding="utf-8", xml_declaration=True)
    with (DIST / "sitemap.xml").open("ab") as handle:
        handle.write(b"\n")
    write_exclusions_report(records, rows, dropped)

    return OUT, len(page.encode("utf-8")), len(rows), len(dropped)


if __name__ == "__main__":
    path, size, kept, dropped = build()
    print(f"wrote {path} ({size:,} bytes, {kept} listed, {dropped} excluded)")
