"""Database query functions for RentAgent VN."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from examples.rentagent_vn.db.connection import get_db


def _gen_id() -> str:
    return uuid4().hex[:12]


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def _row_to_dict(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    return dict(row)


def _compute_fingerprint(listing: dict[str, Any]) -> str:
    """Compute a dedup fingerprint from address + price + area."""
    parts = [
        str(listing.get("address", "")).lower().strip(),
        str(listing.get("price_vnd", "")),
        str(listing.get("area_sqm", "")),
    ]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Campaigns
# ---------------------------------------------------------------------------


async def create_campaign(
    name: str = "Chiến dịch mới",
    preferences: dict[str, Any] | None = None,
    sources: list[str] | None = None,
    scan_frequency: str = "manual",
) -> dict[str, Any]:
    db = await get_db()
    cid = _gen_id()
    now = _now()
    await db.execute(
        """INSERT INTO campaigns
           (id, name, preferences_json, sources_json, scan_frequency, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            cid,
            name,
            json.dumps(preferences or {}, ensure_ascii=False),
            json.dumps(sources or [], ensure_ascii=False),
            scan_frequency,
            now,
            now,
        ),
    )
    await db.commit()
    return await get_campaign(cid)  # type: ignore[return-value]


async def get_campaign(campaign_id: str) -> dict[str, Any] | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
    row = await cursor.fetchone()
    if row is None:
        return None
    d = _row_to_dict(row)
    d["preferences"] = json.loads(d.pop("preferences_json", "{}"))
    d["sources"] = json.loads(d.pop("sources_json", "[]"))
    return d


async def list_campaigns() -> list[dict[str, Any]]:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM campaigns ORDER BY created_at DESC")
    rows = await cursor.fetchall()
    results = []
    for row in rows:
        d = _row_to_dict(row)
        d["preferences"] = json.loads(d.pop("preferences_json", "{}"))
        d["sources"] = json.loads(d.pop("sources_json", "[]"))
        results.append(d)
    return results


async def update_campaign(campaign_id: str, **fields: Any) -> dict[str, Any] | None:
    db = await get_db()
    sets: list[str] = []
    vals: list[Any] = []
    for key, val in fields.items():
        if key == "preferences":
            sets.append("preferences_json = ?")
            vals.append(json.dumps(val, ensure_ascii=False))
        elif key == "sources":
            sets.append("sources_json = ?")
            vals.append(json.dumps(val, ensure_ascii=False))
        elif key in ("name", "scan_frequency", "status"):
            sets.append(f"{key} = ?")
            vals.append(val)
    if not sets:
        return await get_campaign(campaign_id)
    sets.append("updated_at = ?")
    vals.append(_now())
    vals.append(campaign_id)
    await db.execute(f"UPDATE campaigns SET {', '.join(sets)} WHERE id = ?", vals)
    await db.commit()
    return await get_campaign(campaign_id)


# ---------------------------------------------------------------------------
# Listings
# ---------------------------------------------------------------------------


async def upsert_listing(
    campaign_id: str,
    listing_data: dict[str, Any],
    scan_id: str | None = None,
) -> dict[str, Any]:
    """Insert a listing or skip if duplicate (same fingerprint).

    Returns:
        dict with listing data and `_was_duplicate` flag indicating if the
        listing already existed (True) or was newly inserted (False).
    """
    db = await get_db()
    fp = _compute_fingerprint(listing_data)
    lid = _gen_id()
    now = _now()

    # Check for existing
    cursor = await db.execute(
        "SELECT * FROM listings WHERE campaign_id = ? AND fingerprint = ?",
        (campaign_id, fp),
    )
    existing = await cursor.fetchone()
    if existing:
        result = _row_to_dict(existing)
        result["_was_duplicate"] = True
        return result

    await db.execute(
        """INSERT INTO listings (
            id, campaign_id, fingerprint, stage,
            title, description, price_vnd, price_display, deposit_vnd,
            address, district, city, area_sqm, bedrooms, bathrooms,
            listing_url, thumbnail_url, posted_date, source_platform,
            landlord_name, landlord_phone, landlord_zalo,
            landlord_facebook_url, landlord_contact_method,
            match_score, scan_id, created_at, updated_at
        ) VALUES (?, ?, ?, 'new',
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?,
            ?, ?, ?, ?)""",
        (
            lid,
            campaign_id,
            fp,
            listing_data.get("title"),
            listing_data.get("description"),
            listing_data.get("price_vnd"),
            listing_data.get("price_display"),
            listing_data.get("deposit_vnd"),
            listing_data.get("address"),
            listing_data.get("district"),
            listing_data.get("city", "Ho Chi Minh"),
            listing_data.get("area_sqm"),
            listing_data.get("bedrooms"),
            listing_data.get("bathrooms"),
            listing_data.get("listing_url"),
            listing_data.get("thumbnail_url"),
            listing_data.get("posted_date"),
            listing_data.get("source_platform"),
            listing_data.get("landlord_name"),
            listing_data.get("landlord_phone"),
            listing_data.get("landlord_zalo"),
            listing_data.get("landlord_facebook_url"),
            listing_data.get("landlord_contact_method"),
            listing_data.get("match_score"),
            scan_id,
            now,
            now,
        ),
    )
    await db.commit()
    result = await get_listing(lid)
    if result:
        result["_was_duplicate"] = False
    return result  # type: ignore[return-value]


