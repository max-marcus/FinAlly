"""Periodic portfolio snapshot background task."""

from __future__ import annotations

import asyncio
import logging

from .portfolio import PortfolioService

logger = logging.getLogger(__name__)


async def run_snapshot_loop(portfolio: PortfolioService, interval: float = 30.0) -> None:
    """Record a snapshot every `interval` seconds; never lets exceptions escape."""
    while True:
        try:
            await asyncio.sleep(interval)
            portfolio.snapshot()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("snapshot failed")
