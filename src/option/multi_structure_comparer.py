"""
Comparateur Multi-Structures pour Fly et Condor
================================================
Compare les différentes structures générées (Butterfly, Iron Condor, etc.)
et retourne des résultats au format StrategyComparison.

"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
import numpy as np

from .fly_generator import FlyGenerator, FlyConfiguration
from .condor_generator import CondorGenerator, CondorConfiguration
from .comparison_class import StrategyComparison
from .option_utils import calculate_greeks_by_type, calculate_avg_implied_volatility, get_expiration_info


class MultiStructureComparer:
    """
    Comparateur unifié pour toutes les structures multi-leg générées automatiquement.
    
    Retourne des objets StrategyComparison compatibles avec le système existant.
    """
    
    def __init__(self, options_data: Dict[str, List[Dict]]):
        """
        Args:
            options_data: Dictionnaire avec 'calls' et 'puts'
                         Format: {'calls': [...], 'puts': [...]}
        """
        self.fly_generator = FlyGenerator(options_data)
        self.condor_generator = CondorGenerator(options_data)
        self.options_data = options_data
    
    # ========================================================================
    # MÉTHODES UTILITAIRES COMMUNES
    # ========================================================================
    
    @staticmethod
    def _build_greeks_dict(structure) -> Dict[str, float]:
        """
        Construit un dictionnaire complet des Greeks pour une structure.
        Utilise la liste all_options simplifiée.
        
        Args:
            structure: FlyConfiguration ou CondorConfiguration
        
        Returns:
            Dict avec tous les Greeks (calls, puts, total)
        """
        # Utiliser la fonction utilitaire avec all_options
        greeks_by_type = calculate_greeks_by_type(structure.all_options)
        
        return {
            # Calls
            'total_delta_calls': greeks_by_type['calls']['delta'],
            'total_gamma_calls': greeks_by_type['calls']['gamma'],
            'total_vega_calls': greeks_by_type['calls']['vega'],
            'total_theta_calls': greeks_by_type['calls']['theta'],
            # Puts
            'total_delta_puts': greeks_by_type['puts']['delta'],
            'total_gamma_puts': greeks_by_type['puts']['gamma'],
            'total_vega_puts': greeks_by_type['puts']['vega'],
            'total_theta_puts': greeks_by_type['puts']['theta'],
            # Total
            'total_delta': greeks_by_type['total']['delta'],
            'total_gamma': greeks_by_type['total']['gamma'],
            'total_vega': greeks_by_type['total']['vega'],
            'total_theta': greeks_by_type['total']['theta']
        }
    
    @staticmethod
    def _calculate_profit_zone(breakeven_points: List[float], 
                               center_strike: float) -> tuple:
        """
        Calcule la zone de profit à partir des breakevens.
        Méthode commune pour éviter la duplication.
        
        Args:
            breakeven_points: Liste des points de breakeven
            center_strike: Strike central
        
        Returns:
            (profit_range, profit_zone_width)
        """
        if len(breakeven_points) >= 2:
            profit_range = (min(breakeven_points), max(breakeven_points))
            profit_zone_width = profit_range[1] - profit_range[0]
        else:
            profit_range = (center_strike, center_strike)
            profit_zone_width = 0.0
        
        return profit_range, profit_zone_width
    
    @staticmethod
    def _calculate_risk_reward(max_loss: float, max_profit: float) -> float:
        """
        Calcule le ratio risque/rendement.
        Méthode commune pour éviter la duplication.
        
        Args:
            max_loss: Perte maximale
            max_profit: Profit maximum
        
        Returns:
            Risk/Reward ratio
        """
        if max_loss != 0:
            return abs(max_loss) / max_profit if max_profit > 0 else 0
        else:
            return float('inf')
    
    # ========================================================================
    # MÉTHODES DE COMPARAISON
    # ========================================================================
    
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
        """
        Compare toutes les structures possibles et retourne les meilleures.
        
        Args:
            target_price: Prix cible du sous-jacent
            strike_min: Strike minimum
            strike_max: Strike maximum
            days_to_expiry: Jours jusqu'à expiration
            include_flies: Inclure les Butterflies
            include_condors: Inclure les Condors
            require_symmetric: Uniquement les structures symétriques
            top_n: Nombre de meilleures structures à retourner
            weights: Poids pour le scoring
        
        Returns:
            Liste triée de StrategyComparison (format compatible avec StrategyComparer)
        """
        if weights is None:
            weights = {
                'max_profit': 0.25,
                'risk_reward': 0.25,
                'profit_zone': 0.25,
                'target_performance': 0.25
            }
        
        all_comparisons = []
        
        # Prix d'exploration autour du target
        price_min = target_price - 2.0
        price_max = target_price + 2.0
        
        # 1. Générer et analyser les Butterflies
        if include_flies:
            # Call Butterflies
            call_flies = self.fly_generator.generate_all_flies(
                price_min=price_min,
                price_max=price_max,
                strike_min=strike_min,
                strike_max=strike_max,
                option_type='call',
                require_symmetric=require_symmetric,
                min_wing_width=0.25,
                max_wing_width=3.0
            )
            
            # Put Butterflies
            put_flies = self.fly_generator.generate_all_flies(
                price_min=price_min,
                price_max=price_max,
                strike_min=strike_min,
                strike_max=strike_max,
                option_type='put',
                require_symmetric=require_symmetric,
                min_wing_width=0.25,
                max_wing_width=3.0
            )
            
            # Convertir en StrategyComparison
            for fly in call_flies + put_flies:
                comparison = self._fly_to_comparison(fly, target_price, days_to_expiry)
                if comparison:
                    all_comparisons.append(comparison)
        
        # 2. Générer et analyser les Condors
        if include_condors:
            # Iron Condors
            iron_condors = self.condor_generator.generate_iron_condors(
                price_min=price_min,
                price_max=price_max,
                strike_min=strike_min,
                strike_max=strike_max,
                require_symmetric=require_symmetric,
                min_spread_width=0.25,
                max_spread_width=2.5,
                min_body_width=0.5,
                max_body_width=5.0
            )
            
            # Call Condors
            call_condors = self.condor_generator.generate_call_condors(
                price_min=price_min,
                price_max=price_max,
                strike_min=strike_min,
                strike_max=strike_max,
                require_symmetric=require_symmetric,
                min_wing_width=0.25,
                max_wing_width=2.5,
                min_body_width=0.5,
                max_body_width=5.0
            )
            
            # Put Condors
            put_condors = self.condor_generator.generate_put_condors(
                price_min=price_min,
                price_max=price_max,
                strike_min=strike_min,
                strike_max=strike_max,
                require_symmetric=require_symmetric,
                min_wing_width=0.25,
                max_wing_width=2.5,
                min_body_width=0.5,
                max_body_width=5.0
            )
            
            # Convertir en StrategyComparison
            for condor in iron_condors + call_condors + put_condors:
                comparison = self._condor_to_comparison(condor, target_price, days_to_expiry)
                if comparison:
                    all_comparisons.append(comparison)
        
        # 3. Calculer les scores et trier
        if all_comparisons:
            all_comparisons = self._calculate_scores(all_comparisons, weights)
            all_comparisons.sort(key=lambda x: x.score, reverse=True)
            
            # Limiter au top N
            all_comparisons = all_comparisons[:top_n]
            
            # Attribuer les rangs
            for i, comp in enumerate(all_comparisons, 1):
                comp.rank = i
        
        return all_comparisons
    
    def _fly_to_comparison(self, 
                          fly: FlyConfiguration,
                          target_price: float,
                          days_to_expiry: int) -> Optional[StrategyComparison]:
        """
        Convertit une FlyConfiguration en StrategyComparison.
        Version simplifiée utilisant all_options.
        """
        try:
            # Calcul des métriques financières
            net_credit = fly.estimated_cost
            max_profit = self._calculate_fly_max_profit(fly)
            max_loss = self._calculate_fly_max_loss(fly)
            breakeven_points = self._calculate_fly_breakeven(fly)
            
            # Zone de profit (méthode commune)
            profit_range, profit_zone_width = self._calculate_profit_zone(
                breakeven_points, fly.middle_strike
            )
            
            # Risk/Reward (méthode commune)
            risk_reward_ratio = self._calculate_risk_reward(max_loss, max_profit)
            
            # Profit au prix cible
            profit_at_target = self._calculate_fly_profit_at_price(fly, target_price)
            profit_at_target_pct = (profit_at_target / max_profit * 100) if max_profit > 0 else 0
            
            # Greeks (méthode commune depuis all_options)
            greeks = self._build_greeks_dict(fly)
            
            # Volatilité implicite moyenne (depuis all_options)
            avg_iv = calculate_avg_implied_volatility(fly.all_options)
            
            # Date d'expiration (depuis all_options)
            exp_info = get_expiration_info(fly.all_options)
            exp_date = exp_info['expiration_date'] or datetime.now() + timedelta(days=days_to_expiry)
            
            return StrategyComparison(
                strategy_name=fly.name,
                strategy=None,
                target_price=target_price,
                expiration_date=exp_date,
                days_to_expiry=days_to_expiry,
                net_credit=net_credit,
                max_profit=max_profit,
                max_loss=max_loss,
                breakeven_points=breakeven_points,
                profit_range=profit_range,
                profit_zone_width=profit_zone_width,
                risk_reward_ratio=risk_reward_ratio,
                # Greeks - déballage explicite
                total_delta_calls=greeks['total_delta_calls'],
                total_gamma_calls=greeks['total_gamma_calls'],
                total_vega_calls=greeks['total_vega_calls'],
                total_theta_calls=greeks['total_theta_calls'],
                total_delta_puts=greeks['total_delta_puts'],
                total_gamma_puts=greeks['total_gamma_puts'],
                total_vega_puts=greeks['total_vega_puts'],
                total_theta_puts=greeks['total_theta_puts'],
                total_delta=greeks['total_delta'],
                total_gamma=greeks['total_gamma'],
                total_vega=greeks['total_vega'],
                total_theta=greeks['total_theta'],
                # Performance
                profit_at_target=profit_at_target,
                profit_at_target_pct=profit_at_target_pct,
                score=0.0,
                # Options unifiées
                all_options=fly.all_options.copy()
            )
        except Exception as e:
            print(f"⚠️ Erreur lors de la conversion du Fly {fly.name}: {e}")
            return None
    
    def _condor_to_comparison(self,
                             condor: CondorConfiguration,
                             target_price: float,
                             days_to_expiry: int) -> Optional[StrategyComparison]:
        """
        Convertit une CondorConfiguration en StrategyComparison.
        Version simplifiée utilisant all_options.
        """
        try:
            # Calcul des métriques financières
            net_credit = condor.estimated_credit
            max_profit = self._calculate_condor_max_profit(condor)
            max_loss = self._calculate_condor_max_loss(condor)
            breakeven_points = self._calculate_condor_breakeven(condor)
            
            # Zone de profit (méthode commune)
            profit_range, profit_zone_width = self._calculate_profit_zone(
                breakeven_points, condor.center_strike
            )
            # Override pour Condor: utiliser body_width si pas de breakeven
            if len(breakeven_points) < 2:
                profit_zone_width = condor.body_width
            
            # Risk/Reward (méthode commune)
            risk_reward_ratio = self._calculate_risk_reward(max_loss, max_profit)
            
            # Profit au prix cible
            profit_at_target = self._calculate_condor_profit_at_price(condor, target_price)
            profit_at_target_pct = (profit_at_target / max_profit * 100) if max_profit > 0 else 0
            
            # Greeks (méthode commune depuis all_options)
            greeks = self._build_greeks_dict(condor)
            
            # Volatilité implicite moyenne (depuis all_options)
            avg_iv = calculate_avg_implied_volatility(condor.all_options)
            
            # Date d'expiration (depuis all_options)
            exp_info = get_expiration_info(condor.all_options)
            exp_date = exp_info['expiration_date'] or datetime.now() + timedelta(days=days_to_expiry)
            
            return StrategyComparison(
                strategy_name=condor.name,
                strategy=None,
                target_price=target_price,
                expiration_date=exp_date,
                days_to_expiry=days_to_expiry,
                net_credit=net_credit,
                max_profit=max_profit,
                max_loss=max_loss,
                breakeven_points=breakeven_points,
                profit_range=profit_range,
                profit_zone_width=profit_zone_width,
                risk_reward_ratio=risk_reward_ratio,
                # Greeks - déballage explicite
                total_delta_calls=greeks['total_delta_calls'],
                total_gamma_calls=greeks['total_gamma_calls'],
                total_vega_calls=greeks['total_vega_calls'],
                total_theta_calls=greeks['total_theta_calls'],
                total_delta_puts=greeks['total_delta_puts'],
                total_gamma_puts=greeks['total_gamma_puts'],
                total_vega_puts=greeks['total_vega_puts'],
                total_theta_puts=greeks['total_theta_puts'],
                total_delta=greeks['total_delta'],
                total_gamma=greeks['total_gamma'],
                total_vega=greeks['total_vega'],
                total_theta=greeks['total_theta'],
                # Performance
                profit_at_target=profit_at_target,
                profit_at_target_pct=profit_at_target_pct,
                score=0.0,
                # Options unifiées
                all_options=condor.all_options.copy()
            )
        except Exception as e:
            print(f"⚠️ Erreur lors de la conversion du Condor {condor.name}: {e}")
            return None
    
    def _calculate_fly_max_profit(self, fly: FlyConfiguration) -> float:
        """Calcule le profit maximum d'un Butterfly"""
        # Pour un Long Butterfly: Max profit = Wing width - Net debit
        wing_width = min(fly.wing_width_lower, fly.wing_width_upper)
        return max(0, wing_width - abs(fly.estimated_cost))
    
    def _calculate_fly_max_loss(self, fly: FlyConfiguration) -> float:
        """Calcule la perte maximale d'un Butterfly"""
        # Pour un Long Butterfly: Max loss = Net debit payé
        return -abs(fly.estimated_cost)
    
    def _calculate_fly_breakeven(self, fly: FlyConfiguration) -> List[float]:
        """Calcule les points de breakeven d'un Butterfly"""
        # Breakeven inférieur = Lower strike + Net debit
        # Breakeven supérieur = Upper strike - Net debit
        debit = abs(fly.estimated_cost)
        return [
            fly.lower_strike + debit,
            fly.upper_strike - debit
        ]
    
    def _calculate_fly_profit_at_price(self, fly: FlyConfiguration, price: float) -> float:
        """Calcule le profit d'un Butterfly à un prix donné"""
        debit = abs(fly.estimated_cost)
        
        if price <= fly.lower_strike or price >= fly.upper_strike:
            return -debit
        elif price < fly.middle_strike:
            return (price - fly.lower_strike) - debit
        elif price > fly.middle_strike:
            return (fly.upper_strike - price) - debit
        else:  # price == middle_strike
            wing_width = min(fly.wing_width_lower, fly.wing_width_upper)
            return wing_width - debit
    
    def _calculate_condor_max_profit(self, condor: CondorConfiguration) -> float:
        """Calcule le profit maximum d'un Condor"""
        # Pour Iron Condor: Max profit = Net credit reçu
        # Pour Long Condor: Max profit = Body width - Net debit
        if condor.condor_type == 'iron':
            return condor.estimated_credit
        else:
            return max(0, condor.body_width - abs(condor.estimated_credit))
    
    def _calculate_condor_max_loss(self, condor: CondorConfiguration) -> float:
        """Calcule la perte maximale d'un Condor"""
        if condor.condor_type == 'iron':
            # Max loss = Spread width - Net credit
            max_spread = max(condor.lower_spread_width, condor.upper_spread_width)
            return -(max_spread - condor.estimated_credit)
        else:
            # Pour Long Condor: Max loss = Net debit
            return -abs(condor.estimated_credit)
    
    def _calculate_condor_breakeven(self, condor: CondorConfiguration) -> List[float]:
        """Calcule les points de breakeven d'un Condor"""
        if condor.condor_type == 'iron':
            credit = condor.estimated_credit
            return [
                condor.strike2 - credit,  # Breakeven bas
                condor.strike3 + credit   # Breakeven haut
            ]
        else:
            debit = abs(condor.estimated_credit)
            return [
                condor.strike1 + debit,
                condor.strike4 - debit
            ]
    
    def _calculate_condor_profit_at_price(self, condor: CondorConfiguration, price: float) -> float:
        """Calcule le profit d'un Condor à un prix donné"""
        if condor.condor_type == 'iron':
            credit = condor.estimated_credit
            if price <= condor.strike1:
                return -(condor.lower_spread_width - credit)
            elif price < condor.strike2:
                return -((condor.strike2 - price) - credit)
            elif price >= condor.strike4:
                return -(condor.upper_spread_width - credit)
            elif price > condor.strike3:
                return -((price - condor.strike3) - credit)
            else:  # Entre strike2 et strike3
                return credit
        else:
            debit = abs(condor.estimated_credit)
            if price <= condor.strike1 or price >= condor.strike4:
                return -debit
            elif price < condor.strike2:
                return (price - condor.strike1) - debit
            elif price > condor.strike3:
                return (condor.strike4 - price) - debit
            else:  # Dans le corps
                return condor.body_width - debit
    
    def _calculate_scores(self,
                         comparisons: List[StrategyComparison],
                         weights: Dict[str, float]) -> List[StrategyComparison]:
        """Calcule les scores composites (identique à StrategyComparer)"""
        
        if not comparisons:
            return comparisons
        
        # Trouver les valeurs max pour normalisation
        max_profit_val = max(c.max_profit for c in comparisons)
        max_zone_width = max(c.profit_zone_width for c in comparisons if c.profit_zone_width != float('inf'))
        max_target_perf = max(abs(c.profit_at_target_pct) for c in comparisons)
        
        # Risk/reward: plus bas est mieux
        risk_rewards = [c.risk_reward_ratio for c in comparisons if c.risk_reward_ratio != float('inf')]
        min_rr = min(risk_rewards) if risk_rewards else 1
        max_rr = max(risk_rewards) if risk_rewards else 10
        
        for comp in comparisons:
            score = 0.0
            
            # 1. Max profit (plus élevé = mieux)
            if 'max_profit' in weights and max_profit_val > 0:
                normalized_profit = comp.max_profit / max_profit_val
                score += normalized_profit * weights['max_profit']
            
            # 2. Risk/Reward (plus bas = mieux)
            if 'risk_reward' in weights and comp.risk_reward_ratio != float('inf'):
                if max_rr > min_rr:
                    normalized_rr = 1 - ((comp.risk_reward_ratio - min_rr) / (max_rr - min_rr))
                else:
                    normalized_rr = 1.0
                score += normalized_rr * weights['risk_reward']
            
            # 3. Zone profitable (plus large = mieux)
            if 'profit_zone' in weights and comp.profit_zone_width != float('inf') and max_zone_width > 0:
                normalized_zone = comp.profit_zone_width / max_zone_width
                score += normalized_zone * weights['profit_zone']
            
            # 4. Performance au prix cible (meilleur = mieux)
            if 'target_performance' in weights and max_target_perf > 0:
                normalized_target = abs(comp.profit_at_target_pct) / max_target_perf
                score += normalized_target * weights['target_performance']
            
            comp.score = score
        
        return comparisons
    
    def display_comparison(self, comparisons: List[StrategyComparison]):
        """Affiche le tableau de comparaison (format identique à StrategyComparer)"""
        
        if not comparisons:
            print("Aucune stratégie à comparer")
            return
        
        print("\n" + "="*130)
        print(f"COMPARAISON DES STRUCTURES - Prix cible: ${comparisons[0].target_price:.2f} - DTE: {comparisons[0].days_to_expiry}j")
        print("="*130)
        print(f"{'Rank':<6} {'Structure':<35} {'Crédit':<10} {'Max Profit':<12} {'Max Loss':<12} "
              f"{'R/R Ratio':<10} {'Zone ±':<10} {'P&L@Target':<12} {'Score':<8}")
        print("-"*130)
        
        for comp in comparisons:
            max_loss_str = f"${abs(comp.max_loss):.2f}" if comp.max_loss != -999999.0 else "Illimité"
            rr_str = f"{comp.risk_reward_ratio:.2f}" if comp.risk_reward_ratio != float('inf') else "∞"
            zone_str = f"${comp.profit_zone_width:.2f}" if comp.profit_zone_width != float('inf') else "Illimité"
            
            print(f"{comp.rank:<6} {comp.strategy_name:<35} ${comp.net_credit:<9.2f} "
                  f"${comp.max_profit:<11.2f} {max_loss_str:<12} {rr_str:<10} {zone_str:<10} "
                  f"${comp.profit_at_target:<11.2f} {comp.score:<8.3f}")
        
        print("="*130)
        
        # Détails des breakevens
        print("\nPOINTS DE BREAKEVEN:")
        print("-"*80)
        for comp in comparisons:
            if comp.breakeven_points:
                be_str = ", ".join([f"${be:.2f}" for be in comp.breakeven_points])
                print(f"{comp.strategy_name:<35} : {be_str}")
        print("="*130 + "\n")
