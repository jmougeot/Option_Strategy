"""
Comparateur Multi-Structures - Version 2
=========================================
Comparateur simplifié pour les stratégies générées par option_generator_v2.
Utilise le même système de scoring que multi_structure_comparer.py.
Optimisé avec numpy pour des calculs vectorisés rapides.
"""

from typing import List, Dict, Optional, Callable, Tuple
from dataclasses import dataclass
import numpy as np
from myproject.strategy.comparison_class import StrategyComparison


@dataclass
class MetricConfig:
    """Configuration pour une métrique de scoring."""
    name: str
    weight: float
    extractor: Callable[[StrategyComparison], float]
    normalizer: Callable[[List[float]], Tuple[float, float]]
    scorer: Callable[[float, float, float], float]


class StrategyComparerV2:
    """
    Comparateur simplifié pour stratégies provenant de generate_all_combinations.
    
    Usage:
        comparer = StrategyComparerV2()
        ranked_strategies = comparer.compare_and_rank(
            strategies=all_strategies,
            top_n=10,
            weights={'surface_profit': 0.35, 'profit_loss_ratio': 0.15, ...}
        )
    """
    
    def __init__(self):
        """Initialise le comparateur avec les configurations de métriques."""
        self.metrics_config = self._create_metrics_config()
    
    def _create_metrics_config(self) -> List[MetricConfig]:
        """
        Crée la configuration de toutes les métriques.
        Facilite l'ajout/suppression de métriques.
        """
        return [
            # ========== MÉTRIQUES FINANCIÈRES ==========
            MetricConfig(
                name='max_profit',
                weight=0.10,
                extractor=lambda s: s.max_profit if s.max_profit != float('inf') else 0.0,
                normalizer=self._normalize_max,
                scorer=self._score_higher_better
            ),
            MetricConfig(
                name='risk_reward',
                weight=0.10,
                extractor=lambda s: s.risk_reward_ratio if s.risk_reward_ratio != float('inf') else 0.0,
                normalizer=self._normalize_min_max,
                scorer=self._score_lower_better
            ),
            MetricConfig(
                name='profit_zone',
                weight=0.08,
                extractor=lambda s: s.profit_zone_width if s.profit_zone_width != float('inf') else 0.0,
                normalizer=self._normalize_max,
                scorer=self._score_higher_better
            ),
            MetricConfig(
                name='target_performance',
                weight=0.08,
                extractor=lambda s: abs(s.profit_at_target_pct),
                normalizer=self._normalize_max,
                scorer=self._score_higher_better
            ),
            
            # ========== SURFACES ==========
            MetricConfig(
                name='surface_profit',
                weight=0.12,
                extractor=lambda s: s.surface_profit if (s.surface_profit is not None and s.surface_profit > 0) else 0.0,
                normalizer=self._normalize_max,
                scorer=self._score_higher_better
            ),
            MetricConfig(
                name='surface_loss',
                weight=0.08,
                extractor=lambda s: abs(s.surface_loss) if (s.surface_loss is not None and s.surface_loss != 0) else 0.0,
                normalizer=self._normalize_max,
                scorer=self._score_higher_better
            ),

            MetricConfig(
                name='surface_loss_ponderated',
                weight=0.08,
                extractor=lambda s: abs(s.surface_loss_ponderated) if s.surface_loss_ponderated != 0 else 0.0,
                normalizer=self._normalize_max,
                scorer=self._score_higher_better
            ),

            MetricConfig(
                name='surface_profit_ponderated',
                weight=0.08,
                extractor=lambda s: s.surface_profit_ponderated if s.surface_profit_ponderated > 0 else 0.0,
                normalizer=self._normalize_max,
                scorer=self._score_higher_better
            ),

            MetricConfig(
                name='profit_loss_ratio',
                weight=0.10,
                extractor=lambda s: (s.surface_profit / s.surface_loss) if (s.surface_profit is not None and s.surface_loss is not None and s.surface_loss > 0) else 0.0,
                normalizer=self._normalize_min_max,
                scorer=self._score_higher_better
            ),
            
            # ========== GREEKS ==========
            MetricConfig(
                name='delta_neutral',
                weight=0.00,
                extractor=lambda s: abs(s.total_delta),
                normalizer=self._normalize_max,
                scorer=self._score_lower_better
            ),
            MetricConfig(
                name='gamma_exposure',
                weight=0.00,
                extractor=lambda s: abs(s.total_gamma),
                normalizer=self._normalize_max,
                scorer=self._score_moderate_better
            ),
            MetricConfig(
                name='vega_exposure',
                weight=0.00,
                extractor=lambda s: abs(s.total_vega),
                normalizer=self._normalize_max,
                scorer=self._score_moderate_better
            ),
            MetricConfig(
                name='theta_positive',
                weight=0.05,
                extractor=lambda s: s.total_theta,
                normalizer=self._normalize_min_max,
                scorer=self._score_positive_better
            ),
            
            # ========== VOLATILITÉ ==========
            MetricConfig(
                name='implied_vol',
                weight=0.00,
                extractor=lambda s: s.avg_implied_volatility if s.avg_implied_volatility > 0 else 0.0,
                normalizer=self._normalize_min_max,
                scorer=self._score_moderate_better
            ),
            
            # ========== MÉTRIQUES GAUSSIENNES (MIXTURE) ==========
            MetricConfig(
                name='average_pnl',
                weight=0.70,
                extractor=lambda s: s.average_pnl if s.average_pnl is not None else 0.0,
                normalizer=self._normalize_min_max,
                scorer=self._score_higher_better
            ),
            MetricConfig(
                name='sigma_pnl',
                weight=0.05,
                extractor=lambda s: s.sigma_pnl if s.sigma_pnl is not None else 0.0,
                normalizer=self._normalize_max,
                scorer=self._score_lower_better  # Plus faible écart-type = meilleur
            ),
            
        ]
    
    # ========== NORMALISATEURS ==========
    
    @staticmethod
    def _normalize_max(values: List[float]) -> Tuple[float, float]:
        """Normalisation simple avec maximum."""
        valid_values = [v for v in values if v != 0.0]
        max_val = max(valid_values) if valid_values else 1.0
        return 0.0, max_val
    
    @staticmethod
    def _normalize_min_max(values: List[float]) -> Tuple[float, float]:
        """Normalisation avec minimum et maximum."""
        valid_values = [v for v in values if v != 0.0]
        if not valid_values:
            return 0.0, 1.0
        return min(valid_values), max(valid_values)
    
    # ========== SCORERS ==========
    
    @staticmethod
    def _score_higher_better(value: float, min_val: float, max_val: float) -> float:
        """Score normalisé: plus élevé = meilleur."""
        if max_val <= 0:
            return 0.0
        return value / max_val
    
    @staticmethod
    def _score_lower_better(value: float, min_val: float, max_val: float) -> float:
        """Score normalisé inversé: plus bas = meilleur."""
        if max_val <= min_val:
            return 0.0
        normalized = (value - min_val) / (max_val - min_val)
        return 1.0 - normalized
    
    @staticmethod
    def _score_moderate_better(value: float, min_val: float, max_val: float) -> float:
        """Score favorisant les valeurs modérées (autour de 0.5 de la plage)."""
        if max_val <= 0:
            return 0.0
        normalized = value / max_val
        # Score optimal à 0.5, pénalise les extrêmes
        score = 1.0 - abs(normalized - 0.5) * 2.0
        return max(0.0, score)
    
    @staticmethod
    def _score_positive_better(value: float, min_val: float, max_val: float) -> float:
        """Score favorisant les valeurs positives."""
        if value >= 0 and max_val > min_val:
            return (value - min_val) / (max_val - min_val)
        return 0.0
    
    def compare_and_rank(self,
                        strategies: List[StrategyComparison],
                        top_n: int = 10,
                        weights: Optional[Dict[str, float]] = None) -> List[StrategyComparison]:
        """
        Compare et classe les stratégies selon un système de scoring multi-critères.
        
        Example:
            >>> comparer = StrategyComparerV2()
            >>> best = comparer.compare_and_rank(strategies, top_n=5)
            >>> for s in best:
            ...     print(f"{s.rank}. {s.strategy_name} - Score: {s.score:.3f}")
        """
        if not strategies:
            print("⚠️ Aucune stratégie à comparer")
            return []
        
        # Appliquer les poids personnalisés si fournis
        if weights:
            for metric in self.metrics_config:
                if metric.name in weights:
                    metric.weight = weights[metric.name]
        
        # Calculer les scores
        strategies = self._calculate_scores(strategies)
        
        # Trier par score décroissant
        strategies.sort(key=lambda x: x.score, reverse=True)
        
        # Limiter au top_n et assigner les rangs
        strategies = strategies[:top_n]
        for i, strat in enumerate(strategies, 1):
            strat.rank = i
        
        print(f"✅ {len(strategies)} stratégies classées (top {top_n})")
        
        return strategies
    
    def _calculate_scores(self, strategies: List[StrategyComparison]) -> List[StrategyComparison]:
        """
        Calcule les scores composites pour chaque stratégie avec numpy (optimisé).
        
        Utilise des arrays numpy pour des calculs vectorisés rapides.
        ~10-100x plus rapide que les boucles Python pour de grandes listes.
        """
        if not strategies:
            return strategies
        
        n_strategies = len(strategies)
        n_metrics = len(self.metrics_config)
        
        # ============ ÉTAPE 1: EXTRACTION EN ARRAY NUMPY ============
        # Créer une matrice (n_strategies x n_metrics) avec toutes les valeurs
        metric_matrix = np.zeros((n_strategies, n_metrics))
        weights = np.zeros(n_metrics)
        
        for j, metric in enumerate(self.metrics_config):
            # Extraire toutes les valeurs pour cette métrique (vectorisé)
            metric_matrix[:, j] = [metric.extractor(s) for s in strategies]
            weights[j] = metric.weight
        
        # ============ ÉTAPE 2: NORMALISATION VECTORISÉE ============
        # Pour chaque métrique, calculer min/max et normaliser
        scores_matrix = np.zeros_like(metric_matrix)
        
        for j, metric in enumerate(self.metrics_config):
            values = metric_matrix[:, j]
            
            # Calculer les paramètres de normalisation
            valid_mask = values != 0.0
            valid_values = values[valid_mask]
            
            if len(valid_values) > 0:
                if metric.normalizer == self._normalize_max:
                    min_val, max_val = 0.0, np.max(valid_values)
                else:  # _normalize_min_max
                    min_val, max_val = np.min(valid_values), np.max(valid_values)
                
                # Appliquer le scorer de manière vectorisée
                if metric.scorer == self._score_higher_better:
                    if max_val > 0:
                        scores_matrix[:, j] = values / max_val
                
                elif metric.scorer == self._score_lower_better:
                    if max_val > min_val:
                        normalized = (values - min_val) / (max_val - min_val)
                        scores_matrix[:, j] = 1.0 - normalized
                
                elif metric.scorer == self._score_moderate_better:
                    if max_val > 0:
                        normalized = values / max_val
                        scores_matrix[:, j] = np.maximum(0.0, 1.0 - np.abs(normalized - 0.5) * 2.0)
                
                elif metric.scorer == self._score_positive_better:
                    if max_val > min_val:
                        scores_matrix[:, j] = np.where(
                            values >= 0,
                            (values - min_val) / (max_val - min_val),
                            0.0
                        )
        
        # ============ ÉTAPE 3: CALCUL DU SCORE FINAL (vectorisé) ============
        # Multiplication matrice-vecteur: (n_strategies x n_metrics) @ (n_metrics)
        final_scores = scores_matrix @ weights
        
        # Assigner les scores aux stratégies
        for idx, strat in enumerate(strategies):
            strat.score = float(final_scores[idx])
        
        return strategies
    
