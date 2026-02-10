"""
Multi-Ranking Result Types
==========================

Dataclasses et utilitaires pour les résultats du scoring multi-poids.
Le C++ retourne N classements (un par jeu de poids) + un classement consensus.
"""

from dataclasses import dataclass, field
from typing import Dict, List

from myproject.strategy.strategy_class import StrategyComparison


@dataclass
class MultiRankingResult:
    """
    Résultat d'un scoring multi-poids.

    Attributes:
        per_set_strategies: Liste de listes — un classement par jeu de poids.
        consensus_strategies: Classement consensus (moyenne des rangs).
        weight_sets: Les jeux de poids utilisés.
        n_candidates: Nombre total de combinaisons évaluées.
    """
    per_set_strategies: List[List[StrategyComparison]] = field(default_factory=list)
    consensus_strategies: List[StrategyComparison] = field(default_factory=list)
    weight_sets: List[Dict[str, float]] = field(default_factory=list)
    n_candidates: int = 0

    @property
    def n_sets(self) -> int:
        """Nombre de jeux de poids."""
        return len(self.weight_sets)

    @property
    def is_multi(self) -> bool:
        """True si plus d'un jeu de poids a été utilisé."""
        return self.n_sets > 1

    def get_active_weights_summary(self, set_index: int) -> str:
        """Résumé textuel d'un jeu de poids (clés avec poids > 0)."""
        if set_index >= self.n_sets:
            return ""
        ws = self.weight_sets[set_index]
        parts = [f"{k}: {v:.0%}" for k, v in ws.items() if v > 0]
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
