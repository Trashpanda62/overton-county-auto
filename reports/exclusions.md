# Exclusions

Twelve of the 71 harvested records are not rendered on the site. None of them was
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

The harvest set `is_chain` to `false` on all 71 records, which is wrong. Three
listed businesses are locations of a chain or multi-location brand:

- **CAR FIX Cookeville**, Cookeville — teamcarfix.com
- **Strickland Brothers 10 Minute Oil Change**, Livingston — sboilchange.com
- **Tire Discounters**, Cookeville — tirediscounters.com

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
Fentress. The site's Overton County count is 20 rather than the 22 the
raw `in_overton` flags would have produced, and the difference is entirely these
corrections.

## The excluded records


### Christian Brothers Automotive Celina

`christian-brothers-automotive-celina` · harvested as Celina · found by `auto repair|Celina` · 686 Google reviews read 2026-08-13

Out of region. The address is 4075 S Preston Rd, Celina, TX 75009 and the phone is a 945 area code; Google's own category line reads 'Auto repair shop in Celina, Texas'. The Celina query pulled back the Texas town of the same name.

### Jackson Motors Body Shop

`jackson-motors-body-shop` · harvested as Livingston · found by `auto body shop|Livingston` · 39 Google reviews read 2026-08-13

Out of region. The address is 63 Oakdale Rd, Lafayette, TN 37083 — Macon County — with a 615 area code. The harvest flagged it in_overton; its own address does not agree, and the spec's Overton prospect list inherits the same error.

### Joe's Automotive Repair

`joe-automotive-repair` · harvested as Monroe · found by `auto repair|Monroe` · 95 Google reviews read 2026-08-13

Out of region. The address is 230b Upton Rd, Sweetwater, TN 37874 with a 423 area code. The Monroe query matched Monroe County in East Tennessee rather than the Monroe community in Overton County. The spec lists this business as an Overton prospect; the harvested address does not support that, and the address is what we can check.

### Joshua's Tire Sales

`joshua-tire-sales` · harvested as Hilham · found by `tire shops|Hilham` · 112 Google reviews read 2026-08-13

Out of region. The address is 1276 TN-113, White Pine, TN 37890 — Jefferson County, about 150 miles east — with an 865 area code. It was returned by the Hilham tire query.

### Kingdom Mobile Auto Repair

`kingdom-mobile-auto-repair` · harvested as Monroe · found by `auto repair|Monroe` · 108 Google reviews read 2026-08-13

Out of scope for mobile operators. The record has no address and no phone, and the shop's own site, fetched 2026-08-14, publishes no service radius and no town list — it says only that it serves 'the Middle TN area'. The scope rule admits a mobile mechanic when it is based in one of the six counties and publishes a service radius. This one clears neither test on the evidence available. One phone call could reinstate it.

### Mobile Diesel Mechanic | Howells

`mobile-diesel-mechanic-howells` · harvested as Livingston · found by `diesel repair|Livingston` · 5 Google reviews read 2026-08-13

Out of region. The recorded website was fetched on 2026-08-14: the business is based in Clarksville, states a service area of 'All Areas Within 100 Mile Radius of Clarksville, TN', and lists a second location at Bradyville serving Woodbury, Murfreesboro, Smyrna and neighbours. It names neither Livingston, nor Overton County, nor the Upper Cumberland. The Livingston profile is a service-area listing, not a shop here.

### Monroe Tire & Service Inc.

`monroe-tire-and-service-inc` · harvested as Monroe · found by `auto repair|Monroe` · 63 Google reviews read 2026-08-13

Out of region. Google's category line reads 'Auto repair shop in Madisonville, Tennessee', the phone is a 423 number and the address is on US-411 — Monroe County, East Tennessee. Same mis-resolution as the record above.

### Monteagle Truck & Tire

`monteagle-truck-and-tire` · harvested as Hilham · found by `tire shops|Hilham` · 2 Google reviews read 2026-08-13

Out of region. The address is Dixie Lee Ave, Monteagle, TN 37356 — the Cumberland Plateau above Grundy and Marion counties, roughly 80 miles south. Returned by the Hilham tire query.

### Monterey Market

`monterey-market` · harvested as Monterey · found by `tire shops|Monterey` · 110 Google reviews read 2026-08-13

Not an auto business. The recorded website is the Town of Monterey's own 'Visit Farmers Market' page. The tire query for Monterey resolved to the town market.

### Philly Auto

`philly-auto` · harvested as Byrdstown · found by `auto repair|Byrdstown` · 2,000 Google reviews read 2026-08-13

Unverifiable. The record carries no address, no phone and no website — nothing in it can be checked against anything. Its 2,000 review count is also an order of magnitude above every other Byrdstown record, which is what a mis-resolved local pack looks like. The spec already flagged this business's knowledge-panel lookup as failed.

### Rush Towing Service

`rush-towing-service` · harvested as Cookeville · found by `towing|Cookeville` · 279 Google reviews read 2026-08-13

Duplicate. Same business and same host as rush-towing-llc, which is the record that carries the street address and the phone number. This one has neither.

### Stuarts Auto Supply

`stuarts-auto-supply` · harvested as Byrdstown · found by `auto repair|Byrdstown` · 11 Google reviews read 2026-08-13

Out of subject scope. Google's category line reads 'Auto parts store in Byrdstown, Tennessee'. This directory lists businesses that repair, service or tire a vehicle; it does not list parts counters, dealerships, car washes, detailers, salvage or rental.

---

71 harvested · 59 listed · 12 excluded · 0 deleted. Regenerate with `python scripts/build.py`.
