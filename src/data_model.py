"""Strict record validation with cross-record invariants.

Two rules drive everything in this file.

The first is that a record either carries a full hand pass or carries a written
reason for not being rendered. There is no third state, and there is no silent
deletion: `validate_roster` raises if a single one of the 71 harvested records
falls through both.

The second is that no listing may assert something the roster cannot point at.
The blurb text is checked against a list of claims that generated directory
copy reaches for by reflex — founding years, family ownership, "serving the
community since", certifications, awards, turnaround times, prices. A blurb may
only contain one of those if the record carries a `sources` entry, which is a
URL that was fetched by hand with a note on what it is being used to support.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Mapping, Sequence
from urllib.parse import urlparse

from src.site_config import CATEGORY_LABELS, COUNTIES

SCHEMA_VERSION = 1

COUNTY_SOURCES = {"address", "city", "own-site"}
BRAND_TYPES = {"independent", "chain"}
SITE_STATUSES = {"has-site", "no-website", "weak-web", "dead-site"}
# Re-derived from the recorded host, not copied from the harvest.
WEB_GAPS = {
    None,
    "no-website",        # nothing at all
    "facebook-only",     # a Facebook page in the website field
    "rented-subdomain",  # a builder subdomain the business does not own
    "aggregator-only",   # a third-party listings page in the website field
    "dead-site",         # a domain that gave no answer when it was checked
    "domain-for-sale",   # a parked domain-brokerage page
}

HARVEST_FIELDS = {
    "id", "name", "categories", "city", "address", "phone", "site", "site_host",
    "has_own_site", "web_gap", "reviews", "rating", "is_chain", "in_overton",
    "found_by", "verified", "site_status", "http_status", "live_verified", "panel_checked",
}
HAND_FIELDS = {
    "county", "county_source", "categories_hand", "brand_type", "web_gap_hand",
    "blurb", "notes", "sources",
}
# Set only where the harvested city is wrong and the street address carries no
# town to correct it with. Everywhere else the town derives at render time.
OPTIONAL_HAND_FIELDS = {"town"}

ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DIGITS = re.compile(r"\D+")
WORD = re.compile(r"\S+")

# Claims a generated directory reaches for by reflex. Any of these in a blurb
# requires a recorded source. The check is deliberately blunt: it is cheaper to
# attach a source than to argue about whether a claim really needed one.
INVENTED_CLAIM_PATTERNS = (
    (r"\bsince\s+(?:18|19|20)\d{2}\b", "a founding or 'serving since' year"),
    (r"\b(?:18|19|20)\d{2}\s*[-–]\s*(?:present|today)\b", "an operating-span claim"),
    (r"\bfamily[\s-]owned\b", "a family-ownership claim"),
    (r"\bfamily[\s-]run\b", "a family-ownership claim"),
    (r"\bfamily\s+business\b", "a family-ownership claim"),
    (r"\bgenerations?\b", "a generational-ownership claim"),
    (r"\b(?:founded|established|opened)\s+in\b", "a founding claim"),
    (r"\b(?:decades|years)\s+of\s+experience\b", "an experience claim"),
    (r"\bserving\s+the\s+community\b", "a community-tenure claim"),
    (r"\bASE\b", "a certification claim"),
    (r"\bcertified\b", "a certification claim"),
    (r"\baward[\s-]winning\b", "an awards claim"),
    (r"\b(?:same[\s-]day|next[\s-]day|24[\s-]hour|24/7)\b", "a turnaround or availability claim"),
    (r"\$\s?\d", "a price claim"),
    (r"\b(?:cheapest|lowest\s+price|best\s+price|free\s+estimate)\b", "a price claim"),
    (r"\b(?:trusted|reputable|honest|reliable|friendly)\b", "a reputation claim"),
    (r"\bhighly\s+rated\b", "a reputation claim"),
)

PLACEHOLDER_PATTERNS = (
    r"lorem\s+ipsum", r"\bTBD\b", r"\bTODO\b", r"\bFIXME\b", r"\bXXX\b",
    r"\bplaceholder\b", r"\bcoming\s+soon\b", r"\bexample\.com\b",
)


class DataValidationError(ValueError):
    """Raised with a field location, never with a whole record dumped in."""


def _at(rid: str, field: str) -> str:
    return f"{rid}.{field}"


def _text(value: object, where: str, minimum: int = 1) -> str:
    if not isinstance(value, str) or len(value.strip()) < minimum:
        raise DataValidationError(f"{where}: expected text of at least {minimum} characters")
    if "<" in value or ">" in value:
        raise DataValidationError(f"{where}: markup is not allowed")
    if any(ord(c) < 32 and c not in "\t\n" for c in value):
        raise DataValidationError(f"{where}: control characters are not allowed")
    return value


def _date(value: object, where: str) -> dt.date:
    text = _text(value, where)
    try:
        parsed = dt.date.fromisoformat(text)
    except ValueError as error:
        raise DataValidationError(f"{where}: expected an ISO calendar date") from error
    if parsed > dt.date.today():
        raise DataValidationError(f"{where}: dates in the future are not allowed")
    return parsed


def _web_url(value: object, where: str, require_https: bool = False) -> str:
    text = _text(value, where, 8)
    parsed = urlparse(text)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise DataValidationError(f"{where}: expected an absolute http(s) URL")
    if require_https and parsed.scheme != "https":
        raise DataValidationError(f"{where}: expected HTTPS")
    if parsed.username or parsed.password:
        raise DataValidationError(f"{where}: credentials in URLs are not allowed")
    return text


def phone_digits(raw: object) -> str:
    return DIGITS.sub("", str(raw or ""))[-10:]


def _validate_sources(record: Mapping[str, object], rid: str) -> list[Mapping[str, str]]:
    sources = record["sources"]
    if not isinstance(sources, list):
        raise DataValidationError(f"{_at(rid, 'sources')}: expected an array")
    seen = set()
    for index, source in enumerate(sources):
        where = f"{_at(rid, 'sources')}[{index}]"
        if not isinstance(source, Mapping) or set(source) != {"url", "checked", "supports"}:
            raise DataValidationError(f"{where}: expected url, checked and supports")
        url = _web_url(source["url"], f"{where}.url")
        _date(source["checked"], f"{where}.checked")
        _text(source["supports"], f"{where}.supports", 20)
        if url in seen:
            raise DataValidationError(f"{where}.url: duplicate source")
        seen.add(url)
    return sources


def _validate_blurb(record: Mapping[str, object], rid: str) -> str:
    where = _at(rid, "blurb")
    blurb = _text(record["blurb"], where, 20)
    if not blurb.rstrip().endswith((".", "?")):
        raise DataValidationError(f"{where}: entries are sentences and end in a full stop")
    words = len(WORD.findall(blurb))
    if not 5 <= words <= 80:
        raise DataValidationError(f"{where}: {words} words is outside the 5-80 range")
    for pattern in PLACEHOLDER_PATTERNS:
        if re.search(pattern, blurb, re.I):
            raise DataValidationError(f"{where}: placeholder text matching /{pattern}/")
    if record["sources"]:
        return blurb
    for pattern, label in INVENTED_CLAIM_PATTERNS:
        if re.search(pattern, blurb, re.I):
            raise DataValidationError(
                f"{where}: makes {label} with no entry in `sources` to point at")
    return blurb


def _validate_record(record: Mapping[str, object]) -> None:
    if not isinstance(record, Mapping):
        raise DataValidationError("records: expected objects")
    rid = record.get("id")
    if not isinstance(rid, str) or not ID.fullmatch(rid):
        raise DataValidationError(f"records: {rid!r} is not a valid stable id")

    missing = HARVEST_FIELDS - set(record)
    if missing:
        raise DataValidationError(f"{rid}: missing harvest fields: {', '.join(sorted(missing))}")

    _text(record["name"], _at(rid, "name"), 2)
    _text(record["city"], _at(rid, "city"), 3)
    _date(record["panel_checked"], _at(rid, "panel_checked"))
    _date(record["verified"], _at(rid, "verified"))
    if record["site_status"] not in SITE_STATUSES:
        raise DataValidationError(f"{_at(rid, 'site_status')}: unknown status")
    if not isinstance(record["reviews"], int) or record["reviews"] < 0:
        raise DataValidationError(f"{_at(rid, 'reviews')}: expected a non-negative integer")
    if not isinstance(record["rating"], (int, float)) or not 0 <= record["rating"] <= 5:
        raise DataValidationError(f"{_at(rid, 'rating')}: expected a rating between 0 and 5")
    if record["site"] is not None:
        _web_url(record["site"], _at(rid, "site"))
    if record["address"] is not None:
        _text(record["address"], _at(rid, "address"), 5)
    if record["phone"] is not None and len(phone_digits(record["phone"])) != 10:
        raise DataValidationError(f"{_at(rid, 'phone')}: expected ten dialable digits")

    hours = record.get("hours")
    if hours is not None:
        if not isinstance(hours, Mapping) or not hours:
            raise DataValidationError(f"{_at(rid, 'hours')}: expected a non-empty weekday map")
        if not record.get("hours_source") or not record.get("hours_checked"):
            raise DataValidationError(
                f"{_at(rid, 'hours')}: hours require both hours_source and hours_checked")
        _date(record["hours_checked"], _at(rid, "hours_checked"))
        for day, value in hours.items():
            _text(day, f"{_at(rid, 'hours')}.{day}", 3)
            _text(value, f"{_at(rid, 'hours')}.{day}", 3)

    if "excluded" in record:
        _text(record["excluded"], _at(rid, "excluded"), 40)
        stray = (HAND_FIELDS | OPTIONAL_HAND_FIELDS) & set(record)
        if stray:
            raise DataValidationError(
                f"{rid}: excluded records carry no hand pass, found {', '.join(sorted(stray))}")
        return

    absent = HAND_FIELDS - set(record)
    if absent:
        raise DataValidationError(
            f"{rid}: neither rendered nor excluded — missing {', '.join(sorted(absent))}. "
            "Every harvested record needs a hand pass or a written reason.")

    if "town" in record:
        _text(record["town"], _at(rid, "town"), 3)
        if record["town"] == record["city"]:
            raise DataValidationError(
                f"{_at(rid, 'town')}: repeats the harvested city, so it corrects nothing")
    if record["county"] not in COUNTIES:
        raise DataValidationError(f"{_at(rid, 'county')}: outside the six-county scope")
    if record["county_source"] not in COUNTY_SOURCES:
        raise DataValidationError(f"{_at(rid, 'county_source')}: unknown derivation")
    if record["brand_type"] not in BRAND_TYPES:
        raise DataValidationError(f"{_at(rid, 'brand_type')}: unknown brand type")
    if record["web_gap_hand"] not in WEB_GAPS:
        raise DataValidationError(f"{_at(rid, 'web_gap_hand')}: unknown web-gap class")

    categories = record["categories_hand"]
    if not isinstance(categories, list) or not categories:
        raise DataValidationError(f"{_at(rid, 'categories_hand')}: expected a non-empty array")
    if len(categories) != len(set(categories)):
        raise DataValidationError(f"{_at(rid, 'categories_hand')}: duplicate category")
    for category in categories:
        if category not in CATEGORY_LABELS:
            raise DataValidationError(f"{_at(rid, 'categories_hand')}: {category!r} is not a category")

    notes = record["notes"]
    if not isinstance(notes, list):
        raise DataValidationError(f"{_at(rid, 'notes')}: expected an array")
    for index, note in enumerate(notes):
        _text(note, f"{_at(rid, 'notes')}[{index}]", 20)

    _validate_sources(record, rid)
    _validate_blurb(record, rid)

    if record["county_source"] == "own-site" and not record["sources"]:
        raise DataValidationError(
            f"{rid}: a county corrected from the shop's own site needs that site in `sources`")
    if record["web_gap_hand"] is None and record["site"] is None:
        raise DataValidationError(f"{rid}: no website recorded but no web gap declared either")
    if record["web_gap_hand"] != record["web_gap"] and not record["notes"]:
        raise DataValidationError(
            f"{rid}: the web gap was re-derived away from the harvest with no note saying so")


def _cross_record(records: Sequence[Mapping[str, object]]) -> None:
    ids = [r["id"] for r in records]
    if len(ids) != len(set(ids)):
        raise DataValidationError("records: duplicate id")

    listed = [r for r in records if "excluded" not in r]
    if not listed:
        raise DataValidationError("records: nothing survives exclusion")

    # A shared phone is not automatically an error — two shops on the same
    # street really can answer one line. Publishing it as if it were two
    # independently confirmed businesses is. So both records must say so.
    by_phone: dict[str, list[Mapping[str, object]]] = {}
    for record in listed:
        if record["phone"]:
            by_phone.setdefault(phone_digits(record["phone"]), []).append(record)
    for phone, group in by_phone.items():
        if len(group) < 2:
            continue
        for record in group:
            others = [o["name"] for o in group if o["id"] != record["id"]]
            joined = " ".join(record["notes"])
            if not any(name in joined for name in others):
                raise DataValidationError(
                    f"{_at(record['id'], 'notes')}: shares phone {phone} with "
                    f"{', '.join(others)} and does not say so")

    by_host: dict[str, list[str]] = {}
    for record in listed:
        if record["site_host"]:
            by_host.setdefault(record["site_host"].lower(), []).append(record["id"])
    for host, group in by_host.items():
        if len(group) > 1 and host not in {"facebook.com", "m.facebook.com", "www.facebook.com"}:
            raise DataValidationError(
                f"records: {host} is claimed by more than one listed record ({', '.join(group)})")

    for county in COUNTIES:
        if not any(r["county"] == county for r in listed):
            raise DataValidationError(f"records: {county} County has no listed business")
    for category in CATEGORY_LABELS:
        if not any(category in r["categories_hand"] for r in listed):
            raise DataValidationError(f"records: category {category!r} has no listed business")

    # Identical-length descriptions are the loudest signal on a directory page
    # that it was generated rather than written. This is the guard.
    lengths = [len(WORD.findall(r["blurb"])) for r in listed]
    if len(set(lengths)) < 12:
        raise DataValidationError(
            f"records: only {len(set(lengths))} distinct blurb lengths across {len(listed)} entries")
    if max(lengths) - min(lengths) < 25:
        raise DataValidationError(
            f"records: blurb lengths span only {max(lengths) - min(lengths)} words")

    blurbs = [r["blurb"] for r in listed]
    if len(set(blurbs)) != len(blurbs):
        raise DataValidationError("records: two listed entries share the same blurb")


def validate_roster(payload: object) -> list[Mapping[str, object]]:
    """Validate the whole roster file. Raises on the first problem found."""
    if not isinstance(payload, Mapping):
        raise DataValidationError("roster: expected an object")
    records = payload.get("businesses")
    if not isinstance(records, list) or not records:
        raise DataValidationError("roster.businesses: expected a non-empty array")
    _date(payload.get("generated"), "roster.generated")
    for record in records:
        _validate_record(record)
    _cross_record(records)
    return records


def listed(records: Sequence[Mapping[str, object]]) -> list[Mapping[str, object]]:
    """The records the page renders, name-ordered. Exclusions are filtered here."""
    kept = [r for r in records if "excluded" not in r]
    return sorted(kept, key=lambda r: r["name"].lower().removeprefix("the "))


def excluded(records: Sequence[Mapping[str, object]]) -> list[Mapping[str, object]]:
    kept = [r for r in records if "excluded" in r]
    return sorted(kept, key=lambda r: r["name"].lower())
