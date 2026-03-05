"""
Central application state — replaces st.session_state.
A single AppState instance is created in MainWindow and passed to all panels/pages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.data_types import FilterData, FutureData, ScenarioData, UIParams


@dataclass
class AppState:
    """Mutable state shared across all panels and pages."""

    # ── Sidebar widget outputs ─────────────────────────────────────────────
    params: Optional[UIParams] = None
    scenarios: Optional[ScenarioData] = None
    filter: Optional[FilterData] = None
    scoring_weights: List[Dict[str, float]] = field(default_factory=list)

    # ── Computation results ────────────────────────────────────────────────
    multi_ranking: Any = None               # MultiRankingResult
    comparisons: List[Any] = field(default_factory=list)  # List[StrategyComparison]
    mixture: Optional[Tuple[np.ndarray, np.ndarray, float]] = None
    future_data: Optional[FutureData] = None
    stats: Dict[str, Any] = field(default_factory=dict)
    all_imported_options: List[Any] = field(default_factory=list)  # List[Option]

    # ── History (persisted to JSON) ────────────────────────────────────────
    search_history: List[Any] = field(default_factory=list)

    # ── Processing flags ───────────────────────────────────────────────────
    is_processing: bool = False
