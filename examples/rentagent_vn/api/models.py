"""Pydantic request/response models for the REST API."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Type Aliases
# ---------------------------------------------------------------------------

ScanFrequency = Literal["auto", "manual"]
CampaignStatus = Literal["active", "paused", "archived"]
ScanStatus = Literal["running", "completed", "failed"]
ListingStage = Literal[
    "new",
    "reviewing",
    "contacted",
    "visited",
    "skipped",
    "pending_review",
    "researching",
]
OutreachStatus = Literal["drafted", "sent", "failed"]
ResearchStatus = Literal["queued", "running", "done", "failed"]

Hour = Annotated[int, Field(ge=0, le=23)]

# ---------------------------------------------------------------------------
# Campaign
# ---------------------------------------------------------------------------


class CreateCampaignRequest(BaseModel):
    name: str = "New Campaign"
    preferences: dict[str, Any] = Field(default_factory=dict)
    sources: list[str] = Field(default_factory=list)
    scan_frequency: ScanFrequency = "manual"
    auto_scan_hour: Hour = 6
    auto_scan_timezone: str = "Asia/Ho_Chi_Minh"


class UpdateCampaignRequest(BaseModel):
    name: str | None = None
    preferences: dict[str, Any] | None = None
    sources: list[str] | None = None
    scan_frequency: ScanFrequency | None = None
    auto_scan_hour: Hour | None = None
    auto_scan_timezone: str | None = None
    status: CampaignStatus | None = None


class CampaignResponse(BaseModel):
    id: str
    name: str
    preferences: dict[str, Any]
    sources: list[str]
    scan_frequency: ScanFrequency
    auto_scan_hour: Hour = 6
    auto_scan_timezone: str = "Asia/Ho_Chi_Minh"
    last_auto_scan_date: str | None = None
    status: CampaignStatus
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------


class UpdateListingRequest(BaseModel):
    stage: ListingStage | None = None
    skip_reason: str | None = None
    user_notes: str | None = None


class ListingResponse(BaseModel):
    id: str
    campaign_id: str
    stage: ListingStage
    title: str | None = None
    description: str | None = None
    price_vnd: float | None = None
    price_display: str | None = None
    deposit_vnd: float | None = None
    address: str | None = None
    district: str | None = None
    city: str | None = None
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
    match_score: float | None = None
    skip_reason: str | None = None
    user_notes: str | None = None
    scan_id: str | None = None
    research_id: str | None = None
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------


class ScanResponse(BaseModel):
    id: str
    campaign_id: str
    job_id: str | None = None
    status: ScanStatus
    listings_found: int = 0
    new_listings: int = 0
    errors: list[dict[str, Any]] = Field(default_factory=list)
    started_at: str
    completed_at: str | None = None


class TriggerScanRequest(BaseModel):
    """Optional overrides when triggering a manual scan."""

    query: str | None = None  # Override the auto-generated query


# ---------------------------------------------------------------------------
# Activity
# ---------------------------------------------------------------------------


class ActivityResponse(BaseModel):
    id: int
    campaign_id: str
    scan_id: str | None = None
    event_type: str
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


class StatsResponse(BaseModel):
    total_listings: int = 0
    by_stage: dict[str, int] = Field(default_factory=dict)
    new_today: int = 0
    total_scans: int = 0


# ---------------------------------------------------------------------------
# Zalo
# ---------------------------------------------------------------------------


class ZaloAuthCookieRequest(BaseModel):
    cookie: str
    imei: str
    user_agent: str


class ZaloStatusResponse(BaseModel):
    connected: bool
    phone_number: str | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Outreach
# ---------------------------------------------------------------------------


class DraftOutreachRequest(BaseModel):
    custom_notes: str | None = None


class SendOutreachRequest(BaseModel):
    message_id: str
    final_text: str | None = None


class OutreachMessageResponse(BaseModel):
    id: str
    listing_id: str
    campaign_id: str
    draft_text: str
    final_text: str | None = None
    status: OutreachStatus
    landlord_phone: str | None = None
    zalo_user_id: str | None = None
    sent_at: str | None = None
    error_message: str | None = None
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Area Research
# ---------------------------------------------------------------------------


class AutoOutreachConfigRequest(BaseModel):
    enabled: bool = False
    threshold: float = 7.0
    must_pass: dict[str, float] = Field(default_factory=dict)
    message_template: str | None = None


class TriggerResearchRequest(BaseModel):
    """Request to start area research for one or more listings."""

    listing_ids: list[str]
    criteria: list[str] = Field(
        default_factory=lambda: [
            "food_shopping",
            "healthcare",
            "education_family",
            "transportation",
            "entertainment_sports",
            "street_atmosphere",
            "security",
        ]
    )
    auto_outreach: AutoOutreachConfigRequest = Field(
        default_factory=AutoOutreachConfigRequest,
    )


class TriggerResearchResponse(BaseModel):
    research_ids: list[str]
    status: ResearchStatus = "queued"
    message: str = ""


class AreaResearchResponse(BaseModel):
    id: str
    listing_id: str
    campaign_id: str
    status: ResearchStatus
    criteria: list[str] = Field(default_factory=list)
    scores: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    verdict: str | None = None
    overall_score: float | None = None
    street_view_urls: list[str] = Field(default_factory=list)
    auto_outreach_enabled: bool = False
    auto_outreach_threshold: float | None = None
    auto_outreach_conditions: dict[str, Any] | None = None
    auto_outreach_triggered: bool = False
    tinyfish_job_id: str | None = None
    error_message: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    created_at: str
    updated_at: str
