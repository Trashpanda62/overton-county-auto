"""Typed, validated source of truth for public site identity and metadata.

The canonical domain is not registered yet. It is still declared here as the
canonical URL because every absolute reference on the page — canonical link,
og:url, sitemap loc, JSON-LD @id — has to agree with each other and with the
address the site will eventually answer on. Pointing them at a placeholder
would mean rewriting all of them at launch and re-running every check.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

# The six Upper Cumberland counties this directory covers, flagship first.
# Order is meaningful: it is the order the page renders its county sections in,
# and Overton leads because the property is Overton-flagged by design.
COUNTIES: tuple[str, ...] = ("Overton", "Putnam", "Fentress", "Clay", "Pickett", "Jackson")
FLAGSHIP_COUNTY = "Overton"

# Hand-assigned categories. These are not the harvest's query-derived tags;
# they were re-derived per record from the business name, the Google category
# and the query that surfaced it. Towing is last on purpose — it is a listed
# category, not a content investment.
CATEGORIES: tuple[tuple[str, str, str], ...] = (
    ("auto-repair", "Auto repair", "AutoRepair"),
    ("tire", "Tire shops", "TireShop"),
    ("auto-body", "Auto body", "AutoBodyShop"),
    ("diesel", "Diesel repair", "AutomotiveBusiness"),
    ("transmission", "Transmission repair", "AutomotiveBusiness"),
    ("towing", "Towing", "TowingService"),
)
CATEGORY_LABELS = {key: label for key, label, _ in CATEGORIES}
CATEGORY_SCHEMA = {key: schema for key, _, schema in CATEGORIES}


@dataclass(frozen=True)
class SiteConfig:
    name: str
    h1: str
    title: str
    description: str
    social_description: str
    canonical_url: str
    domain_status: str
    locale: str
    publisher_name: str
    publisher_url: str
    correction_email: str
    date_published: str
    date_modified: str
    date_human: str
    harvest_date: str
    harvest_date_human: str
    theme_color: str
    network_sites: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        for label, value in (("canonical_url", self.canonical_url), ("publisher_url", self.publisher_url)):
            parsed = urlparse(value)
            if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
                raise ValueError(f"{label} must be a clean HTTPS URL")
            if not value.endswith("/"):
                raise ValueError(f"{label} must end with a slash")
        if "@" not in self.correction_email:
            raise ValueError("correction_email must be an address")
        if self.date_modified < self.date_published:
            raise ValueError("date_modified precedes date_published")
        if self.harvest_date > self.date_modified:
            raise ValueError("harvest cannot post-date the build")
        if not self.network_sites:
            raise ValueError("network_sites must not be empty")
        for label, url in self.network_sites:
            if not label or urlparse(url).scheme != "https":
                raise ValueError(f"network site {label!r} must be a labelled HTTPS URL")

    @property
    def host(self) -> str:
        return urlparse(self.canonical_url).netloc

    def url(self, path: str) -> str:
        return urljoin(self.canonical_url, path.lstrip("/"))


SITE_CONFIG = SiteConfig(
    name="Upper Cumberland Auto",
    h1="Every auto shop we can prove is real, in six counties.",
    title="Upper Cumberland Auto — auto repair, tire, body and towing shops in six Tennessee counties",
    description=(
        "A hand-checked roster of auto repair, tire, body, diesel, transmission and towing "
        "businesses in Overton, Putnam, Fentress, Clay, Pickett and Jackson counties, Tennessee. "
        "Unranked, unrated, and free to be listed on."
    ),
    social_description=(
        "Auto repair, tire, body and towing shops across the six Upper Cumberland counties, "
        "with Overton County first. No rankings, no scores, no paid placement."
    ),
    canonical_url="https://overtoncountyauto.com/",
    domain_status="not yet registered",
    locale="en-US",
    publisher_name="Barnraised",
    publisher_url="https://barnraised.design/",
    correction_email="steve@barnraised.design",
    date_published="2026-08-14",
    date_modified="2026-08-14",
    date_human="Aug 14, 2026",
    harvest_date="2026-08-13",
    harvest_date_human="Aug 13, 2026",
    theme_color="#1f3a2e",
    network_sites=(
        ("Livingston Outdoors", "https://livingstonoutdoors.com/"),
        ("Visit Livingston TN", "https://visitlivingstontn.com/"),
        ("Middle TN Printers", "https://middletnprinters.com/"),
    ),
)
