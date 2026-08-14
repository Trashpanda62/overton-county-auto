#!/usr/bin/env python3
"""Apply the hand pass to data/roster.json. Idempotent; already applied.

The harvest is a Google local-pack sweep. It got a lot right and a few things
badly wrong, and none of it can be deleted, because "we deleted the rows that
embarrassed us" is not a verification method. So every judgement call lives
here as data written onto the record:

  excluded          why a record is not rendered. Nothing is removed.
  county            the county this roster stands behind, re-derived from the
                    address town, or from the shop's own website where one was
                    fetched and disagreed with the harvest.
  county_source     how that county was arrived at.
  categories_hand   hand-assigned category keys. The harvest's `categories`
                    field is the query that surfaced the business, not an
                    assessment of what the shop does, and is left untouched.
  brand_type        independent / chain. The harvest set is_chain to false on
                    all 71 records, which is wrong for at least four of them.
  web_gap_hand      re-derived from the recorded host: a facebook.com URL is a
                    Facebook page whatever the harvest called it, an edan.io or
                    lovable.app host is rented, and a domain-for-sale parking
                    page is not a business website.
  blurb             one hand-written entry. Never templated, never padded to a
                    matching length, and never asserting anything the roster or
                    a recorded source does not support.
  sources           pages fetched by hand on 2026-08-14, with what each one is
                    being used to support. A blurb may only make a capability,
                    certification or ownership claim if it points at one.
  notes             data caveats that belong on the public listing rather than
                    in a private file.

Run again after editing the tables below: python scripts/annotate_roster.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "data" / "roster.json"
FETCHED = "2026-08-14"

# --------------------------------------------------------------------------
# Excluded. Twelve records, each with the reason it is not rendered.
# --------------------------------------------------------------------------
EXCLUDED = {
    "philly-auto": (
        "Unverifiable. The record carries no address, no phone and no website — nothing in it "
        "can be checked against anything. Its 2,000 review count is also an order of magnitude "
        "above every other Byrdstown record, which is what a mis-resolved local pack looks like. "
        "The spec already flagged this business's knowledge-panel lookup as failed."
    ),
    "christian-brothers-automotive-celina": (
        "Out of region. The address is 4075 S Preston Rd, Celina, TX 75009 and the phone is a "
        "945 area code; Google's own category line reads 'Auto repair shop in Celina, Texas'. "
        "The Celina query pulled back the Texas town of the same name."
    ),
    "rush-towing-service": (
        "Duplicate. Same business and same host as rush-towing-llc, which is the record that "
        "carries the street address and the phone number. This one has neither."
    ),
    "joshua-tire-sales": (
        "Out of region. The address is 1276 TN-113, White Pine, TN 37890 — Jefferson County, "
        "about 150 miles east — with an 865 area code. It was returned by the Hilham tire query."
    ),
    "monterey-market": (
        "Not an auto business. The recorded website is the Town of Monterey's own "
        "'Visit Farmers Market' page. The tire query for Monterey resolved to the town market."
    ),
    "kingdom-mobile-auto-repair": (
        "Out of scope for mobile operators. The record has no address and no phone, and the "
        "shop's own site, fetched 2026-08-14, publishes no service radius and no town list — it "
        "says only that it serves 'the Middle TN area'. The scope rule admits a mobile mechanic "
        "when it is based in one of the six counties and publishes a service radius. This one "
        "clears neither test on the evidence available. One phone call could reinstate it."
    ),
    "joe-automotive-repair": (
        "Out of region. The address is 230b Upton Rd, Sweetwater, TN 37874 with a 423 area code. "
        "The Monroe query matched Monroe County in East Tennessee rather than the Monroe "
        "community in Overton County. The spec lists this business as an Overton prospect; the "
        "harvested address does not support that, and the address is what we can check."
    ),
    "monroe-tire-and-service-inc": (
        "Out of region. Google's category line reads 'Auto repair shop in Madisonville, "
        "Tennessee', the phone is a 423 number and the address is on US-411 — Monroe County, "
        "East Tennessee. Same mis-resolution as the record above."
    ),
    "jackson-motors-body-shop": (
        "Out of region. The address is 63 Oakdale Rd, Lafayette, TN 37083 — Macon County — with "
        "a 615 area code. The harvest flagged it in_overton; its own address does not agree, and "
        "the spec's Overton prospect list inherits the same error."
    ),
    "stuarts-auto-supply": (
        "Out of subject scope. Google's category line reads 'Auto parts store in Byrdstown, "
        "Tennessee'. This directory lists businesses that repair, service or tire a vehicle; it "
        "does not list parts counters, dealerships, car washes, detailers, salvage or rental."
    ),
    "mobile-diesel-mechanic-howells": (
        "Out of region. The recorded website was fetched on 2026-08-14: the business is based in "
        "Clarksville, states a service area of 'All Areas Within 100 Mile Radius of Clarksville, "
        "TN', and lists a second location at Bradyville serving Woodbury, Murfreesboro, Smyrna "
        "and neighbours. It names neither Livingston, nor Overton County, nor the Upper "
        "Cumberland. The Livingston profile is a service-area listing, not a shop here."
    ),
    "monteagle-truck-and-tire": (
        "Out of region. The address is Dixie Lee Ave, Monteagle, TN 37356 — the Cumberland "
        "Plateau above Grundy and Marion counties, roughly 80 miles south. Returned by the "
        "Hilham tire query."
    ),
}

# --------------------------------------------------------------------------
# Kept records. county, county_source, categories, brand, web gap, blurb.
# --------------------------------------------------------------------------
# county_source values:
#   address   the town in the harvested address is in that county
#   city      the record's city field; the address carried no town
#   own-site  the business's own website was fetched and disagreed with the
#             harvest, and the primary source wins
K = {}


def keep(rid, county, county_source, cats, blurb, brand="independent",
         gap="__inherit__", notes=(), sources=(), town=None):
    K[rid] = {
        "county": county, "county_source": county_source, "categories_hand": list(cats),
        "brand_type": brand, "web_gap_hand": gap, "blurb": blurb,
        "notes": list(notes), "sources": list(sources),
    }
    # Only where the harvested city field is wrong and the street address does
    # not carry a town to correct it with. Everything else derives at render.
    if town:
        K[rid]["town"] = town


def src(url, supports):
    return {"url": url, "checked": FETCHED, "supports": supports}


# --- Overton County -------------------------------------------------------
keep("strickland-brothers-10-minute-oil-change", "Overton", "address", ["auto-repair"],
     "A franchise oil-change bay on West Main. The link goes to the chain's Livingston "
     "location page rather than to anything the Livingston store controls.",
     brand="chain")
keep("kent-wholesale-tire", "Overton", "city", ["tire"],
     "The site on this profile sits at kents-wholesale-tire.edan.io — a builder subdomain "
     "rather than a domain the shop owns — and it refused our automated request, which usually "
     "means a bot filter and nothing worse. Google's category line places this one in "
     "Clarkrange; the harvest recorded Rickman, and the address it carries is a Deer Lodge "
     "Highway number that could sit on either side of that line.",
     gap="rented-subdomain",
     notes=["Google's category line says Clarkrange (Fentress County); the harvested city says "
            "Rickman (Overton County). Both are in scope, so the record stays listed under the "
            "city it was harvested with and the conflict is printed rather than resolved."])
keep("waterloo-tire-service", "Overton", "address", ["tire"],
     "West Main Street, Livingston. No website of any kind.")
keep("maynord-bros-automotive", "Overton", "city", ["auto-body"],
     "Listed as a body shop on East Main. The website on its profile was fetched on "
     "2026-08-14 and belongs to Maynord Auto Sales LLC, a Livingston dealer whose menu carries "
     "a Body Shop entry — it is not a standalone body-shop site, and it answers only over "
     "plain http.",
     sources=[src("http://www.maynordautos.com/",
                  "the site is Maynord Auto Sales LLC of Livingston and its menu lists Body Shop")])
keep("floyd-automotive-and-performance", "Overton", "city", ["auto-repair"],
     "Rickman Road. The only web presence on the profile is a Facebook page.")
keep("hwy-tire", "Overton", "address", ["tire", "auto-repair"],
     "Cookeville Highway, Livingston. Google files it under auto repair in Overton County "
     "rather than under tire, so it is listed under both. No website.")
keep("woolbright-auto-repair", "Overton", "address", ["auto-repair"],
     "North Church Street, Livingston. No website.")
keep("vaughn-collision", "Overton", "city", ["auto-body"],
     "Byrdstown Highway, Livingston. Collision work, no website.")
keep("watkins-and-langford-wrecker-services", "Overton", "city", ["towing"],
     "The address is Oak Street in Livingston. What the profile files as a website is an "
     "m.facebook.com page, so this is a Facebook-only business by any reasonable reading, "
     "whatever the harvest recorded.",
     gap="facebook-only",
     notes=["Harvested as having its own site. The recorded host is m.facebook.com, so this "
            "roster counts it as a Facebook-only web presence."])
keep("t-and-m-automotive", "Overton", "address", ["auto-repair", "transmission"],
     "Rickman Road, Livingston. Repair and transmission work, no website.")
keep("arneys-wrecker-service", "Overton", "address", ["towing"],
     "Kennedy Street, Livingston. No website.")
keep("auto-worx-of-livingston-llc", "Overton", "address", ["auto-repair"],
     "Cookeville Highway, Livingston. Its site answers over plain http and refused our "
     "automated request; that is almost always a bot filter rather than a broken site. Google "
     "files the business as a used car dealer, while the query that surfaced it was auto "
     "repair — worth resolving before either label is quoted.")
keep("waynes-transmission-repair", "Overton", "city", ["transmission"],
     "Little Opossum Creek Road. Transmission work, no website, and no hours on the profile.")
keep("wayne-customs-automotive-and-towing", "Overton", "address", ["auto-repair", "towing"],
     "East Main Street, Livingston, doing both repair and towing per its own name and profile. "
     "No website.")
keep("palestine-tire-shop", "Overton", "address", ["tire"],
     "Palestine Road, Allons. The profile carries no phone number and no website; the address "
     "is the whole of what is known.")
keep("crossroads-diesel-and-auto", "Overton", "own-site", ["diesel", "auto-repair", "transmission"],
     "Its own site, fetched 2026-08-14, gives the address as 3913 Rickman Road, Rickman, and "
     "lists routine maintenance, diesel engine repair, diagnostics, brake work, suspension and "
     "steering, and performance work. The site answers over plain http.",
     town="Rickman",
     sources=[src("http://www.uppercumberlandcrossroadstn.com/",
                  "address 3913 Rickman Rd, Rickman TN and the stated service list")])
keep("light-the-fire-garage-and-fab", "Overton", "city", ["auto-repair"],
     "Standing Stone Highway, Hilham. The web link on the profile points at a Facebook group "
     "rather than a business page.")
keep("roadside-rescue-of-the-upper-cumberland", "Overton", "address", ["towing"],
     "Listed at the corner of Tennessee Drive and Fletcher in Livingston. Facebook page only.")
keep("hunters-garage-inc", "Overton", "address", ["auto-repair"],
     "Mountain Road, Livingston. The site is there, but it redirects away from https down to "
     "plain http, so a browser will mark it not secure.",
     sources=[src("https://huntersgarage.net/",
                  "https requests are redirected to the http origin")])
keep("the-tennessee-hot-rod-shop-llc", "Overton", "address", ["auto-repair"],
     "Jerry Bilbrey Lane, Hilham. No website.")

# --- Putnam County --------------------------------------------------------
keep("car-fix-cookeville", "Putnam", "address", ["auto-repair"],
     "A Cookeville location of the multi-shop CAR FIX brand; the link goes to the chain's own "
     "Cookeville location page.",
     brand="chain")
keep("tire-discounters", "Putnam", "address", ["tire"],
     "Regional tire chain, East Spring Street.",
     brand="chain")
keep("maggart-tire", "Putnam", "address", ["tire"],
     "Cookeville tire shop on Shipley Street, with a working site of its own on https.")
keep("doc-auto-and-tire-center", "Putnam", "address", ["auto-repair", "tire"],
     "Broad Street, Cookeville. The phone and hours came off the Google profile, and there is "
     "no website to check them against.")
keep("doug-freeman-tire-company-llc", "Putnam", "own-site", ["tire"],
     "Its own site, fetched 2026-08-14, gives the location as Cookeville and names Michelin, "
     "BFGoodrich and Uniroyal as the lines it carries, alongside brake, CV axle, strut and "
     "alignment work. The harvest had recorded Rickman; where a shop's own page and the local "
     "pack disagree, this roster follows the shop.",
     sources=[src("https://www.dougfreemantire.com/",
                  "Cookeville location, the Michelin/BFGoodrich/Uniroyal tire lines, and the "
                  "brake, CV axle, strut and alignment service list")],
     town="Cookeville",
     notes=["Harvested as Rickman, Overton County. Corrected to Cookeville, Putnam County, on "
            "the shop's own website."])
keep("patriot-mobile-auto-repair", "Putnam", "city", ["auto-repair"],
     "A mobile mechanic working from a Windsor Drive address in Algood. No website.")
keep("total-automotive", "Putnam", "city", ["auto-repair"],
     "East 10th Street, Cookeville. The site is reachable, but only over plain http.")
keep("rush-towing-llc", "Putnam", "city", ["towing"],
     "The domain on this profile, rushtowing.llc, was fetched on 2026-08-14 and serves a page "
     "offering the domain itself for sale — not a towing company. The phone number is the only "
     "live contact this record has.",
     gap="domain-for-sale",
     sources=[src("https://rushtowing.llc/",
                  "the host serves a 'FOR SALE' domain-brokerage page, not a business site")],
     notes=["Harvested as having its own site. The host now serves a domain-for-sale page, so "
            "this roster counts it as a web gap."])
keep("endurance-automotive-cookeville", "Putnam", "city", ["auto-repair"],
     "The recorded domain gave no answer at all when it was checked on 2026-08-13.")
keep("the-tire-shop", "Putnam", "city", ["tire"],
     "West Broad Street, Cookeville. No website.")
keep("s-o-s-towing-and-recovery-services-llc", "Putnam", "address", ["towing"],
     "C C Camp Road, Cookeville. No website.")
keep("bohannons-towing-service", "Putnam", "address", ["towing"],
     "Harristown Road, Monterey. The Google profile's category field reads 'Band', which is "
     "plainly wrong; the business name and the query that surfaced it both say towing. No "
     "website.",
     notes=["The Google category on this record is 'Band'. It is left in the file and ignored "
            "in favour of the business name."])
keep("walker-diesel-services", "Putnam", "address", ["diesel"],
     "Humble Drive, Cookeville. Filed by Google as a truck repair shop. No website.")
keep("sextons-auto-repair-llc", "Putnam", "city", ["auto-repair", "tire"],
     "Crossville Street North, Monterey. The recorded domain did not respond when it was "
     "checked.")
keep("j-and-g-auto-diesel-repair", "Putnam", "city", ["diesel"],
     "Fisk Road, Cookeville. Diesel work, no website.")
keep("black-smoke-diesel-llc", "Putnam", "address", ["diesel"],
     "Ballard Lane, Cookeville. Diesel work, no website, no hours.")
keep("hales-repair-group", "Putnam", "own-site", ["auto-repair"],
     "Its own site, fetched 2026-08-14, puts the shop in Cookeville rather than Gainesboro as "
     "harvested, and says it specializes in German makes — BMW, Mercedes, VW, Audi, Mini and "
     "Porsche among the marques it names. Nothing else in this roster names a marque specialism "
     "at all.",
     sources=[src("https://halesrepairgroup.com/",
                  "Cookeville location and the stated German-marque specialism")],
     town="Cookeville",
     notes=["Harvested as Gainesboro, Jackson County. Corrected to Cookeville, Putnam County, "
            "on the shop's own website."])

# --- Fentress County ------------------------------------------------------
keep("independent-auto-and-diesel-repair", "Fentress", "own-site",
     ["diesel", "auto-repair", "transmission"],
     "Its own site, fetched 2026-08-14, lists brake, filter, cooling, alignment, transmission, "
     "exhaust, fleet and diesel work down to particulate filters and DEF, and gives the address "
     "as 4859 S. York Hwy, Jamestown. That is Fentress County, not Overton, whatever the "
     "harvest flag says.",
     sources=[src("https://independentautodieselrepair.com/",
                  "address 4859 S. York Hwy, Jamestown TN and the published service list")],
     notes=["Harvested with the Overton County flag set. The address on the shop's own site is "
            "in Jamestown, so it is listed under Fentress County."])
keep("pacana-family-tire-and-repair", "Fentress", "address", ["tire", "auto-repair"],
     "Vol Street, Jamestown, with its own working site on https.")
keep("willard-tire-barn", "Fentress", "address", ["tire"],
     "Bea Lee Road, out past Jamestown. No website.")
keep("auto-solutions-jamestown-llc", "Fentress", "address", ["auto-repair", "transmission"],
     "Kennedy Road, Jamestown. Repair and transmission work per the profile, and no website. "
     "The harvested address arrived with a stray non-English fragment on the end of it, which "
     "has been trimmed rather than published.",
     notes=["The harvested address ended in a Thai-script rendering of 'United States', a "
            "locale artefact of the sweep. Trimmed at render time; the raw value is untouched "
            "in the data file."])
keep("3-sons-automotive-repair", "Fentress", "city", ["auto-repair"],
     "Fairgrounds Road, Jamestown. No website, and no hours on the profile either.")
keep("dave-s-body-shop", "Fentress", "address", ["auto-body"],
     "Alf Threet Road, Jamestown. Body work, no website.")
keep("atkins-towing-llc", "Fentress", "city", ["towing"],
     "South York Highway, Jamestown. Facebook page only.")
keep("mikes-new-and-used-tires", "Fentress", "address", ["tire"],
     "Stockton Road, Jamestown. New and used tires, no website.")
keep("l-train-towing", "Fentress", "own-site", ["towing"],
     "Its site, fetched 2026-08-14, names Jamestown as its base and lists towing, roadside "
     "assistance and heavy recovery — but it runs on a lovable.app builder subdomain rather "
     "than a domain the business owns. That is a rented address, not an owned one.",
     gap="rented-subdomain",
     sources=[src("https://ltraintowing.lovable.app/",
                  "Jamestown base, the towing and roadside service list, and the builder "
                  "subdomain host")],
     notes=["Harvested as having its own site. The host is a lovable.app builder subdomain, so "
            "this roster counts it as a rented web address."])
keep("dcs-body-shop", "Fentress", "address", ["auto-body"],
     "Cooper Bertram Lane, Jamestown. No website.")
keep("choate-body-shop", "Fentress", "address", ["auto-body"],
     "McGhee Road, Jamestown. No website, no hours.")
keep("stockton-automotive-and-towing", "Fentress", "address", ["towing", "auto-repair"],
     "Allardt Highway, Jamestown. Repair and towing, no website.")
keep("mountain-auto-repair", "Fentress", "city", ["transmission", "auto-repair"],
     "Round Mountain Road, Jamestown. The recorded domain did not answer when checked.")

# --- Clay County ----------------------------------------------------------
keep("randell-garage", "Clay", "city", ["auto-repair"],
     "Theater Drive, Celina. Facebook page only.")
keep("d-d-auto-repairs-unlimited", "Clay", "city", ["auto-repair"],
     "Brown Street, Celina. The link on this profile goes to usmapiz.org, which redirects to "
     "usmapinformation.com — a third-party listings site, not the shop's own. It also shares a "
     "phone number with Tilson Auto Repair, a few doors along the same street. The roster "
     "records both facts and resolves neither.",
     gap="aggregator-only",
     sources=[src("https://usmapiz.org/details/d-d-auto-repairs-unlimited-ChIJw8b",
                  "the host issues a 301 to usmapinformation.com, a third-party listings site")],
     notes=["Harvested as having its own site. The host is a third-party listings aggregator, "
            "so this roster counts it as a web gap.",
            "Shares a phone number with Tilson Auto Repair. Neither record is treated as "
            "confirmed until someone calls it."])
keep("nick-auto-repair", "Clay", "address", ["auto-repair"],
     "Main Street, Celina. No website.")
keep("tilson-auto-repair", "Clay", "city", ["auto-repair"],
     "Brown Street, Celina. No website, and the phone number on this profile is the same one "
     "recorded for D D Auto Repairs Unlimited a few doors away.",
     notes=["Shares a phone number with D D Auto Repairs Unlimited. Neither record is treated "
            "as confirmed until someone calls it."])

# --- Pickett County -------------------------------------------------------
keep("pryor-auto-spot", "Pickett", "address", ["auto-repair", "tire", "diesel"],
     "Its own site, fetched 2026-08-14, lists 4x4 service, air conditioning, alignment, brakes, "
     "tires, electrical and diesel engine work, and states that two ASE certified mechanics are "
     "on staff at all times.",
     sources=[src("https://www.pryorsautospot.com/",
                  "Byrdstown location, the published service list, and the claim of two ASE "
                  "certified mechanics on staff at all times")])
keep("pickett-auto-care-and-tire", "Pickett", "address", ["tire", "auto-repair"],
     "One Eleven, Byrdstown. Tire and general service per the profile. No website.")
keep("wilsons-automotive-and-marine", "Pickett", "address", ["auto-repair", "tire"],
     "West Main Street, Byrdstown. The website field on the profile points at a Facebook page "
     "filed under a different name — A.A.W Mobile Mechanic — which is worth resolving before "
     "that link gets quoted anywhere.")

# --- Jackson County -------------------------------------------------------
keep("johnson-auto-parts-and-shop", "Jackson", "city", ["auto-repair"],
     "Grundy Quarles Highway, Gainesboro, and one of only two Jackson County businesses the "
     "sweep returned at all. Facebook page only. The name reads as both a parts counter and a "
     "shop; it surfaced on an auto repair query and is listed on that basis, which is a "
     "judgement call rather than a verified fact.")
keep("uncle-e-cycle-s-and-automotive-repair", "Jackson", "city", ["auto-repair"],
     "Wade Subdivision Lane, Gainesboro. Google files it as a motorcycle shop while the name "
     "says cycles and automotive repair both. The recorded domain did not answer when checked.")


def main() -> int:
    payload = json.loads(ROSTER.read_text(encoding="utf-8"))
    records = payload["businesses"]
    ids = {r["id"] for r in records}

    unknown = (set(EXCLUDED) | set(K)) - ids
    if unknown:
        print(f"annotations reference unknown ids: {sorted(unknown)}", file=sys.stderr)
        return 1
    uncovered = ids - set(EXCLUDED) - set(K)
    if uncovered:
        print(f"records with no hand pass: {sorted(uncovered)}", file=sys.stderr)
        return 1
    overlap = set(EXCLUDED) & set(K)
    if overlap:
        print(f"records both kept and excluded: {sorted(overlap)}", file=sys.stderr)
        return 1

    for record in records:
        rid = record["id"]
        for stale in ("excluded", "town", "county", "county_source", "categories_hand",
                      "brand_type", "web_gap_hand", "blurb", "notes", "sources"):
            record.pop(stale, None)
        if rid in EXCLUDED:
            record["excluded"] = EXCLUDED[rid]
            continue
        hand = K[rid]
        gap = hand["web_gap_hand"]
        record.update(hand)
        record["web_gap_hand"] = record["web_gap"] if gap == "__inherit__" else gap

    ROSTER.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                      encoding="utf-8", newline="\n")
    print(f"annotated {len(records)} records: {len(EXCLUDED)} excluded, {len(K)} listed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
