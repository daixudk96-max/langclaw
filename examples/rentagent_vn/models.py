"""Pydantic models for rental listings and the ListingCache protocol."""

from __future__ import annotations

import re
from typing import Any, Protocol, runtime_checkable

from loguru import logger
from pydantic import BaseModel, Field


class ListingSummary(BaseModel):
    """Compact listing returned from search/scroll results."""

    title: str | None = None
    description: str | None = None
    price_vnd: float | None = None
    price_display: str | None = None
    deposit_vnd: float | None = None
    address: str | None = None
    district: str | None = None
    city: str | None = Field(default="Ho Chi Minh")
    area_sqm: float | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    listing_url: str | None = None
    thumbnail_url: str | None = None
    posted_date: str | None = None
    source_platform: str | None = None
    landlord_name: str | None = None
    landlord_phone: str | None = None
    landlord_zalo: str | None = None
    landlord_facebook_url: str | None = None
    landlord_contact_method: str | None = None


# ---------------------------------------------------------------------------
# TinyFish field-name normalization
# ---------------------------------------------------------------------------

# Maps non-standard field names returned by TinyFish to canonical
# ListingSummary field names.
_FIELD_ALIASES: dict[str, str] = {
    "area": "area_sqm",
    "size": "area_sqm",
    "dien_tich": "area_sqm",
    "price": "price_display",
    "gia": "price_display",
    "rooms": "bedrooms",
    "bedroom": "bedrooms",
    "phong_ngu": "bedrooms",
    "bathroom": "bathrooms",
    "phong_tam": "bathrooms",
    "contact": "landlord_phone",
    "phone": "landlord_phone",
    "so_dien_thoai": "landlord_phone",
    "location": "address",
    "dia_chi": "address",
    "name": "landlord_name",
    "poster": "landlord_name",
    "url": "listing_url",
    "link": "listing_url",
    "image": "thumbnail_url",
    "img": "thumbnail_url",
    "date": "posted_date",
    "source": "source_platform",
    "facebook_url": "landlord_facebook_url",
    "zalo": "landlord_zalo",
}

# Vietnamese placeholder strings that should be treated as null.
_NULL_PLACEHOLDERS = frozenset(
    {
        "khong de cap",
        "không đề cập",
        "khong ro",
        "không rõ",
        "chua ro",
        "chưa rõ",
        "n/a",
        "na",
        "none",
        "null",
        "không có",
        "khong co",
    }
)

# Regex that matches Vietnamese null placeholders with extra detail in
# parentheses, e.g. "Không đề cập (Liên hệ để biết thêm chi tiết)".
_NULL_PATTERN = re.compile(
    r"^(không đề cập|khong de cap|không rõ|chưa rõ|liên hệ|lien he)" r"(\s*\(.*\))?$",
    re.IGNORECASE,
)

_KNOWN_FIELDS = set(ListingSummary.model_fields.keys())


