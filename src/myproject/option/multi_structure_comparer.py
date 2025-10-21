"""
Comparateur Multi-Structures - Version Simplifiée
==================================================
Les générateurs retournent maintenant directement des StrategyComparison.
"""

from typing import List, Dict, Optional
from myproject.option.fly_generator import FlyGenerator
from myproject.option.condor_generator import CondorGenerator
from myproject.option.option_generator import OptionStrategyGenerator
from myproject.option.comparison_class import StrategyComparison


class MultiStructureComparer:
    """Comparateur unifié pour toutes les structures multi-leg."""
    
    def __init__(self, options_data: Dict[str, List[Dict]]):
        self.fly_generator = FlyGenerator(options_data)
        self.condor_generator = CondorGenerator(options_data)
        self.option_generator = OptionStrategyGenerator(options_data)
        self.options_data = options_data
    
    def compare_all_structures(self,
                              target_price: float,
                              strike : float,
                              include_flies: bool = True,
                              include_condors: bool = True,
                              include_spreads: bool = True,
                              include_straddles: bool = True,
                              include_single_legs: bool = False,
                              require_symmetric: bool = False,
                              top_n: int = 10,
                              max_legs: int = 4,
                              weights: Optional[Dict[str, float]] = None) -> List[StrategyComparison]:
        """
        Compare toutes les structures possibles et retourne les meilleures.
        
        Args:
            target_price: Prix cible du sous-jacent
            strike_min: Strike minimum
            strike_max: Strike maximum
            include_flies: Inclure les butterflies
            include_condors: Inclure les condors (iron, call, put)
            include_spreads: Inclure les spreads (bull/bear call/put)
            include_straddles: Inclure les straddles et strangles
            include_single_legs: Inclure les single legs (long/short call/put)
            require_symmetric: N'accepter que les structures symétriques
            top_n: Nombre de meilleures stratégies à retourner
            max_legs: Nombre maximum de legs pour option_generator
            weights: Poids personnalisés pour le scoring
        """
        if weights is None:
            # Nouveaux poids avec les surfaces gaussiennes
            weights = {
                'max_profit': 0.15,           # Profit max (réduit)
                'risk_reward': 0.15,          # Ratio risque/récompense (réduit)
                'profit_zone': 0.10,          # Largeur de zone de profit (réduit)
                'target_performance': 0.10,   # Performance au prix cible (réduit)
                'surface_gauss': 0.35,        # Profit pondéré par gaussienne (NOUVEAU - prioritaire)
                'profit_loss_ratio': 0.15     # Ratio surface_profit/surface_loss (NOUVEAU)
            }
        
        all_comparisons = []
        price_min, price_max = target_price - 2.0, target_price + 2.0
        
        # Stratégies via OptionStrategyGenerator (spreads, straddles, single legs)
        if include_spreads or include_straddles or include_single_legs:
            try:
                generated_strategies = self.option_generator.generate_all_strategies(
                    price_min=price_min,
                    price_max=price_max,
                    strike=strike,
                    target_price=target_price,
                    expiration_date=None,
                    max_legs=max_legs
                )
                
                # Filtrer selon les options choisies
                for strat in generated_strategies:
                    name_lower = strat.strategy_name.lower()
                    
                    # Single legs
                    if include_single_legs and ('long call' in name_lower or 'short call' in name_lower or 
                                                'long put' in name_lower or 'short put' in name_lower) and \
                       'spread' not in name_lower and 'straddle' not in name_lower:
                        all_comparisons.append(strat)
                    
                    # Spreads
                    elif include_spreads and 'spread' in name_lower:
                        all_comparisons.append(strat)
                    
                    # Straddles et Strangles
                    elif include_straddles and ('straddle' in name_lower or 'strangle' in name_lower):
                        all_comparisons.append(strat)
                    
            except Exception as e:
                print(f"⚠️  Erreur lors de la génération avec OptionStrategyGenerator: {e}")
        
        # Butterflies
        if include_flies:
            try:
                # generate_all_flies(price_min, price_max, target_price, option_type='call', expiration_date=None, require_symmetric=False)
                all_comparisons.extend(self.fly_generator.generate_all_flies(
                    price_min=price_min,
                    price_max=price_max,
                    target_price=target_price,
                    option_type='call',
                    expiration_date=None,
                    require_symmetric=require_symmetric
                ))
                all_comparisons.extend(self.fly_generator.generate_all_flies(
                    price_min=price_min,
                    price_max=price_max,
                    target_price=target_price,
                    option_type='put',
                    expiration_date=None,
                    require_symmetric=require_symmetric
                ))
            except Exception as e:
                print(f"⚠️  Erreur lors de la génération des butterflies: {e}")
        
        # Condors
        if include_condors:
            try:
                # generate_iron_condors(price_min, price_max, target_price, expiration_date=None, require_symmetric=False)
                all_comparisons.extend(self.condor_generator.generate_iron_condors(
                    price_min=price_min,
                    price_max=price_max,
                    target_price=target_price,
                    expiration_date=None,
                    require_symmetric=require_symmetric
                ))
                # generate_call_condors et generate_put_condors passent à _generate_single_type_condors
                # _generate_single_type_condors(price_min, price_max, strike, target_price, option_type, ...)
                all_comparisons.extend(self.condor_generator.generate_call_condors(
                    price_min=price_min,
                    price_max=price_max,
                    strike=strike,
                    target_price=target_price,
                    expiration_date=None,
                    require_symmetric=require_symmetric
                ))
                all_comparisons.extend(self.condor_generator.generate_put_condors(
                    price_min=price_min,
                    price_max=price_max,
                    strike=strike,
                    target_price=target_price,
                    expiration_date=None,
                    require_symmetric=require_symmetric
                ))
            except Exception as e:
                print(f"⚠️  Erreur lors de la génération des condors: {e}")
        
        # Scoring et tri
        if all_comparisons:
            all_comparisons = self._calculate_scores(all_comparisons, weights)
            all_comparisons.sort(key=lambda x: x.score, reverse=True)
            all_comparisons = all_comparisons[:top_n]
            for i, comp in enumerate(all_comparisons, 1):
                comp.rank = i
        
        return all_comparisons
    
    def _calculate_scores(self, comparisons: List[StrategyComparison], weights: Dict[str, float]) -> List[StrategyComparison]:
        """Calcule les scores composites avec les nouveaux critères de surfaces."""
        if not comparisons:
            return comparisons
        
        # Normalisation des anciennes métriques
        max_profit_val = max(c.max_profit for c in comparisons if c.max_profit != float('inf'))
        max_zone_width = max(c.profit_zone_width for c in comparisons if c.profit_zone_width != float('inf'))
        max_target_perf = max(abs(c.profit_at_target_pct) for c in comparisons)
        risk_rewards = [c.risk_reward_ratio for c in comparisons if c.risk_reward_ratio != float('inf')]
        min_rr, max_rr = (min(risk_rewards), max(risk_rewards)) if risk_rewards else (1, 10)
        
        # Normalisation des nouvelles métriques de surfaces
        max_surface_gauss = max(c.surface_gauss for c in comparisons if c.surface_gauss > 0)
        profit_loss_ratios = []
        for c in comparisons:
            if c.surface_loss > 0:
                ratio = c.surface_profit / c.surface_loss
                profit_loss_ratios.append(ratio)
        max_pl_ratio = max(profit_loss_ratios) if profit_loss_ratios else 1.0
        min_pl_ratio = min(profit_loss_ratios) if profit_loss_ratios else 0.0
        
        for comp in comparisons:
            score = 0.0
            
            # Anciennes métriques (pondération réduite)
            if 'max_profit' in weights and max_profit_val > 0:
                score += (comp.max_profit / max_profit_val) * weights['max_profit']
            
            if 'risk_reward' in weights and comp.risk_reward_ratio != float('inf') and max_rr > min_rr:
                score += (1 - (comp.risk_reward_ratio - min_rr) / (max_rr - min_rr)) * weights['risk_reward']
            
            if 'profit_zone' in weights and comp.profit_zone_width != float('inf') and max_zone_width > 0:
                score += (comp.profit_zone_width / max_zone_width) * weights['profit_zone']
            
            if 'target_performance' in weights and max_target_perf > 0:
                score += (abs(comp.profit_at_target_pct) / max_target_perf) * weights['target_performance']
            
            # NOUVELLES MÉTRIQUES - Surfaces pondérées par gaussienne
            if 'surface_gauss' in weights and max_surface_gauss > 0:
                # Score normalisé entre 0 et 1 pour la surface gaussienne
                gauss_score = comp.surface_gauss / max_surface_gauss
                score += gauss_score * weights['surface_gauss']
            
            if 'profit_loss_ratio' in weights and comp.surface_loss > 0:
                # Ratio profit/loss normalisé
                pl_ratio = comp.surface_profit / comp.surface_loss
                if max_pl_ratio > min_pl_ratio:
                    pl_score = (pl_ratio - min_pl_ratio) / (max_pl_ratio - min_pl_ratio)
                    score += pl_score * weights['profit_loss_ratio']
            
            comp.score = score
        
        return comparisons