async def get_listings(
    campaign_id: str,
    stage: str | None = None,
) -> list[dict[str, Any]]:
    db = await get_db()
    if stage:
        cursor = await db.execute(
            "SELECT * FROM listings WHERE campaign_id = ? AND stage = ? ORDER BY updated_at DESC",
            (campaign_id, stage),
        )
    else:
        cursor = await db.execute(
            "SELECT * FROM listings WHERE campaign_id = ? ORDER BY updated_at DESC",
            (campaign_id,),
        )
    rows = await cursor.fetchall()
    return [_row_to_dict(r) for r in rows]


async def get_listing(listing_id: str) -> dict[str, Any] | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM listings WHERE id = ?", (listing_id,))
    row = await cursor.fetchone()
    return _row_to_dict(row) if row else None


async def update_listing_stage(
    listing_id: str,
    stage: str,
    skip_reason: str | None = None,
) -> dict[str, Any] | None:
    db = await get_db()
    now = _now()
    if skip_reason:
        await db.execute(
            "UPDATE listings SET stage = ?, skip_reason = ?, updated_at = ? WHERE id = ?",
            (stage, skip_reason, now, listing_id),
        )
    else:
        await db.execute(
            "UPDATE listings SET stage = ?, updated_at = ? WHERE id = ?",
            (stage, now, listing_id),
        )
    await db.commit()
    return await get_listing(listing_id)


async def update_listing_notes(listing_id: str, notes: str) -> dict[str, Any] | None:
    db = await get_db()
    await db.execute(
        "UPDATE listings SET user_notes = ?, updated_at = ? WHERE id = ?",
        (notes, _now(), listing_id),
    )
    await db.commit()
    return await get_listing(listing_id)


# ---------------------------------------------------------------------------
# Scans
# ---------------------------------------------------------------------------


async def create_scan(campaign_id: str, job_id: str) -> dict[str, Any]:
    db = await get_db()
    sid = _gen_id()
    now = _now()
    await db.execute(
        """INSERT INTO scans (id, campaign_id, job_id, status, started_at)
           VALUES (?, ?, ?, 'running', ?)""",
        (sid, campaign_id, job_id, now),
    )
    await db.commit()
    return {
        "id": sid,
        "campaign_id": campaign_id,
        "job_id": job_id,
        "status": "running",
        "started_at": now,
    }


async def complete_scan(
    scan_id: str,
    listings_found: int,
    new_listings: int,
    errors: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    db = await get_db()
    now = _now()
    await db.execute(
        """UPDATE scans SET status = 'completed', listings_found = ?, new_listings = ?,
           errors_json = ?, completed_at = ? WHERE id = ?""",
        (listings_found, new_listings, json.dumps(errors or []), now, scan_id),
    )
    await db.commit()
    cursor = await db.execute("SELECT * FROM scans WHERE id = ?", (scan_id,))
    row = await cursor.fetchone()
    if row:
        d = _row_to_dict(row)
        d["errors"] = json.loads(d.pop("errors_json", "[]"))
        return d
    return None


async def fail_scan(scan_id: str, errors: list[dict[str, Any]] | None = None) -> None:
    db = await get_db()
    now = _now()
    await db.execute(
        "UPDATE scans SET status = 'failed', errors_json = ?, completed_at = ? WHERE id = ?",
        (json.dumps(errors or []), now, scan_id),
    )
    await db.commit()


async def get_scans(campaign_id: str, limit: int = 10) -> list[dict[str, Any]]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM scans WHERE campaign_id = ? ORDER BY started_at DESC LIMIT ?",
        (campaign_id, limit),
    )
    rows = await cursor.fetchall()
    results = []
    for row in rows:
        d = _row_to_dict(row)
        d["errors"] = json.loads(d.pop("errors_json", "[]"))
        results.append(d)
    return results


async def get_latest_scan(campaign_id: str) -> dict[str, Any] | None:
    scans = await get_scans(campaign_id, limit=1)
    return scans[0] if scans else None


async def get_scan_by_job_id(job_id: str) -> dict[str, Any] | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM scans WHERE job_id = ?", (job_id,))
    row = await cursor.fetchone()
    if row:
        d = _row_to_dict(row)
        d["errors"] = json.loads(d.pop("errors_json", "[]"))
        return d
    return None


