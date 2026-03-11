"""
Per-strategy alarm state tracking.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional


class RowState:
    """Tracks the warning countdown and confirmation for one strategy alarm."""

    __slots__ = ("warning_start", "confirmed")

    def __init__(self) -> None:
        self.warning_start: Optional[datetime] = None
        self.confirmed: bool = False  # True once alarm fired — prevents retry loop

    def reset(self) -> None:
        self.warning_start = None
        self.confirmed = False

    def elapsed(self) -> float:
        if self.warning_start is None:
            return 0.0
        return (datetime.now() - self.warning_start).total_seconds()
