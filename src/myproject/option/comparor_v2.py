"""
Comparateur Multi-Structures - Version 2
=========================================
Comparateur simplifié pour les stratégies générées par option_generator_v2.
Utilise le même système de scoring que multi_structure_comparer.py.
"""

from typing import List, Dict, Optional
from myproject.option.comparison_class import StrategyComparison


class StrategyComparerV2:
    """
    Comparateur simplifié pour stratégies provenant de generate_all_combinations.
    
    Usage:
        comparer = StrategyComparerV2()
        ranked_strategies = comparer.compare_and_rank(
            strategies=all_strategies,
            top_n=10,
            weights={'surface_gauss': 0.35, 'profit_loss_ratio': 0.15, ...}
        )
    """
    
    def __init__(self):
        """Initialise le comparateur."""
        pass
    
    def compare_and_rank(self,
                        strategies: List[StrategyComparison],
                        top_n: int = 10,
                        weights: Optional[Dict[str, float]] = None) -> List[StrategyComparison]:
        """
        Compare et classe les stratégies selon un système de scoring multi-critères.
        
        Args:
            strategies: Liste de StrategyComparison à comparer
            top_n: Nombre de meilleures stratégies à retourner
            weights: Poids personnalisés pour le scoring (optionnel)
                - 'max_profit': Poids pour le profit maximum (défaut: 0.15)
                - 'risk_reward': Poids pour le ratio risque/récompense (défaut: 0.15)
                - 'profit_zone': Poids pour la largeur de zone de profit (défaut: 0.10)
                - 'target_performance': Poids pour la performance au prix cible (défaut: 0.10)
                - 'surface_gauss': Poids pour le profit pondéré gaussien (défaut: 0.35)
                - 'profit_loss_ratio': Poids pour le ratio surface profit/loss (défaut: 0.15)
        
        Returns:
            Liste des top_n meilleures stratégies, triées par score décroissant,
            avec score et rank assignés.
            
        Example:
            >>> strategies = generator.generate_all_combinations(...)
            >>> comparer = StrategyComparerV2()
            >>> best = comparer.compare_and_rank(strategies, top_n=5)
            >>> for s in best:
            ...     print(f"{s.rank}. {s.strategy_name} - Score: {s.score:.3f}")
        """
        if not strategies:
            print("⚠️ Aucune stratégie à comparer")
            return []
        
        # Poids par défaut (identiques à multi_structure_comparer.py)
        if weights is None:
            weights = {
                'max_profit': 0.15,           # Profit max
                'risk_reward': 0.15,          # Ratio risque/récompense
                'profit_zone': 0.10,          # Largeur de zone de profit
                'target_performance': 0.10,   # Performance au prix cible
                'surface_gauss': 0.35,        # Profit pondéré par gaussienne (prioritaire)
                'profit_loss_ratio': 0.15     # Ratio surface_profit/surface_loss
            }
        
        # Calculer les scores
        strategies = self._calculate_scores(strategies, weights)
        
        # Trier par score décroissant
        strategies.sort(key=lambda x: x.score, reverse=True)
        
        # Limiter au top_n et assigner les rangs
        strategies = strategies[:top_n]
        for i, strat in enumerate(strategies, 1):
            strat.rank = i
        
        print(f"✅ {len(strategies)} stratégies classées (top {top_n})")
        
        return strategies
    
    def _calculate_scores(self, 
                         strategies: List[StrategyComparison], 
                         weights: Dict[str, float]) -> List[StrategyComparison]:
        """
        Calcule les scores composites pour chaque stratégie.
        Utilise la même logique que multi_structure_comparer.py.
        """
        if not strategies:
            return strategies
        
        # ============ NORMALISATION DES MÉTRIQUES ============
        
        # 1. Profit maximum (filtrer les infinités)
        finite_profits = [s.max_profit for s in strategies if s.max_profit != float('inf')]
        max_profit_val = max(finite_profits) if finite_profits else 1.0
        
        # 2. Largeur zone de profit
        finite_zones = [s.profit_zone_width for s in strategies if s.profit_zone_width != float('inf')]
        max_zone_width = max(finite_zones) if finite_zones else 1.0
        
        # 3. Performance au prix cible
        target_perfs = [abs(s.profit_at_target_pct) for s in strategies]
        max_target_perf = max(target_perfs) if target_perfs else 1.0
        
        # 4. Risk/reward ratio (éviter les infinités)
        finite_rr = [s.risk_reward_ratio for s in strategies if s.risk_reward_ratio != float('inf')]
        min_rr = min(finite_rr) if finite_rr else 0.0
        max_rr = max(finite_rr) if finite_rr else 1.0
        
        # 6. Ratio profit/loss surfaces
        profit_loss_ratios = []
        for s in strategies:
            if s.surface_loss > 0:
                ratio = s.surface_profit / s.surface_loss
                profit_loss_ratios.append(ratio)
        min_pl_ratio = min(profit_loss_ratios) if profit_loss_ratios else 0.0
        max_pl_ratio = max(profit_loss_ratios) if profit_loss_ratios else 1.0
        
        # ============ CALCUL DES SCORES ============
        
        for strat in strategies:
            score = 0.0
            
            # 1. Max profit (normalisé 0-1)
            if 'max_profit' in weights and max_profit_val > 0 and strat.max_profit != float('inf'):
                score += (strat.max_profit / max_profit_val) * weights['max_profit']
            
            # 2. Risk/reward (inversé : plus petit = meilleur)
            if 'risk_reward' in weights and strat.risk_reward_ratio != float('inf') and max_rr > min_rr:
                normalized_rr = (strat.risk_reward_ratio - min_rr) / (max_rr - min_rr)
                score += (1 - normalized_rr) * weights['risk_reward']
            
            # 3. Profit zone width (plus large = meilleur)
            if 'profit_zone' in weights and strat.profit_zone_width != float('inf') and max_zone_width > 0:
                score += (strat.profit_zone_width / max_zone_width) * weights['profit_zone']
            
            # 4. Target performance (plus élevé = meilleur)
            if 'target_performance' in weights and max_target_perf > 0:
                score += (abs(strat.profit_at_target_pct) / max_target_perf) * weights['target_performance']

            # 6. Profit/Loss ratio (plus élevé = meilleur)
            if 'profit_loss_ratio' in weights and strat.surface_loss > 0 and max_pl_ratio > min_pl_ratio:
                pl_ratio = strat.surface_profit / strat.surface_loss
                pl_score = (pl_ratio - min_pl_ratio) / (max_pl_ratio - min_pl_ratio)
                score += pl_score * weights['profit_loss_ratio']
            
            strat.score = score
        
        return strategies
    
    def print_summary(self, strategies: List[StrategyComparison], top_n: int = 5):
        """
        Affiche un résumé des meilleures stratégies.
        
        Args:
            strategies: Liste de stratégies classées
            top_n: Nombre de stratégies à afficher
        """
        if not strategies:
            print("Aucune stratégie à afficher")
            return
        
        print("\n" + "=" * 80)
        print(f"TOP {min(top_n, len(strategies))} STRATÉGIES")
        print("=" * 80)
        
        for strat in strategies[:top_n]:
            print(f"\n#{strat.rank} - {strat.strategy_name}")
            print(f"   Score: {strat.score:.4f}")
            print(f"   Max Profit: ${strat.max_profit:.2f}" + 
                  (f" ({strat.profit_at_target_pct:.1f}% au target)" if strat.profit_at_target_pct else ""))
            print(f"   Max Loss: ${strat.max_loss:.2f}")
            print(f"   Risk/Reward: {strat.risk_reward_ratio:.2f}")
            if strat.profit_zone_width != float('inf'):
                print(f"   Profit Zone: ${strat.profit_zone_width:.2f}")

            if strat.surface_loss > 0:
                pl_ratio = strat.surface_profit / strat.surface_loss
                print(f"   Profit/Loss Ratio: {pl_ratio:.2f}")
            print(f"   Delta Total: {strat.total_delta:.3f}")
        
        print("\n" + "=" * 80)

