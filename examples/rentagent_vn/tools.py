from __future__ import annotations

import json
from typing import Any

from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from loguru import logger

from examples.rentagent_vn.context import RentAgentContext


@tool
async def search_rentals(
    query: str,
    user_preference: str | None = None,
    *,
    runtime: ToolRuntime[RentAgentContext],
) -> dict[str, Any]:
    """Search rental listings across Vietnamese platforms
        (Facebook groups, nhatot.com, batdongsan.com.vn).

    Starts a background scrape and returns immediately. Results are
    delivered to this chat when ready (typically 3-8 minutes).

    Args:
        query: Natural-language description of the property the user
            wants. Include: district/area, bedrooms, budget, and any
            special requirements. Can be Vietnamese or English.
            Examples:
            - "2-bedroom apartment in District 7, under 15 million VND/month"
            - "phòng trọ gần Đại học Bách Khoa, dưới 5 triệu"
            - "pet-friendly studio in Binh Thanh with balcony"
        user_preference: Inferred preferences from the conversation that
            go beyond the explicit query. Pass patterns you've observed,
            e.g. "prefers high floors, dislikes ground floor units, wants
            quiet neighbourhood, needs parking".
    """
    runner = runtime.context.scrape_runner
    urls = runtime.context.rental_urls

    if runner is None:
        msg = "Scrape runner not found in context"
        logger.error(msg)
        return {
            "status": "error",
            "message": msg,
        }

    channel_context = {
        "user_role": runtime.context.user_role,
        "channel": runtime.context.channel,
        "user_id": runtime.context.user_id,
        "context_id": runtime.context.context_id,
        "chat_id": runtime.context.chat_id,
        "metadata": runtime.context.metadata,
    }
    job_id = await runner.start(
        urls=urls,
        query=query,
        channel_context=channel_context,
        user_preference=user_preference,
    )
    logger.info(f"search_rentals job_id: {job_id} started")

    return {
        "status": "started",
        "message": (
            "Notify the user that we are "
            f"searching {len(urls)} platform(s) in the background. "
            "Results will be delivered to this chat when ready."
        ),
    }


@tool
async def contact_landlord(landlord_name: str, landlord_phone: str, message: str) -> dict[str, Any]:
    """Contact a landlord about a rental listing.

    Args:
        landlord_name: Name of the landlord/poster.
        landlord_phone: Phone number of the landlord.
        message: The message to send to the landlord, e.g. asking about
            availability, price negotiation, or scheduling a viewing.
    """
    pass


@tool
async def research_area(area_name: str, city: str = "Ho Chi Minh") -> dict[str, Any]:
    """Research a neighbourhood or district for rental suitability.

    Args:
        area_name: Name of the district or neighbourhood, e.g.
            "Quan 7", "Binh Thanh", "Thao Dien".
        city: City name. Defaults to "Ho Chi Minh".
    """
    pass


@tool
async def extract_rental_criteria(
    location: str,
    bedrooms: int | None = None,
    bathrooms: int | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    min_area: int | None = None,
    max_area: int | None = None,
    property_type: str | None = None,
    notes: str | None = None,
) -> str:
    """Extract and save rental criteria from the user's requirements.

    Call this tool when the user describes their rental needs during onboarding.
    Extract the criteria from their message and pass them as parameters.
    The criteria will be sent to the frontend to pre-fill the search form.

    Args:
        location: District, city or area name (e.g., "District 7", "Binh Thanh, Ho Chi Minh").
        bedrooms: Number of bedrooms. Use 0 for studio.
        bathrooms: Number of bathrooms.
        min_price: Minimum monthly rent in VND. Convert shorthand:
            "5tr" or "5 triệu" = 5000000, "15M" = 15000000.
        max_price: Maximum monthly rent in VND. Same conversion rules.
        min_area: Minimum area in square meters.
        max_area: Maximum area in square meters.
        property_type: Type of property - "room", "apartment", "studio", "house".
        notes: Any other requirements (e.g., "pet-friendly", "has balcony").
    """
    preferences = {
        k: v
        for k, v in {
            "location": location,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "min_price": min_price,
            "max_price": max_price,
            "min_area": min_area,
            "max_area": max_area,
            "property_type": property_type,
            "notes": notes,
        }.items()
        if v is not None
    }

    result = {
        "status": "extracted",
        "preferences": preferences,
    }

    logger.info(f"Extracted rental criteria: {preferences}")

    return json.dumps(result)
