"""
Comparateur Multi-Structures - Version Simplifiée
==================================================
Les générateurs retournent maintenant directement des StrategyComparison.
"""

from typing import List, Dict, Optional
from myproject.option.fly_generator import FlyGenerator
from myproject.option.condor_generator import CondorGenerator
from myproject.option.comparison_class import StrategyComparison


class MultiStructureComparer:
    """Comparateur unifié pour toutes les structures multi-leg."""
    
    def __init__(self, options_data: Dict[str, List[Dict]]):
        self.fly_generator = FlyGenerator(options_data)
        self.condor_generator = CondorGenerator(options_data)
        self.options_data = options_data
    
    def compare_all_structures(self,
                              target_price: float,
                              strike_min: float,
                              strike_max: float,
                              days_to_expiry: int,
                              include_flies: bool = True,
                              include_condors: bool = True,
                              require_symmetric: bool = False,
                              top_n: int = 10,
                              weights: Optional[Dict[str, float]] = None) -> List[StrategyComparison]:
        """Compare toutes les structures possibles et retourne les meilleures."""
        if weights is None:
            weights = {'max_profit': 0.25, 'risk_reward': 0.25, 'profit_zone': 0.25, 'target_performance': 0.25}
        
        all_comparisons = []
        price_min, price_max = target_price - 2.0, target_price + 2.0
        
        # Butterflies
        if include_flies:
            all_comparisons.extend(self.fly_generator.generate_all_flies(
                price_min, price_max, strike_min, strike_max, target_price,
                'call', None, require_symmetric, 0.25, 3.0))
            all_comparisons.extend(self.fly_generator.generate_all_flies(
                price_min, price_max, strike_min, strike_max, target_price,
                'put', None, require_symmetric, 0.25, 3.0))
        
        # Condors
        if include_condors:
            all_comparisons.extend(self.condor_generator.generate_iron_condors(
                price_min, price_max, strike_min, strike_max, target_price,
                None, require_symmetric, 0.25, 2.5, 0.5, 5.0))
            all_comparisons.extend(self.condor_generator.generate_call_condors(
                price_min, price_max, strike_min, strike_max, target_price,
                None, require_symmetric, 0.25, 2.5, 0.5, 5.0))
            all_comparisons.extend(self.condor_generator.generate_put_condors(
                price_min, price_max, strike_min, strike_max, target_price,
                None, require_symmetric, 0.25, 2.5, 0.5, 5.0))
        
        # Scoring et tri
        if all_comparisons:
            all_comparisons = self._calculate_scores(all_comparisons, weights)
            all_comparisons.sort(key=lambda x: x.score, reverse=True)
            all_comparisons = all_comparisons[:top_n]
            for i, comp in enumerate(all_comparisons, 1):
                comp.rank = i
        
        return all_comparisons
    
    def _calculate_scores(self, comparisons: List[StrategyComparison], weights: Dict[str, float]) -> List[StrategyComparison]:
        """Calcule les scores composites."""
        if not comparisons:
            return comparisons
        
        max_profit_val = max(c.max_profit for c in comparisons if c.max_profit != float('inf'))
        max_zone_width = max(c.profit_zone_width for c in comparisons if c.profit_zone_width != float('inf'))
        max_target_perf = max(abs(c.profit_at_target_pct) for c in comparisons)
        risk_rewards = [c.risk_reward_ratio for c in comparisons if c.risk_reward_ratio != float('inf')]
        min_rr, max_rr = (min(risk_rewards), max(risk_rewards)) if risk_rewards else (1, 10)
        
        for comp in comparisons:
            score = 0.0
            if 'max_profit' in weights and max_profit_val > 0:
                score += (comp.max_profit / max_profit_val) * weights['max_profit']
            if 'risk_reward' in weights and comp.risk_reward_ratio != float('inf') and max_rr > min_rr:
                score += (1 - (comp.risk_reward_ratio - min_rr) / (max_rr - min_rr)) * weights['risk_reward']
            if 'profit_zone' in weights and comp.profit_zone_width != float('inf') and max_zone_width > 0:
                score += (comp.profit_zone_width / max_zone_width) * weights['profit_zone']
            if 'target_performance' in weights and max_target_perf > 0:
                score += (abs(comp.profit_at_target_pct) / max_target_perf) * weights['target_performance']
            comp.score = score
        
        return comparisons
    
    def display_comparison(self, comparisons: List[StrategyComparison]):
        """Affiche le tableau de comparaison."""
        if not comparisons:
            print("Aucune stratégie à comparer")
            return
        
        print("\n" + "="*130)
        print(f"COMPARAISON DES STRUCTURES - Prix cible: ${comparisons[0].target_price:.2f}")
        print("="*130)
        print(f"{'Rank':<6} {'Structure':<35} {'Max Profit':<12} {'Max Loss':<12} "
              f"{'R/R Ratio':<10} {'Zone ±':<10} {'P&L@Target':<12} {'Score':<8}")
        print("-"*130)
        
        for comp in comparisons:
            max_loss_str = f"${abs(comp.max_loss):.2f}" if comp.max_loss != -999999.0 else "Illimité"
            rr_str = f"{comp.risk_reward_ratio:.2f}" if comp.risk_reward_ratio != float('inf') else "∞"
            zone_str = f"${comp.profit_zone_width:.2f}" if comp.profit_zone_width != float('inf') else "Illimité"
            
            print(f"{comp.rank:<6} {comp.strategy_name:<35} "
                  f"${comp.max_profit:<11.2f} {max_loss_str:<12} {rr_str:<10} {zone_str:<10} "
                  f"${comp.profit_at_target:<11.2f} {comp.score:<8.3f}")
        
        print("="*130)
        print("\nPOINTS DE BREAKEVEN:")
        print("-"*80)
        for comp in comparisons:
            if comp.breakeven_points:
                be_str = ", ".join([f"${be:.2f}" for be in comp.breakeven_points])
                print(f"{comp.strategy_name:<35} : {be_str}")
        print("="*130 + "\n")
