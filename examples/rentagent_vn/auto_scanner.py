"""Auto-scanner for campaigns with scan_frequency='auto'.

Runs as a background service that periodically checks which campaigns are due
for scanning based on their individual schedule settings stored in the database.

Each campaign has:
- scan_frequency: 'auto' | 'manual'
- auto_scan_hour: 0-23 (hour of day to run scan)
- auto_scan_timezone: timezone string (e.g., 'Asia/Ho_Chi_Minh')
- last_auto_scan_date: tracks when last scan ran to avoid duplicates
"""

from __future__ import annotations

import os
from collections.abc import Callable, Coroutine
from datetime import datetime
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

from loguru import logger

if TYPE_CHECKING:
    from apscheduler import AsyncScheduler

TriggerScanFn = Callable[[str, str | None], Coroutine[Any, Any, dict[str, Any]]]

# How often to check for campaigns due for scanning (in minutes)
CHECK_INTERVAL_MINUTES = int(os.getenv("RENTAGENT_AUTO_SCAN_CHECK_INTERVAL", "10"))


class AutoScanner:
    """Background scheduler that triggers scans for campaigns based on their schedule.

    Each campaign stores its own schedule (hour + timezone) in the database.
    The scanner checks periodically which campaigns are due and triggers scans.

    Args:
        trigger_scan: Async function to trigger a scan for a campaign.
            Signature: (campaign_id: str, query_override: str | None) -> dict
    """

    def __init__(self, trigger_scan: TriggerScanFn) -> None:
        self._trigger_scan = trigger_scan
        self._scheduler: AsyncScheduler | None = None
        self._enabled = os.getenv("RENTAGENT_AUTO_SCAN_ENABLED", "true").lower() in (
            "true",
            "1",
            "yes",
        )

    async def start(self) -> None:
        """Start the auto-scanner scheduler."""
        if not self._enabled:
            logger.info("Auto-scanner disabled via RENTAGENT_AUTO_SCAN_ENABLED")
            return

        try:
            from apscheduler import AsyncScheduler
            from apscheduler.datastores.memory import MemoryDataStore
            from apscheduler.eventbrokers.local import LocalEventBroker
            from apscheduler.triggers.interval import IntervalTrigger
        except ImportError as exc:
            raise ImportError(
                "AutoScanner requires apscheduler>=4. Install with: uv add 'apscheduler>=4'"
            ) from exc

        self._scheduler = AsyncScheduler(
            data_store=MemoryDataStore(),
            event_broker=LocalEventBroker(),
        )
        await self._scheduler.__aenter__()

        trigger = IntervalTrigger(minutes=CHECK_INTERVAL_MINUTES)
        await self._scheduler.add_schedule(
            self._check_and_run_scans,
            trigger,
            id="auto_scanner_check",
        )
        logger.info(f"Auto-scanner started (checking every {CHECK_INTERVAL_MINUTES} minutes)")

        await self._scheduler.start_in_background()

    async def stop(self) -> None:
        """Stop the auto-scanner scheduler."""
        if self._scheduler is not None:
            await self._scheduler.__aexit__(None, None, None)
            self._scheduler = None
            logger.info("Auto-scanner stopped")

    async def _check_and_run_scans(self) -> None:
        """Check which campaigns are due for scanning and trigger them."""
        from examples.rentagent_vn.db import queries

        logger.debug("Auto-scanner: checking for campaigns due for scanning")

        try:
            campaigns = await queries.list_auto_campaigns()
        except Exception as exc:
            logger.error(f"Auto-scanner: failed to query campaigns: {exc}")
            return

        if not campaigns:
            return

        triggered_count = 0

        for campaign in campaigns:
            campaign_id = campaign["id"]
            campaign_name = campaign.get("name", campaign_id)
            scan_hour = campaign.get("auto_scan_hour", 6)
            timezone_str = campaign.get("auto_scan_timezone", "Asia/Ho_Chi_Minh")
            last_scan_date = campaign.get("last_auto_scan_date")

            try:
                tz = ZoneInfo(timezone_str)
            except Exception:
                logger.warning(
                    f"Auto-scanner: invalid timezone '{timezone_str}' for campaign "
                    f"'{campaign_name}', using Asia/Ho_Chi_Minh"
                )
                tz = ZoneInfo("Asia/Ho_Chi_Minh")

            now = datetime.now(tz)
            today_date = now.strftime("%Y-%m-%d")
            current_hour = now.hour

            # Skip if not the scheduled hour
            if current_hour != scan_hour:
                continue

            # Skip if already scanned today
            if last_scan_date == today_date:
                continue

            # Trigger the scan
            try:
                logger.info(
                    f"Auto-scanner: triggering scan for campaign '{campaign_name}' "
                    f"(scheduled hour={scan_hour}, tz={timezone_str})"
                )

                await queries.add_activity(
                    campaign_id,
                    "auto_scan_start",
                    f"Auto-scan triggered (scheduled at {scan_hour}:00 {timezone_str})",
                )

                scan = await self._trigger_scan(campaign_id, None)

                # Mark as scanned to avoid duplicate runs
                await queries.mark_campaign_scanned(campaign_id, today_date)

                logger.info(f"Auto-scanner: scan {scan['id']} started for '{campaign_name}'")
                triggered_count += 1

            except Exception as exc:
                logger.error(f"Auto-scanner: failed to scan campaign '{campaign_name}': {exc}")
                try:
                    await queries.add_activity(
                        campaign_id,
                        "auto_scan_error",
                        f"Auto-scan failed: {exc}",
                    )
                except Exception:
                    pass

        if triggered_count > 0:
            logger.info(f"Auto-scanner: triggered {triggered_count} scan(s)")

    async def run_now(self) -> None:
        """Manually trigger a check cycle (for testing/debugging)."""
        await self._check_and_run_scans()
