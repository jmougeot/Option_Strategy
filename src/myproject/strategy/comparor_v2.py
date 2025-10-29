"""
Comparateur Multi-Structures - Version 2
=========================================
Comparateur simplifié pour les stratégies générées par option_generator_v2.
Utilise le même système de scoring que multi_structure_comparer.py.
"""

from typing import List, Dict, Optional, Callable, Tuple
from dataclasses import dataclass
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
                extractor=lambda s: s.surface_profit if s.surface_profit > 0 else 0.0,
                normalizer=self._normalize_max,
                scorer=self._score_higher_better
            ),
            MetricConfig(
                name='surface_loss',
                weight=0.08,
                extractor=lambda s: abs(s.surface_loss) if s.surface_loss != 0 else 0.0,
                normalizer=self._normalize_max,
                scorer=self._score_lower_better
            ),
            MetricConfig(
                name='profit_loss_ratio',
                weight=0.12,
                extractor=lambda s: s.surface_profit / s.surface_loss if s.surface_loss > 0 else 0.0,
                normalizer=self._normalize_min_max,
                scorer=self._score_higher_better
            ),
            
            # ========== GREEKS ==========
            MetricConfig(
                name='delta_neutral',
                weight=0.06,
                extractor=lambda s: abs(s.total_delta),
                normalizer=self._normalize_max,
                scorer=self._score_lower_better
            ),
            MetricConfig(
                name='gamma_exposure',
                weight=0.04,
                extractor=lambda s: abs(s.total_gamma),
                normalizer=self._normalize_max,
                scorer=self._score_moderate_better
            ),
            MetricConfig(
                name='vega_exposure',
                weight=0.04,
                extractor=lambda s: abs(s.total_vega),
                normalizer=self._normalize_max,
                scorer=self._score_moderate_better
            ),
            MetricConfig(
                name='theta_positive',
                weight=0.04,
                extractor=lambda s: s.total_theta,
                normalizer=self._normalize_min_max,
                scorer=self._score_positive_better
            ),
            
            # ========== VOLATILITÉ ==========
            MetricConfig(
                name='implied_vol',
                weight=0.04,
                extractor=lambda s: s.avg_implied_volatility if s.avg_implied_volatility > 0 else 0.0,
                normalizer=self._normalize_min_max,
                scorer=self._score_moderate_better
            ),
            
            # ========== MÉTRIQUES GAUSSIENNES (MIXTURE) ==========
            MetricConfig(
                name='average_pnl',
                weight=0.06,
                extractor=lambda s: s.average_pnl if s.average_pnl is not None else 0.0,
                normalizer=self._normalize_min_max,
                scorer=self._score_higher_better
            ),
            MetricConfig(
                name='sigma_pnl',
                weight=0.04,
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
    
    def _calculate_scores(self, 
                         strategies: List[StrategyComparison]) -> List[StrategyComparison]:
        """
        Calcule les scores composites pour chaque stratégie en UN SEUL PARCOURS.
        
        Algorithme optimisé:
        1. Premier parcours: extraire toutes les valeurs et calculer min/max
        2. Deuxième parcours: calculer les scores pour chaque stratégie
        """
        if not strategies:
            return strategies
        
        # ============ ÉTAPE 1: EXTRACTION ET NORMALISATION (1 parcours) ============
        
        # Dictionnaire pour stocker les valeurs extraites par métrique
        metric_values: Dict[str, List[float]] = {}
        metric_params: Dict[str, Tuple[float, float]] = {}
        
        # Extraire toutes les valeurs en un seul parcours
        for metric in self.metrics_config:
            metric_values[metric.name] = [metric.extractor(s) for s in strategies]
        
        # Calculer les paramètres de normalisation pour chaque métrique
        for metric in self.metrics_config:
            metric_params[metric.name] = metric.normalizer(metric_values[metric.name])
        
        # ============ ÉTAPE 2: CALCUL DES SCORES (1 parcours) ============
        
        for idx, strat in enumerate(strategies):
            score = 0.0
            
            # Parcourir toutes les métriques configurées
            for metric in self.metrics_config:
                value = metric_values[metric.name][idx]
                min_val, max_val = metric_params[metric.name]
                
                # Calculer le score normalisé pour cette métrique
                metric_score = metric.scorer(value, min_val, max_val)
                
                # Ajouter au score total avec le poids
                score += metric_score * metric.weight
            
            strat.score = score
        
        return strategies
    