def _normalize_listing_dict(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize a single listing dict from TinyFish output.

    - Renames known field aliases to canonical ListingSummary field names.
    - Converts Vietnamese placeholder strings to None.
    - Strips unknown meta keys (id, note, group, etc.).
    """
    normalized: dict[str, Any] = {}

    for key, value in raw.items():
        canonical = _FIELD_ALIASES.get(key.lower().strip(), key)

        if canonical not in _KNOWN_FIELDS:
            continue

        if isinstance(value, str):
            stripped = value.strip()
            if stripped.lower() in _NULL_PLACEHOLDERS or _NULL_PATTERN.match(stripped):
                value = None

        normalized[canonical] = value

    return normalized


class ListingDetail(ListingSummary):
    """Rich listing detail from an individual listing page."""

    deposit_display: str | None = None
    floor: str | None = None
    furnishing: str | None = None
    amenities: list[str] = Field(default_factory=list)
    pet_policy: str | None = None
    photo_urls: list[str] = Field(default_factory=list)
    landlord_email: str | None = None
    landlord_response_rate: str | None = None
    nearby: list[str] = Field(default_factory=list)


class TinyFishListingResponse(BaseModel):
    """Validates the raw JSON wrapper returned by TinyFish.

    TinyFish returns either ``{"listings": [...]}`` or a bare list.
    This model normalises both shapes into a uniform ``listings`` list
    and re-validates each item through ``ListingSummary``.
    """

    listings: list[ListingSummary] = Field(default_factory=list)

    @classmethod
    def _parse_items(cls, items: list[Any]) -> list[ListingSummary]:
        """Validate a list of raw dicts through normalization + Pydantic."""
        parsed: list[ListingSummary] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                parsed.append(ListingSummary.model_validate(_normalize_listing_dict(item)))
            except Exception as exc:
                logger.debug("Skipping invalid listing item: {}", exc)
        return parsed

    @classmethod
    def from_raw(cls, raw: dict[str, Any] | list[Any]) -> TinyFishListingResponse:
        """Parse raw TinyFish output into a validated response.

        Handles:
          - ``{"listings": [...]}`` wrapper (canonical)
          - ``{"rentals": [...]}`` / ``{"results": [...]}`` / ``{"data": [...]}``
            (common TinyFish variants)
          - Bare list of listing dicts
          - Single listing dict
        """
        if isinstance(raw, list):
            return cls(listings=cls._parse_items(raw))

        if isinstance(raw, dict):
            # Try known key variants for the listing array
            for key in ("listings", "rentals", "results", "data"):
                items = raw.get(key)
                if isinstance(items, list):
                    return cls(listings=cls._parse_items(items))

            # Single listing dict — strip meta keys before validating
            return cls(listings=cls._parse_items([raw]))

        return cls()


# ---------------------------------------------------------------------------
# Area Research models
# ---------------------------------------------------------------------------

RESEARCH_CRITERIA_KEYS = [
    "food_shopping",
    "healthcare",
    "education_family",
    "transportation",
    "entertainment_sports",
    "street_atmosphere",
    "security",
]

RESEARCH_CRITERIA_LABELS: dict[str, str] = {
    "food_shopping": "Ăn uống & Mua sắm",
    "healthcare": "Y tế",
    "education_family": "Giáo dục & Gia đình",
    "transportation": "Giao thông",
    "entertainment_sports": "Giải trí & Thể thao",
    "street_atmosphere": "Đường phố & Vệ sinh",
    "security": "An ninh",
}


class AutoOutreachConfig(BaseModel):
    """Configuration for auto-outreach after research."""

    enabled: bool = False
    threshold: float = 7.0
    must_pass: dict[str, float] = Field(default_factory=dict)
    message_template: str | None = None


class ResearchConfig(BaseModel):
    """Full research job configuration."""

    criteria: list[str] = Field(default_factory=lambda: list(RESEARCH_CRITERIA_KEYS))
    auto_outreach: AutoOutreachConfig = Field(default_factory=AutoOutreachConfig)


class CriterionDetail(BaseModel):
    """A key-value detail for a criterion (replaces dict[str, str] for OpenAI compatibility)."""

    key: str
    value: str


class CriterionScore(BaseModel):
    """Score and details for a single research criterion."""

    criterion_key: str  # e.g. "food_shopping", "healthcare"
    score: int
    label: str
    highlights: list[str]
    details: list[CriterionDetail]  # OpenAI strict mode requires list, not dict
    walking_distance: bool | None = None


class ResearchScores(BaseModel):
    """Complete scoring result from area research."""

    overall: float
    criteria: list[CriterionScore]  # OpenAI strict mode requires list, not dict

    verdict: str


class ResearchResult(BaseModel):
    """Full structured result from area research."""

    address: str
    verdict: str
    scores: ResearchScores
    street_view_urls: list[str] | None = None
    overall_score: float
    verdict: str
    criteria: dict[str, CriterionScore]
    highlights: list[str]
    details: dict[str, str]
    walking_distance: bool | None = None


class ScrapeInput(BaseModel):
    """Input to the scrape workflow."""

    urls: list[str]
    query: str
    user_preference: str | None = None


class ScrapeResult(BaseModel):
    """Output of the scrape workflow."""

    listings: list[ListingSummary] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    urls_scanned: int = 0
    streaming_urls: dict[str, str] = Field(
        default_factory=dict,
        description="Source URL -> live browser preview URL for FE iframe.",
    )


# ---------------------------------------------------------------------------
# Cache protocol (architecture only — not implemented in MVP)
# ---------------------------------------------------------------------------


@runtime_checkable
class ListingCache(Protocol):
    """Interface for caching TinyFish scrape results.

    MVP: not implemented — all requests hit TinyFish directly.
    Production: in-memory dict (dev) or Redis (prod) with TTL.
    """

    async def get_search(self, url: str, query: str) -> list[dict[str, Any]] | None:
        """Return cached search results or ``None`` on miss.

        Key: ``hash(normalized_url + query)``, TTL 1-4 hours.
        """
        ...

    async def set_search(self, url: str, query: str, results: list[dict[str, Any]]) -> None:
        """Store search results in cache."""
        ...

    async def get_listing(self, listing_url: str) -> dict[str, Any] | None:
        """Return cached listing detail or ``None`` on miss.

        Key: ``listing_url``, TTL 6-24 hours.
        """
        ...

    async def set_listing(self, listing_url: str, detail: dict[str, Any]) -> None:
        """Store listing detail in cache."""
        ...
