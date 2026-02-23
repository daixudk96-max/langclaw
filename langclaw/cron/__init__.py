"""Cron scheduling system for langclaw.

Factory
-------
Use ``make_cron_manager`` to construct a ``CronManager`` with the correct
APScheduler ``data_store`` and ``event_broker`` from a ``CronConfig``.

Direct construction (e.g. for tests) is still supported::

    mgr = CronManager(bus=bus)               # memory + local (defaults)
    mgr = CronManager(bus, data_store=...)   # custom APScheduler objects
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langclaw.cron.scheduler import CronJob, CronManager, _schedule_to_cronjob

if TYPE_CHECKING:
    from apscheduler.abc import DataStore, EventBroker

    from langclaw.bus.base import BaseMessageBus
    from langclaw.config.schema import (
        CronConfig,
        CronDataStoreConfig,
        CronEventBrokerConfig,
    )


# ---------------------------------------------------------------------------
# Internal helpers — deferred imports keep startup fast and deps optional
# ---------------------------------------------------------------------------


def _make_data_store(cfg: CronDataStoreConfig) -> DataStore:
    """Construct an APScheduler DataStore from config."""
    if cfg.backend == "memory":
        from apscheduler.datastores.memory import MemoryDataStore

        return MemoryDataStore()

    if cfg.backend == "sqlite":
        try:
            from apscheduler.datastores.sqlalchemy import SQLAlchemyDataStore
        except ImportError as exc:
            raise ImportError(
                "SQLite cron data store requires sqlalchemy and aiosqlite. "
                "Install with: uv add sqlalchemy aiosqlite"
            ) from exc

        import re
        from pathlib import Path

        raw = cfg.sqlite.db_path
        expanded = str(Path(raw).expanduser())
        # Ensure parent dir exists so SQLAlchemy doesn't fail on first run.
        Path(expanded).parent.mkdir(parents=True, exist_ok=True)
        # APScheduler expects an async-compatible URL.
        url = re.sub(r"^(sqlite)", r"\1+aiosqlite", expanded)
        if not url.startswith("sqlite"):
            url = f"sqlite+aiosqlite:///{expanded}"
        return SQLAlchemyDataStore(url)

    if cfg.backend == "postgres":
        if not cfg.postgres.dsn:
            raise ValueError(
                "cron.data_store.postgres.dsn must be set when "
                "data_store.backend = 'postgres'."
            )
        try:
            from apscheduler.datastores.sqlalchemy import SQLAlchemyDataStore
        except ImportError as exc:
            raise ImportError(
                "Postgres cron data store requires sqlalchemy and asyncpg. "
                "Install with: uv add sqlalchemy asyncpg"
            ) from exc

        return SQLAlchemyDataStore(cfg.postgres.dsn)

    raise ValueError(
        f"Unknown cron data_store backend: {cfg.backend!r}. "
        "Choose 'memory', 'sqlite', or 'postgres'."
    )


def _make_event_broker(cfg: CronEventBrokerConfig) -> EventBroker:
    """Construct an APScheduler EventBroker from config."""
    if cfg.backend == "local":
        from apscheduler.eventbrokers.local import LocalEventBroker

        return LocalEventBroker()

    if cfg.backend == "asyncpg":
        if not cfg.asyncpg.dsn:
            raise ValueError(
                "cron.event_broker.asyncpg.dsn must be set when "
                "event_broker.backend = 'asyncpg'."
            )
        try:
            from apscheduler.eventbrokers.asyncpg import AsyncpgEventBroker
        except ImportError as exc:
            raise ImportError(
                "asyncpg event broker requires asyncpg. " "Install with: uv add asyncpg"
            ) from exc

        return AsyncpgEventBroker.from_dsn(cfg.asyncpg.dsn)

    if cfg.backend == "psycopg":
        if not cfg.psycopg.dsn:
            raise ValueError(
                "cron.event_broker.psycopg.dsn must be set when "
                "event_broker.backend = 'psycopg'."
            )
        try:
            from apscheduler.eventbrokers.psycopg import PsycopgEventBroker
        except ImportError as exc:
            raise ImportError(
                "psycopg event broker requires psycopg. "
                "Install with: uv add 'psycopg[binary]'"
            ) from exc

        return PsycopgEventBroker.from_dsn(cfg.psycopg.dsn)

    if cfg.backend == "redis":
        try:
            from apscheduler.eventbrokers.redis import RedisEventBroker
        except ImportError as exc:
            raise ImportError(
                "Redis event broker requires redis. " "Install with: uv add redis"
            ) from exc

        return RedisEventBroker(host=cfg.redis.host, port=cfg.redis.port)

    raise ValueError(
        f"Unknown cron event_broker backend: {cfg.backend!r}. "
        "Choose 'local', 'asyncpg', 'psycopg', or 'redis'."
    )


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


async def list_jobs_from_store(config: CronConfig) -> list[CronJob]:
    """Read persisted cron jobs directly from the data store.

    Opens a short-lived ``AsyncScheduler`` against the configured data store,
    reads all schedules, and maps them to ``CronJob`` objects.  The scheduler
    is torn down immediately after the read — no background task is started.

    This is the implementation behind ``langclaw cron list``: the CLI does not
    need a running gateway; it connects to the same SQLite/Postgres file the
    gateway uses and reads it directly.

    Args:
        config: ``CronConfig`` section from ``LangclawConfig``.

    Returns:
        List of ``CronJob`` objects found in the store.

    Raises:
        ValueError: if the data store backend is ``"memory"`` (nothing to read).
    """
    if config.data_store.backend == "memory":
        raise ValueError(
            "Cannot list jobs with the memory data store: no persistence. "
            "Set cron.data_store.backend to 'sqlite' or 'postgres'."
        )

    try:
        from apscheduler import AsyncScheduler
    except ImportError as exc:
        raise ImportError(
            "list_jobs_from_store requires apscheduler>=4. "
            "Install with: uv add 'apscheduler>=4'"
        ) from exc

    data_store = _make_data_store(config.data_store)
    event_broker = _make_event_broker(config.event_broker)

    async with AsyncScheduler(
        data_store=data_store,
        event_broker=event_broker,
    ) as scheduler:
        schedules = await scheduler.data_store.get_schedules()

    return [job for s in schedules if (job := _schedule_to_cronjob(s)) is not None]


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------


def make_cron_manager(
    bus: BaseMessageBus,
    config: CronConfig,
) -> CronManager:
    """Construct a ``CronManager`` from ``CronConfig``.

    Mirrors the ``make_message_bus`` / ``make_checkpointer_backend`` pattern:
    config drives which APScheduler ``data_store`` and ``event_broker``
    backends are instantiated.

    Args:
        bus:    Running ``BaseMessageBus`` — fired jobs publish
                ``InboundMessage`` objects here.
        config: ``CronConfig`` section from ``LangclawConfig``.

    Returns:
        A ``CronManager`` ready for ``await mgr.start()``.
    """
    data_store = _make_data_store(config.data_store)
    event_broker = _make_event_broker(config.event_broker)
    return CronManager(
        bus=bus,
        timezone=config.timezone,
        data_store=data_store,
        event_broker=event_broker,
    )


__all__ = [
    "CronJob",
    "CronManager",
    "list_jobs_from_store",
    "make_cron_manager",
]
