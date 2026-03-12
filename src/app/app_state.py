"""
Central application state — replaces st.session_state.
A single AppState instance is created in MainWindow and passed to all panels/pages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import numpy as np

from app.data_types import FilterData, FutureData, ScenarioData, UIParams

if TYPE_CHECKING:
    from option.option_class import Option
    from strategy.strategy_class import StrategyComparison
    from strategy.multi_ranking import MultiRankingResult
    from option.sabr import SABRCalibration


@dataclass
class ComputationResult:
    """Résultats atomiques d'un pipeline de calcul (Bloomberg + stratégies).

    Regroupé ici pour qu'une mise à jour de résultats soit toujours atomique
    (via AppState.store_result) et pour séparer les données générées par
    calcul des entrées UI.
    """
    multi_ranking: "MultiRankingResult"
    comparisons: "List[StrategyComparison]"
    mixture: Optional[Tuple[np.ndarray, np.ndarray, float]]
    future_data: Optional[FutureData]
    stats: Dict[str, Any]
    all_imported_options: "List[Option]" = field(default_factory=list)
    sabr_calibration: "Optional[SABRCalibration]" = None


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
    sabr_calibration: Optional[Any] = None  # SABRCalibration from last pipeline run

    # ── History (persisted to JSON) ────────────────────────────────────────
    search_history: List[Any] = field(default_factory=list)

    # ── Processing flags ───────────────────────────────────────────────────
    is_processing: bool = False

    def store_result(self, result: ComputationResult) -> None:
        """Stocke atomiquement les résultats d'un pipeline de calcul."""
        self.multi_ranking = result.multi_ranking
        self.comparisons = result.comparisons
        self.mixture = result.mixture
        self.future_data = result.future_data
        self.stats = result.stats
        self.all_imported_options = result.all_imported_options
        self.sabr_calibration = result.sabr_calibration
