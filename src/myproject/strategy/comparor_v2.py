"""
Comparateur Multi-Structures - Version 2
=========================================
Comparateur simplifié pour les stratégies générées par option_generator_v2.
Utilise le même système de scoring que multi_structure_comparer.py.
Optimisé avec numpy pour des calculs vectorisés rapides.

✅ CORRECTIONS APPORTÉES (Audit 31/10/2025):
---------------------------------------------------
1. Surface Loss: scorer=_score_lower_better (plus petite perte = meilleur)
2. Risk/Reward: renommé "risk_over_reward" pour clarté
3. Reward/Risk: nouveau ratio "reward_over_risk" = surface_profit/surface_loss
4. Poids normalisés: division automatique par la somme (scores comparables)
5. Comparaison de méthodes: utilise scorer.__name__ au lieu de ==
6. Zéro inclus: filtre sur np.isfinite() au lieu de != 0
7. Robustesse: helpers _safe_value() et _safe_ratio() pour None/NaN/Inf
8. Greeks modérés: gamma/vega utilisent _score_lower_better (faible expo = meilleur)
9. Target performance: max(value, 0) pour récompenser uniquement les profits
10. Premium: scorer=_score_lower_better (crédit = meilleur)
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
        
        Note: Les poids seront automatiquement normalisés à 1.0 lors du calcul.
        """
        return [
            # ========== MÉTRIQUES FINANCIÈRES ==========
            MetricConfig(
                name='max_profit',
                weight=0.10,
                extractor=lambda s: self._safe_value(s.max_profit),
                normalizer=self._normalize_max,
                scorer=self._score_higher_better
            ),
            MetricConfig(
                name='risk_over_reward',  # Clarifié: Risk/Reward (plus petit = mieux)
                weight=0.10,
                extractor=lambda s: self._safe_value(s.risk_reward_ratio),
                normalizer=self._normalize_min_max,
                scorer=self._score_lower_better
            ),
            MetricConfig(
                name='profit_zone_width',
                weight=0.08,
                extractor=lambda s: self._safe_value(s.profit_zone_width),
                normalizer=self._normalize_max,
                scorer=self._score_higher_better
            ),
            MetricConfig(
                name='profit_at_target',  # Uniquement positif
                weight=0.08,
                extractor=lambda s: max(self._safe_value(s.profit_at_target_pct), 0.0),
                normalizer=self._normalize_max,
                scorer=self._score_higher_better
            ),
            
            # ========== SURFACES ==========
            MetricConfig(
                name='surface_profit',
                weight=0.12,
                extractor=lambda s: self._safe_value(s.surface_profit),
                normalizer=self._normalize_max,
                scorer=self._score_higher_better
            ),
            MetricConfig(
                name='surface_loss',  # ✅ CORRIGÉ: lower_better
                weight=0.08,
                extractor=lambda s: abs(self._safe_value(s.surface_loss)),
                normalizer=self._normalize_max,
                scorer=self._score_lower_better  # Plus petite perte = meilleur
            ),
            MetricConfig(
                name='surface_loss_ponderated',  # ✅ CORRIGÉ: lower_better
                weight=0.08,
                extractor=lambda s: abs(self._safe_value(s.surface_loss_ponderated)),
                normalizer=self._normalize_max,
                scorer=self._score_lower_better  # Plus petite perte = meilleur
            ),
            MetricConfig(
                name='surface_profit_ponderated',
                weight=0.08,
                extractor=lambda s: self._safe_value(s.surface_profit_ponderated),
                normalizer=self._normalize_max,
                scorer=self._score_higher_better
            ),
            MetricConfig(
                name='reward_over_risk',  # Ratio Profit/Loss (plus grand = mieux)
                weight=0.10,
                extractor=lambda s: self._safe_ratio(s.surface_profit, s.surface_loss),
                normalizer=self._normalize_min_max,
                scorer=self._score_higher_better
            ),
            
            # ========== GREEKS (optimisés pour neutralité) ==========
            MetricConfig(
                name='delta_neutral',
                weight=0.06,
                extractor=lambda s: abs(self._safe_value(s.total_delta)),
                normalizer=self._normalize_max,
                scorer=self._score_lower_better  # Plus proche de 0 = meilleur
            ),
            MetricConfig(
                name='gamma_low',  # ✅ CORRIGÉ: lower_better au lieu de moderate
                weight=0.04,
                extractor=lambda s: abs(self._safe_value(s.total_gamma)),
                normalizer=self._normalize_max,
                scorer=self._score_lower_better  # Faible exposition = meilleur
            ),
            MetricConfig(
                name='vega_low',  # ✅ CORRIGÉ: lower_better au lieu de moderate
                weight=0.04,
                extractor=lambda s: abs(self._safe_value(s.total_vega)),
                normalizer=self._normalize_max,
                scorer=self._score_lower_better  # Faible exposition = meilleur
            ),
            MetricConfig(
                name='theta_positive',
                weight=0.04,
                extractor=lambda s: self._safe_value(s.total_theta),
                normalizer=self._normalize_min_max,
                scorer=self._score_higher_better  # Theta positif = meilleur
            ),
            
            # ========== VOLATILITÉ ==========
            MetricConfig(
                name='implied_vol_moderate',
                weight=0.04,
                extractor=lambda s: self._safe_value(s.avg_implied_volatility),
                normalizer=self._normalize_min_max,
                scorer=self._score_moderate_better
            ),
            
            # ========== MÉTRIQUES GAUSSIENNES (MIXTURE) ==========
            MetricConfig(
                name='average_pnl',
                weight=0.15,
                extractor=lambda s: self._safe_value(s.average_pnl),
                normalizer=self._normalize_min_max,
                scorer=self._score_higher_better
            ),
            MetricConfig(
                name='sigma_pnl',
                weight=0.03,
                extractor=lambda s: self._safe_value(s.sigma_pnl),
                normalizer=self._normalize_max,
                scorer=self._score_lower_better  # Plus faible écart-type = meilleur
            ),
            
            # ========== COÛT/CRÉDIT ==========
            MetricConfig(
                name='premium_credit',  # Premium négatif (crédit) = meilleur
                weight=0.05,
                extractor=lambda s: self._safe_value(s.premium),
                normalizer=self._normalize_min_max,
                scorer=self._score_lower_better  # Plus négatif = meilleur
            ),
        ]
    
    # ========== HELPERS POUR EXTRACTION ROBUSTE ==========
    
    @staticmethod
    def _safe_value(value: Optional[float], default: float = 0.0) -> float:
        """Extrait une valeur en gérant None/NaN/Inf."""
        if value is None:
            return default
        if not np.isfinite(value):
            return default
        return float(value)
    
    @staticmethod
    def _safe_ratio(numerator: Optional[float], denominator: Optional[float], default: float = 0.0) -> float:
        """Calcule un ratio en gérant None/0/Inf."""
        num = StrategyComparerV2._safe_value(numerator, 0.0)
        den = StrategyComparerV2._safe_value(denominator, 0.0)
        
        if den == 0.0 or not np.isfinite(den):
            return default
        
        ratio = num / den
        return ratio if np.isfinite(ratio) else default
    
    # ========== NORMALISATEURS ==========
    
    @staticmethod
    def _normalize_max(values: List[float]) -> Tuple[float, float]:
        """
        Normalisation simple avec maximum.
        ✅ Garde les 0 (valeur informative), filtre uniquement None/NaN/Inf.
        """
        valid_values = [v for v in values if np.isfinite(v)]
        if not valid_values:
            return 0.0, 1.0
        max_val = max(valid_values)
        return 0.0, max_val if max_val != 0.0 else 1.0
    
    @staticmethod
    def _normalize_min_max(values: List[float]) -> Tuple[float, float]:
        """
        Normalisation avec minimum et maximum.
        ✅ Garde les 0 (valeur informative), filtre uniquement None/NaN/Inf.
        """
        valid_values = [v for v in values if np.isfinite(v)]
        if not valid_values:
            return 0.0, 1.0
        min_val = min(valid_values)
        max_val = max(valid_values)
        if max_val == min_val:
            return min_val, min_val + 1.0  # Éviter division par zéro
        return min_val, max_val
    
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
        
        ✅ Les poids sont automatiquement normalisés à 1.0 pour rendre les scores comparables.
        
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
        
        # ✅ Normaliser les poids à 1.0
        total_weight = sum(m.weight for m in self.metrics_config)
        if total_weight > 0:
            for metric in self.metrics_config:
                metric.weight /= total_weight
        
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
            
            #  Appeler  le normalizer
            min_val, max_val = metric.normalizer(values.tolist())
            
            if max_val > min_val or (max_val == min_val and max_val != 0):
                # Vérifier le type de scorer et appliquer le bon calcul
                # Appliquer le scorer de manière vectorisée
                #  Utiliser le nom de la méthode pour identifier le type
                scorer_name = metric.scorer.__name__
                
                if scorer_name == '_score_higher_better':
                    if max_val > 0:
                        scores_matrix[:, j] = np.clip(values / max_val, 0.0, 1.0)
                
                elif scorer_name == '_score_lower_better':
                    if max_val > min_val:
                        normalized = (values - min_val) / (max_val - min_val)
                        scores_matrix[:, j] = np.clip(1.0 - normalized, 0.0, 1.0)
                
                elif scorer_name == '_score_moderate_better':
                    if max_val > 0:
                        normalized = values / max_val
                        scores_matrix[:, j] = np.maximum(0.0, 1.0 - np.abs(normalized - 0.5) * 2.0)
                
                elif scorer_name == '_score_positive_better':
                    if max_val > min_val:
                        scores_matrix[:, j] = np.where(
                            values >= 0,
                            np.clip((values - min_val) / (max_val - min_val), 0.0, 1.0),
                            0.0
                        )
                elif scorer_name == '_score_negative_better':
                    # Supprimé car redondant avec _score_lower_better
                    if max_val > min_val:
                        normalized = (values - min_val) / (max_val - min_val)
                        scores_matrix[:, j] = np.clip(1.0 - normalized, 0.0, 1.0)
        
        # ============ ÉTAPE 3: CALCUL DU SCORE FINAL (vectorisé) ============
        # Multiplication matrice-vecteur: (n_strategies x n_metrics) @ (n_metrics)
        final_scores = scores_matrix @ weights
        
        # Assigner les scores aux stratégies
        for idx, strat in enumerate(strategies):
            strat.score = float(final_scores[idx])
        
        return strategies

