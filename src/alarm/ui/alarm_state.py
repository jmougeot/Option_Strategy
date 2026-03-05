"""
Per-strategy alarm state tracking.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from alarm.models.strategy import Strategy


class RowState:
    """Tracks the warning countdown and confirmation for one strategy alarm."""

    def __init__(self, strategy: Strategy) -> None:
        self.strategy = strategy
        self.warning_start: Optional[datetime] = None
        self.confirmed: bool = False  # True once WARN_DELAY seconds have elapsed

    def reset(self) -> None:
        self.warning_start = None
        self.confirmed = False

    def elapsed(self) -> float:
        if self.warning_start is None:
            return 0.0
        return (datetime.now() - self.warning_start).total_seconds()
