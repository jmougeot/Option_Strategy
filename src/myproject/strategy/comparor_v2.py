"""
Comparateur Multi-Structures - Version 2
=========================================
Comparateur simplifié pour les stratégies générées par option_generator_v2.
Utilise le même système de scoring que multi_structure_comparer.py.
"""

from typing import List, Dict, Optional
from myproject.strategy.comparison_class import StrategyComparison


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
        Compare et classe les stratégies selon un système de scoring multi-critères COMPLET.
        Tous les attributs de StrategyComparison participent au scoring.
        
        Args:
            strategies: Liste de StrategyComparison à comparer
            top_n: Nombre de meilleures stratégies à retourner
            weights: Poids personnalisés pour le scoring (optionnel)
                MÉTRIQUES FINANCIÈRES:
                - 'max_profit': Profit maximum (défaut: 0.10)
                - 'risk_reward': Ratio risque/récompense (défaut: 0.10)
                - 'profit_zone': Largeur de zone de profit (défaut: 0.08)
                - 'target_performance': Performance au prix cible (défaut: 0.08)
                
                SURFACES:
                - 'surface_profit': Surface de profit (défaut: 0.12)
                - 'surface_loss': Surface de perte (inversé) (défaut: 0.08)
                - 'profit_loss_ratio': Ratio surface profit/loss (défaut: 0.12)
                
                GREEKS:
                - 'delta_neutral': Neutralité du delta (défaut: 0.06)
                - 'gamma_exposure': Exposition gamma (défaut: 0.04)
                - 'vega_exposure': Exposition vega (défaut: 0.04)
                - 'theta_positive': Theta positif (défaut: 0.04)
                
                VOLATILITÉ:
                - 'implied_vol': Volatilité implicite moyenne (défaut: 0.04)
                
                BREAKEVENS:
                - 'breakeven_count': Nombre de points de breakeven (défaut: 0.05)
                - 'breakeven_spread': Écart des breakevens (défaut: 0.05)
        
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
        
        # Poids par défaut - TOUS les attributs participent
        if weights is None:
            weights = {
                # Métriques financières (40%)
                'max_profit': 0.10,
                'risk_reward': 0.10,
                'profit_zone': 0.08,
                'target_performance': 0.08,
                
                # Surfaces (32%)
                'surface_profit': 0.12,
                'surface_loss': 0.08,
                'profit_loss_ratio': 0.12,
                
                # Greeks (18%)
                'delta_neutral': 0.06,
                'gamma_exposure': 0.04,
                'vega_exposure': 0.04,
                'theta_positive': 0.04,
                
                # Volatilité (4%)
                'implied_vol': 0.04,
                
                # Breakevens (6%)
                'breakeven_count': 0.03,
                'breakeven_spread': 0.03,
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
        TOUS les attributs de StrategyComparison participent au scoring.
        """
        if not strategies:
            return strategies
        
        # ============ NORMALISATION DES MÉTRIQUES ============
        
        # 1. MÉTRIQUES FINANCIÈRES
        finite_profits = [s.max_profit for s in strategies if s.max_profit != float('inf')]
        max_profit_val = max(finite_profits) if finite_profits else 1.0
        
        finite_zones = [s.profit_zone_width for s in strategies if s.profit_zone_width != float('inf')]
        max_zone_width = max(finite_zones) if finite_zones else 1.0
        
        target_perfs = [abs(s.profit_at_target_pct) for s in strategies]
        max_target_perf = max(target_perfs) if target_perfs else 1.0
        
        finite_rr = [s.risk_reward_ratio for s in strategies if s.risk_reward_ratio != float('inf')]
        min_rr = min(finite_rr) if finite_rr else 0.0
        max_rr = max(finite_rr) if finite_rr else 1.0
        
        # 2. SURFACES
        surface_profits = [s.surface_profit for s in strategies if s.surface_profit > 0]
        max_surf_profit = max(surface_profits) if surface_profits else 1.0
        
        surface_losses = [abs(s.surface_loss) for s in strategies if s.surface_loss != 0]
        max_surf_loss = max(surface_losses) if surface_losses else 1.0
        
        profit_loss_ratios = []
        for s in strategies:
            if s.surface_loss > 0:
                ratio = s.surface_profit / s.surface_loss
                profit_loss_ratios.append(ratio)
        min_pl_ratio = min(profit_loss_ratios) if profit_loss_ratios else 0.0
        max_pl_ratio = max(profit_loss_ratios) if profit_loss_ratios else 1.0
        
        # 3. GREEKS
        deltas = [abs(s.total_delta) for s in strategies]
        max_delta = max(deltas) if deltas else 1.0
        
        gammas = [abs(s.total_gamma) for s in strategies]
        max_gamma = max(gammas) if gammas else 1.0
        
        vegas = [abs(s.total_vega) for s in strategies]
        max_vega = max(vegas) if vegas else 1.0
        
        thetas = [s.total_theta for s in strategies]
        min_theta = min(thetas) if thetas else 0.0
        max_theta = max(thetas) if thetas else 1.0
        
        # 4. VOLATILITÉ
        impl_vols = [s.avg_implied_volatility for s in strategies if s.avg_implied_volatility > 0]
        min_vol = min(impl_vols) if impl_vols else 0.0
        max_vol = max(impl_vols) if impl_vols else 1.0
        
        # 5. BREAKEVENS
        be_counts = [len(s.breakeven_points) for s in strategies]
        max_be_count = max(be_counts) if be_counts else 1
        
        be_spreads = []
        for s in strategies:
            if len(s.breakeven_points) >= 2:
                spread = max(s.breakeven_points) - min(s.breakeven_points)
                be_spreads.append(spread)
        max_be_spread = max(be_spreads) if be_spreads else 1.0
        
        # ============ CALCUL DES SCORES ============
        
        for strat in strategies:
            score = 0.0
            
            # ========== MÉTRIQUES FINANCIÈRES ==========
            
            # 1. Max profit (normalisé, plus élevé = meilleur)
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
            
            # ========== SURFACES ==========
            
            # 5. Surface profit (plus élevée = meilleur)
            if 'surface_profit' in weights and max_surf_profit > 0:
                score += (strat.surface_profit / max_surf_profit) * weights['surface_profit']
            
            # 6. Surface loss (inversé : plus petite = meilleur)
            if 'surface_loss' in weights and max_surf_loss > 0 and strat.surface_loss != 0:
                normalized_loss = abs(strat.surface_loss) / max_surf_loss
                score += (1 - normalized_loss) * weights['surface_loss']
            
            # 7. Profit/Loss ratio (plus élevé = meilleur)
            if 'profit_loss_ratio' in weights and strat.surface_loss > 0 and max_pl_ratio > min_pl_ratio:
                pl_ratio = strat.surface_profit / strat.surface_loss
                pl_score = (pl_ratio - min_pl_ratio) / (max_pl_ratio - min_pl_ratio)
                score += pl_score * weights['profit_loss_ratio']
            
            # ========== GREEKS ==========
            
            # 8. Delta neutralité (plus proche de 0 = meilleur)
            if 'delta_neutral' in weights and max_delta > 0:
                delta_score = 1 - (abs(strat.total_delta) / max_delta)
                score += delta_score * weights['delta_neutral']
            
            # 9. Gamma exposure (exposition gamma modérée préférable)
            if 'gamma_exposure' in weights and max_gamma > 0:
                # Gamma modéré est préférable (ni trop élevé ni trop faible)
                gamma_normalized = abs(strat.total_gamma) / max_gamma
                # Score optimal à 0.5, pénalise les extrêmes
                gamma_score = 1 - abs(gamma_normalized - 0.5) * 2
                score += max(0, gamma_score) * weights['gamma_exposure']
            
            # 10. Vega exposure (exposition vega modérée)
            if 'vega_exposure' in weights and max_vega > 0:
                vega_normalized = abs(strat.total_vega) / max_vega
                vega_score = 1 - abs(vega_normalized - 0.5) * 2
                score += max(0, vega_score) * weights['vega_exposure']
            
            # 11. Theta positif (theta positif préférable)
            if 'theta_positive' in weights and max_theta > min_theta:
                if strat.total_theta >= 0:
                    # Theta positif = bon
                    theta_score = (strat.total_theta - min_theta) / (max_theta - min_theta) if max_theta > min_theta else 0
                else:
                    # Theta négatif = pénalité
                    theta_score = 0
                score += theta_score * weights['theta_positive']
            
            # ========== VOLATILITÉ ==========
            
            # 12. Volatilité implicite (volatilité modérée préférable)
            if 'implied_vol' in weights and max_vol > min_vol and strat.avg_implied_volatility > 0:
                vol_normalized = (strat.avg_implied_volatility - min_vol) / (max_vol - min_vol)
                # Volatilité modérée (autour de 0.5) est préférable
                vol_score = 1 - abs(vol_normalized - 0.5) * 2
                score += max(0, vol_score) * weights['implied_vol']

            
            strat.score = score
        
        return strategies
    
