"""
Multi-Ranking Result Types
==========================

Dataclasses et utilitaires pour les résultats du scoring multi-poids.
Le C++ retourne N classements (un par jeu de poids) + un classement consensus.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from myproject.strategy.strategy_class import StrategyComparison

# Metric key → short human label (used in summaries)
_METRIC_LABELS: Dict[str, str] = {
    "avg_pnl_levrage": "Leverage",
    "roll_quarterly": "Roll",
    "avg_intra_life_pnl": "Dynamic",
    "average_pnl": "Gain",
    "max_loss": "Tail Risk",
    "premium": "Premium",
    "sigma_pnl": "StdDev",
    "delta_neutral": "ΔNeutral",
    "delta_levrage": "ΔLev",
}


@dataclass
class MultiRankingResult:
    """
    Résultat d'un scoring multi-poids.

    Attributes:
        per_set_strategies: Liste de listes — un classement par jeu de poids.
        consensus_strategies: Classement consensus (moyenne des rangs).
        weight_sets: Les jeux de poids utilisés.
        weight_set_names: Labels optionnels (ex: "R1 — Leverage").
        n_candidates: Nombre total de combinaisons évaluées.
    """
    per_set_strategies: List[List[StrategyComparison]] = field(default_factory=list)
    consensus_strategies: List[StrategyComparison] = field(default_factory=list)
    weight_sets: List[Dict[str, float]] = field(default_factory=list)
    weight_set_names: List[str] = field(default_factory=list)
    n_candidates: int = 0

    @property
    def n_sets(self) -> int:
        return len(self.weight_sets)

    @property
    def is_multi(self) -> bool:
        return self.n_sets > 1

    def get_set_label(self, set_index: int) -> str:
        """Return the preset name if available, else a short summary."""
        if set_index < len(self.weight_set_names) and self.weight_set_names[set_index]:
            return self.weight_set_names[set_index]
        return self.get_active_weights_summary(set_index)

    def get_active_weights_summary(self, set_index: int) -> str:
        """Short summary with human-readable metric labels."""
        if set_index >= self.n_sets:
            return ""
        ws = self.weight_sets[set_index]
        parts = [
            f"{_METRIC_LABELS.get(k, k)} {v:.0%}"
            for k, v in ws.items() if v > 0
        ]
        return ", ".join(parts) if parts else "(aucun poids)"

    def all_strategies_flat(self) -> List[StrategyComparison]:
        """
        Retourne le consensus si multi, sinon le premier (et unique) set.
        Utile pour la rétro-compatibilité avec le code qui attend une liste plate.
        """
        if self.is_multi:
            return self.consensus_strategies
        if self.per_set_strategies:
            return self.per_set_strategies[0]
        return []
