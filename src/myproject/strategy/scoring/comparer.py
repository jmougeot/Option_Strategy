"""
Comparateur Multi-Structures - Version 2
=========================================
Comparateur simplifié et optimisé pour les stratégies.
"""

from typing import List, Dict, Optional
from copy import deepcopy
import numpy as np

from myproject.strategy.comparison_class import StrategyComparison
from myproject.strategy.scoring.metrics_config import MetricConfig, create_metrics_config



class StrategyComparerV2:
    """
    Comparateur simplifié pour stratégies provenant de generate_all_combinations.

    Usage:
        comparer = StrategyComparerV2()
        ranked_strategies = comparer.compare_and_rank(
            strategies=all_strategies,
            top_n=10,
            weights={'average_pnl': 0.35, 'roll': 0.15, ...}
        )
    """

    def __init__(self):
        """Initialise le comparateur avec les configurations de métriques."""
        self._base_metrics_config = create_metrics_config()

    def compare_and_rank(
        self,
        strategies: List[StrategyComparison],
        top_n: int = 10,
        weights: Optional[Dict[str, float]] = None,
    ) -> List[StrategyComparison]:
        """
        Compare et classe les stratégies selon un système de scoring multi-critères.

        Args:
            strategies: Liste des stratégies à comparer
            top_n: Nombre de meilleures stratégies à retourner
            weights: Poids personnalisés partiels (les autres gardent leur valeur par défaut)
        """
        if not strategies:
            print("⚠️ Aucune stratégie à comparer")
            return []

        metrics_config = deepcopy(self._base_metrics_config)

        # Appliquer les poids personnalisés si fournis
        if weights:
            for metric in metrics_config:
                if metric.name in weights:
                    metric.weight = weights[metric.name]

        # Normaliser les poids à 1.0
        total_weight = sum(m.weight for m in metrics_config)
        if total_weight > 0:
            for metric in metrics_config:
                metric.weight /= total_weight

        # Calculer les scores
        strategies = self._calculate_scores(strategies, metrics_config)

        # Trier par score décroissant
        strategies.sort(key=lambda x: x.score, reverse=True)

        # Limiter au top_n et assigner les rangs
        strategies = strategies[:top_n]
        for i, strat in enumerate(strategies, 1):
            strat.rank = i

        print(f"\n✅ {len(strategies)} stratégies classées (top {top_n})")

        return strategies

    def _calculate_scores(
        self, strategies: List[StrategyComparison], metrics_config: List[MetricConfig]
    ) -> List[StrategyComparison]:
        """
        Calcule les scores composites pour chaque stratégie avec numpy (optimisé).
        """
        if not strategies:
            return strategies

        n_strategies = len(strategies)
        n_metrics = len(metrics_config)

        # ============ ÉTAPE 1: EXTRACTION EN ARRAY NUMPY ============
        metric_matrix = np.zeros((n_strategies, n_metrics))
        weights = np.zeros(n_metrics)

        for j, metric in enumerate(metrics_config):
            # Extraction robuste: attraper les erreurs individuelles
            extracted = []
            for s in strategies:
                try:
                    val = metric.extractor(s)
                    extracted.append(val if np.isfinite(val) else 0.0)
                except Exception:
                    extracted.append(0.0)
            metric_matrix[:, j] = extracted
            weights[j] = metric.weight

        # ============ ÉTAPE 2: NORMALISATION VECTORISÉE ============
        scores_matrix = np.zeros_like(metric_matrix)

        for j, metric in enumerate(metrics_config):
            values = metric_matrix[:, j]
            min_val, max_val = metric.normalizer(values.tolist())

            if max_val > min_val or (max_val == min_val and max_val != 0):
                scorer_name = metric.scorer.__name__

                if scorer_name == "score_higher_better":
                    if max_val > 0:
                        scores_matrix[:, j] = np.clip(values / max_val, 0.0, 1.0)

                elif scorer_name == "score_lower_better":
                    if max_val > min_val:
                        normalized = (values - min_val) / (max_val - min_val)
                        scores_matrix[:, j] = np.clip(1.0 - normalized, 0.0, 1.0)

                elif scorer_name == "score_moderate_better":
                    if max_val > 0:
                        normalized = values / max_val
                        scores_matrix[:, j] = np.maximum(
                            0.0, 1.0 - np.abs(normalized - 0.5) * 2.0
                        )

                elif scorer_name == "score_positive_better":
                    if max_val > min_val:
                        scores_matrix[:, j] = np.where(
                            values >= 0,
                            np.clip((values - min_val) / (max_val - min_val), 0.0, 1.0),
                            0.0,
                        )

        # ============ ÉTAPE 3: CALCUL DU SCORE FINAL (vectorisé) ============
        final_scores = scores_matrix @ weights

        for idx, strat in enumerate(strategies):
            strat.score = float(final_scores[idx])

        return strategies