# ---------------------------------------------------------------------------
# Activity Log
# ---------------------------------------------------------------------------


async def add_activity(
    campaign_id: str,
    event_type: str,
    message: str,
    scan_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    db = await get_db()
    await db.execute(
        """INSERT INTO activity_log
           (campaign_id, scan_id, event_type, message, metadata_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (campaign_id, scan_id, event_type, message, json.dumps(metadata or {}), _now()),
    )
    await db.commit()


async def get_activities(
    campaign_id: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM activity_log WHERE campaign_id = ? ORDER BY created_at DESC LIMIT ?",
        (campaign_id, limit),
    )
    rows = await cursor.fetchall()
    results = []
    for row in rows:
        d = _row_to_dict(row)
        d["metadata"] = json.loads(d.pop("metadata_json", "{}"))
        results.append(d)
    return results


# ---------------------------------------------------------------------------
# Stats helpers
# ---------------------------------------------------------------------------


async def get_campaign_stats(campaign_id: str) -> dict[str, Any]:
    """Get quick stats for dashboard."""
    db = await get_db()

    # Total listings
    cursor = await db.execute(
        "SELECT COUNT(*) as cnt FROM listings WHERE campaign_id = ?", (campaign_id,)
    )
    total = (await cursor.fetchone())["cnt"]  # type: ignore[index]

    # By stage
    cursor = await db.execute(
        "SELECT stage, COUNT(*) as cnt FROM listings WHERE campaign_id = ? GROUP BY stage",
        (campaign_id,),
    )
    by_stage = {row["stage"]: row["cnt"] for row in await cursor.fetchall()}  # type: ignore[index]

    # New today
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    cursor = await db.execute(
        "SELECT COUNT(*) as cnt FROM listings WHERE campaign_id = ? AND created_at >= ?",
        (campaign_id, today),
    )
    new_today = (await cursor.fetchone())["cnt"]  # type: ignore[index]

    # Total scans
    cursor = await db.execute(
        "SELECT COUNT(*) as cnt FROM scans WHERE campaign_id = ?", (campaign_id,)
    )
    total_scans = (await cursor.fetchone())["cnt"]  # type: ignore[index]

    return {
        "total_listings": total,
        "by_stage": by_stage,
        "new_today": new_today,
        "total_scans": total_scans,
    }


# ---------------------------------------------------------------------------
# Outreach Messages
# ---------------------------------------------------------------------------


async def create_outreach_message(
    listing_id: str,
    campaign_id: str,
    draft_text: str,
    landlord_phone: str | None = None,
) -> dict[str, Any]:
    """Create a new outreach message draft."""
    db = await get_db()
    mid = _gen_id()
    now = _now()
    await db.execute(
        """INSERT INTO outreach_messages
           (id, listing_id, campaign_id, draft_text, landlord_phone, status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, 'drafted', ?, ?)""",
        (mid, listing_id, campaign_id, draft_text, landlord_phone, now, now),
    )
    await db.commit()
    return await get_outreach_message(mid)  # type: ignore[return-value]


async def get_outreach_message(message_id: str) -> dict[str, Any] | None:
    """Get a single outreach message by ID."""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM outreach_messages WHERE id = ?", (message_id,))
    row = await cursor.fetchone()
    return _row_to_dict(row) if row else None


async def get_outreach_for_listing(listing_id: str) -> list[dict[str, Any]]:
    """Get all outreach messages for a listing."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM outreach_messages WHERE listing_id = ? ORDER BY created_at DESC",
        (listing_id,),
    )
    rows = await cursor.fetchall()
    return [_row_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Area Research
# ---------------------------------------------------------------------------


async def create_area_research(
    listing_id: str,
    campaign_id: str,
    criteria: list[str],
    auto_outreach_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a new area research job in queued state."""
    db = await get_db()
    rid = _gen_id()
    now = _now()
    config = auto_outreach_config or {}
    await db.execute(
        """INSERT INTO area_research
           (id, listing_id, campaign_id, status, criteria_json,
            auto_outreach_enabled, auto_outreach_threshold,
            auto_outreach_conditions_json, created_at, updated_at)
           VALUES (?, ?, ?, 'queued', ?, ?, ?, ?, ?, ?)""",
        (
            rid,
            listing_id,
            campaign_id,
            json.dumps(criteria, ensure_ascii=False),
            1 if config.get("enabled") else 0,
            config.get("threshold"),
            json.dumps(config.get("must_pass", {}), ensure_ascii=False)
            if config.get("must_pass")
            else None,
            now,
            now,
        ),
    )
    await db.commit()
    return await get_area_research(rid)  # type: ignore[return-value]


def _parse_research_row(row: Any) -> dict[str, Any]:
    """Convert an area_research row to a dict with parsed JSON fields."""
    d = _row_to_dict(row)
    if not d:
        return d
    d["criteria"] = json.loads(d.pop("criteria_json", "[]"))
    d["scores"] = json.loads(d.pop("scores_json", "null") or "null")
    d["result"] = json.loads(d.pop("result_json", "null") or "null")
    d["street_view_urls"] = json.loads(d.pop("street_view_urls_json", "[]") or "[]")
    d["auto_outreach_conditions"] = json.loads(
        d.pop("auto_outreach_conditions_json", "null") or "null"
    )
    d["auto_outreach_enabled"] = bool(d.get("auto_outreach_enabled"))
    d["auto_outreach_triggered"] = bool(d.get("auto_outreach_triggered"))
    return d


async def get_area_research(research_id: str) -> dict[str, Any] | None:
    """Get a single area research record."""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM area_research WHERE id = ?", (research_id,))
    row = await cursor.fetchone()
    return _parse_research_row(row) if row else None


async def get_research_for_listing(listing_id: str) -> dict[str, Any] | None:
    """Get the latest research for a listing."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM area_research WHERE listing_id = ? ORDER BY created_at DESC LIMIT 1",
        (listing_id,),
    )
    row = await cursor.fetchone()
    return _parse_research_row(row) if row else None


async def list_research(
    campaign_id: str,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """List area research for a campaign, optionally filtered by status."""
    db = await get_db()
    if status:
        cursor = await db.execute(
            "SELECT * FROM area_research"
            " WHERE campaign_id = ? AND status = ?"
            " ORDER BY created_at DESC",
            (campaign_id, status),
        )
    else:
        cursor = await db.execute(
            "SELECT * FROM area_research WHERE campaign_id = ? ORDER BY created_at DESC",
            (campaign_id,),
        )
    rows = await cursor.fetchall()
    return [_parse_research_row(r) for r in rows]


async def update_research_status(
    research_id: str,
    status: str,
    error_message: str | None = None,
    tinyfish_job_id: str | None = None,
) -> dict[str, Any] | None:
    """Update research status and optional fields."""
    db = await get_db()
    now = _now()
    sets = ["status = ?", "updated_at = ?"]
    vals: list[Any] = [status, now]

    if status == "running":
        sets.append("started_at = ?")
        vals.append(now)
    if error_message is not None:
        sets.append("error_message = ?")
        vals.append(error_message)
    if tinyfish_job_id is not None:
        sets.append("tinyfish_job_id = ?")
        vals.append(tinyfish_job_id)

    vals.append(research_id)
    await db.execute(f"UPDATE area_research SET {', '.join(sets)} WHERE id = ?", vals)
    await db.commit()
    return await get_area_research(research_id)


async def complete_research(
    research_id: str,
    scores: dict[str, Any],
    result: dict[str, Any],
    verdict: str,
    overall_score: float,
    street_view_urls: list[str] | None = None,
) -> dict[str, Any] | None:
    """Mark research as done with full results."""
    db = await get_db()
    now = _now()
    await db.execute(
        """UPDATE area_research SET
           status = 'done', scores_json = ?, result_json = ?,
           verdict = ?, overall_score = ?, street_view_urls_json = ?,
           completed_at = ?, updated_at = ?
           WHERE id = ?""",
        (
            json.dumps(scores, ensure_ascii=False),
            json.dumps(result, ensure_ascii=False),
            verdict,
            overall_score,
            json.dumps(street_view_urls or [], ensure_ascii=False),
            now,
            now,
            research_id,
        ),
    )
    await db.commit()
    return await get_area_research(research_id)


async def link_research_to_listing(listing_id: str, research_id: str) -> None:
    """Link a research record to its listing."""
    db = await get_db()
    await db.execute(
        "UPDATE listings SET research_id = ?, updated_at = ? WHERE id = ?",
        (research_id, _now(), listing_id),
    )
    await db.commit()


async def update_outreach_status(
    message_id: str,
    status: str,
    final_text: str | None = None,
    zalo_user_id: str | None = None,
    error_message: str | None = None,
) -> dict[str, Any] | None:
    """Update outreach message status and related fields."""
    db = await get_db()
    now = _now()
    sets = ["status = ?", "updated_at = ?"]
    vals: list[Any] = [status, now]

    if final_text is not None:
        sets.append("final_text = ?")
        vals.append(final_text)

    if zalo_user_id is not None:
        sets.append("zalo_user_id = ?")
        vals.append(zalo_user_id)

    if error_message is not None:
        sets.append("error_message = ?")
        vals.append(error_message)

    if status == "sent":
        sets.append("sent_at = ?")
        vals.append(now)

    vals.append(message_id)
    await db.execute(f"UPDATE outreach_messages SET {', '.join(sets)} WHERE id = ?", vals)
    await db.commit()
    return await get_outreach_message(message_id)
