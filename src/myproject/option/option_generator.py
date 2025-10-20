"""
Générateur Universel de Stratégies d'Options
=============================================
Génère toutes les stratégies possibles de 1 à 4 legs directement en StrategyComparison.
Stratégies couvertes:
- 1 leg: Long Call, Long Put, Short Call, Short Put
- 2 legs: Spread, Straddle, Strangle
- 3 legs: Butterfly (call/put)
- 4 legs: Iron Condor, Call/Put Condor, Iron Butterfly
"""

from typing import List, Dict, Optional, Literal, Tuple
from myproject.option.option_class import Option
from myproject.option.option_utils import (
    dict_to_option,
    calculate_greeks_by_type,
    calculate_avg_implied_volatility,
    get_expiration_key,
    calculate_all_surfaces
)
from myproject.option.comparison_class import StrategyComparison


class OptionStrategyGenerator:
    """
    Générateur universel de stratégies d'options de 1 à 4 legs.
    Retourne directement des objets StrategyComparison.
    """
    
    def __init__(self, options_data: Dict[str, List[Dict]]):
        """
        Initialise le générateur avec les données d'options Bloomberg
        
        Args:
            options_data: Dictionnaire avec 'calls' et 'puts'
        """
        self.calls_data = options_data.get('calls', [])
        self.puts_data = options_data.get('puts', [])
        self._index_options()
        
        # Paramètres pour le calcul des surfaces (seront mis à jour par generate_all_strategies)
        self.price_min = None
        self.price_max = None
    
    def _index_options(self):
        """Crée des index pour accès rapide par strike et expiration"""
        self.calls_by_strike_exp = {}
        self.puts_by_strike_exp = {}
        
        for call in self.calls_data:
            exp_key = get_expiration_key(
                call.get('day_of_expiration', 1),
                call.get('month_of_expiration', 'F'),
                call.get('year_of_expiration', 2025)
            )
            key = (call['strike'], exp_key)
            self.calls_by_strike_exp[key] = call
        
        for put in self.puts_data:
            exp_key = get_expiration_key(
                put.get('day_of_expiration', 1),
                put.get('month_of_expiration', 'F'),
                put.get('year_of_expiration', 2025)
            )
            key = (put['strike'], exp_key)
            self.puts_by_strike_exp[key] = put
    
    def _calculate_surfaces(self, all_options: List[Option], center_strike: float) -> Dict[str, float]:
        """
        Calcule les surfaces (profit, loss, gauss) pour une stratégie.
        
        Args:
            all_options: Liste des options de la stratégie
            center_strike: Strike central pour la gaussienne
        
        Returns:
            Dict avec 'profit_surface', 'loss_surface', 'surface_gauss'
        """
        if self.price_min is None or self.price_max is None:
            return {
                'profit_surface': 0.0,
                'loss_surface': 0.0,
                'surface_gauss': 0.0
            }
        
        try:
            surfaces = calculate_all_surfaces(
                all_options,
                self.price_min,
                self.price_max,
                center_strike,
                num_points=500  # Compromis entre précision et performance
            )
            return {
                'profit_surface': surfaces['profit_surface'],
                'loss_surface': surfaces['loss_surface'],
                'surface_gauss': surfaces['surface_gauss']
            }
        except Exception as e:
            print(f"⚠️  Erreur calcul surfaces: {e}")
            return {
                'profit_surface': 0.0,
                'loss_surface': 0.0,
                'surface_gauss': 0.0
            }
    
    def get_available_strikes(self, option_type: str = 'call', expiration_date: Optional[str] = None) -> List[float]:
        """Récupère la liste des strikes disponibles"""
        data = self.calls_data if option_type.lower() == 'call' else self.puts_data
        if expiration_date:
            strikes = [
                opt['strike'] for opt in data 
                if get_expiration_key(
                    opt.get('day_of_expiration', 1),
                    opt.get('month_of_expiration', 'F'),
                    opt.get('year_of_expiration', 2025)
                ) == expiration_date
            ]
        else:
            strikes = [opt['strike'] for opt in data]
        return sorted(set(strikes))
    
    def get_available_expirations(self, option_type: str = 'call') -> List[str]:
        """Récupère la liste des dates d'expiration disponibles"""
        data = self.calls_data if option_type.lower() == 'call' else self.puts_data
        expirations = [
            get_expiration_key(
                opt.get('day_of_expiration', 1),
                opt.get('month_of_expiration', 'F'),
                opt.get('year_of_expiration', 2025)
            )
            for opt in data
        ]
        return sorted(set(expirations))
    
    def generate_all_strategies(self,
                                price_min: float,
                                price_max: float,
                                strike_min: float,
                                strike_max: float,
                                target_price: float,
                                expiration_date: Optional[str] = None,
                                max_legs: int = 4) -> List[StrategyComparison]:
        """
        Génère toutes les stratégies possibles de 1 à max_legs.
        
        Args:
            price_min: Prix minimum pour le filtre
            price_max: Prix maximum pour le filtre
            strike_min: Strike minimum
            strike_max: Strike maximum
            target_price: Prix cible du sous-jacent
            expiration_date: Date d'expiration (optionnel, format 'YYYY-MM-DD')
            max_legs: Nombre maximum de legs (1 à 4)
        
        Returns:
            Liste de StrategyComparison pour toutes les stratégies générées
        """
        # Stocker les paramètres de prix pour le calcul des surfaces
        self.price_min = price_min
        self.price_max = price_max
        
        all_strategies = []
        
        # 1 leg strategies
        if max_legs >= 1:
            all_strategies.extend(self._generate_single_leg_strategies(
                strike_min, strike_max, target_price, expiration_date
            ))
        
        # 2 legs strategies
        if max_legs >= 2:
            all_strategies.extend(self._generate_two_leg_strategies(
                price_min, price_max, strike_min, strike_max, target_price, expiration_date
            ))
        
        # 3 legs strategies
        if max_legs >= 3:
            all_strategies.extend(self._generate_three_leg_strategies(
                price_min, price_max, strike_min, strike_max, target_price, expiration_date
            ))
        
        # 4 legs strategies
        if max_legs >= 4:
            all_strategies.extend(self._generate_four_leg_strategies(
                price_min, price_max, strike_min, strike_max, target_price, expiration_date
            ))
        
        return all_strategies
    
    # ==================== 1 LEG STRATEGIES ====================
    
    def _generate_single_leg_strategies(self,
                                       strike_min: float,
                                       strike_max: float,
                                       target_price: float,
                                       expiration_date: Optional[str] = None) -> List[StrategyComparison]:
        """Génère toutes les stratégies à 1 leg: Long/Short Call/Put"""
        strategies = []
        
        # Déterminer les expirations communes
        if expiration_date:
            expirations = [expiration_date]
        else:
            call_exps = set(self.get_available_expirations('call'))
            put_exps = set(self.get_available_expirations('put'))
            expirations = sorted(call_exps | put_exps)
        
        for exp_date in expirations:
            # Long Call
            for strike in self.get_available_strikes('call', exp_date):
                if strike_min <= strike <= strike_max:
                    opt_dict = self.calls_by_strike_exp.get((strike, exp_date))
                    if opt_dict:
                        strategy = self._create_single_leg_strategy(
                            opt_dict, 'long', 'call', strike, target_price
                        )
                        if strategy:
                            strategies.append(strategy)
            
            # Short Call
            for strike in self.get_available_strikes('call', exp_date):
                if strike_min <= strike <= strike_max:
                    opt_dict = self.calls_by_strike_exp.get((strike, exp_date))
                    if opt_dict:
                        strategy = self._create_single_leg_strategy(
                            opt_dict, 'short', 'call', strike, target_price
                        )
                        if strategy:
                            strategies.append(strategy)
            
            # Long Put
            for strike in self.get_available_strikes('put', exp_date):
                if strike_min <= strike <= strike_max:
                    opt_dict = self.puts_by_strike_exp.get((strike, exp_date))
                    if opt_dict:
                        strategy = self._create_single_leg_strategy(
                            opt_dict, 'long', 'put', strike, target_price
                        )
                        if strategy:
                            strategies.append(strategy)
            
            # Short Put
            for strike in self.get_available_strikes('put', exp_date):
                if strike_min <= strike <= strike_max:
                    opt_dict = self.puts_by_strike_exp.get((strike, exp_date))
                    if opt_dict:
                        strategy = self._create_single_leg_strategy(
                            opt_dict, 'short', 'put', strike, target_price
                        )
                        if strategy:
                            strategies.append(strategy)
        
        return strategies
    
    def _create_single_leg_strategy(self, opt_dict: Dict, position: str, option_type: str,
                                   strike: float, target_price: float) -> Optional[StrategyComparison]:
        """Crée un StrategyComparison pour une stratégie à 1 leg"""
        try:
            opt = dict_to_option(opt_dict, position=position, quantity=1)
            if not opt:
                return None
            
            all_options = [opt]
            
            # Calculer coût/crédit
            cost = opt.premium if position == 'long' else -opt.premium
            
            # Métriques financières
            if option_type == 'call':
                if position == 'long':
                    max_profit = float('inf')  # Illimité
                    max_loss = -cost
                    breakeven = strike + cost
                    profit_at_target = max(0, target_price - strike) - cost
                else:  # short
                    max_profit = cost
                    max_loss = float('-inf')  # Illimité
                    breakeven = strike + cost
                    profit_at_target = -max(0, target_price - strike) + cost
            else:  # put
                if position == 'long':
                    max_profit = strike - cost
                    max_loss = -cost
                    breakeven = strike - cost
                    profit_at_target = max(0, strike - target_price) - cost
                else:  # short
                    max_profit = cost
                    max_loss = -(strike - cost)
                    breakeven = strike - cost
                    profit_at_target = -max(0, strike - target_price) + cost
            
            # Greeks
            greeks = calculate_greeks_by_type(all_options)
            avg_iv = calculate_avg_implied_volatility(all_options)
            
            # Calcul des surfaces (centre = strike de l'option)
            center_strike = strike
            surfaces = self._calculate_surfaces(all_options, center_strike)
            
            strategy_name = f"{'Long' if position == 'long' else 'Short'} {option_type.capitalize()} {strike}"
            
            return StrategyComparison(
                strategy_name=strategy_name,
                strategy=None,
                target_price=target_price,
                max_profit=max_profit if max_profit != float('inf') else 999999.0,
                max_loss=max_loss if max_loss != float('-inf') else -999999.0,
                breakeven_points=[breakeven],
                profit_range=(0, breakeven) if option_type == 'put' else (breakeven, 999999),
                profit_zone_width=abs(breakeven - strike),
                surface_profit=surfaces['profit_surface'],
                surface_loss=surfaces['loss_surface'],
                surface_gauss=surfaces['surface_gauss'],
                risk_reward_ratio=abs(max_loss) / max_profit if max_profit > 0 and max_profit != float('inf') else 0,
                all_options=all_options,
                total_delta_calls=greeks['calls']['delta'],
                total_gamma_calls=greeks['calls']['gamma'],
                total_vega_calls=greeks['calls']['vega'],
                total_theta_calls=greeks['calls']['theta'],
                total_delta_puts=greeks['puts']['delta'],
                total_gamma_puts=greeks['puts']['gamma'],
                total_vega_puts=greeks['puts']['vega'],
                total_theta_puts=greeks['puts']['theta'],
                total_delta=greeks['total']['delta'],
                total_gamma=greeks['total']['gamma'],
                total_vega=greeks['total']['vega'],
                total_theta=greeks['total']['theta'],
                avg_implied_volatility=avg_iv,
                profit_at_target=profit_at_target,
                profit_at_target_pct=0.0,
                score=0.0,
                rank=0
            )
        except Exception as e:
            print(f"⚠️ Erreur création single leg {position} {option_type} {strike}: {e}")
            return None
    
    # ==================== 2 LEGS STRATEGIES ====================
    
    def _generate_two_leg_strategies(self,
                                     price_min: float,
                                     price_max: float,
                                     strike_min: float,
                                     strike_max: float,
                                     target_price: float,
                                     expiration_date: Optional[str] = None) -> List[StrategyComparison]:
        """Génère stratégies à 2 legs: Spreads, Straddle, Strangle"""
        strategies = []
        
        # Déterminer les expirations
        if expiration_date:
            expirations = [expiration_date]
        else:
            call_exps = set(self.get_available_expirations('call'))
            put_exps = set(self.get_available_expirations('put'))
            expirations = sorted(call_exps & put_exps)
        
        for exp_date in expirations:
            call_strikes = [s for s in self.get_available_strikes('call', exp_date) 
                           if strike_min <= s <= strike_max]
            put_strikes = [s for s in self.get_available_strikes('put', exp_date) 
                          if strike_min <= s <= strike_max]
            
            # Bull Call Spread (Long lower strike call + Short higher strike call)
            for i, s1 in enumerate(call_strikes):
                for s2 in call_strikes[i+1:]:
                    strategies.extend(self._create_call_spread(s1, s2, exp_date, target_price, 'bull'))
            
            # Bear Call Spread (Short lower strike call + Long higher strike call)
            for i, s1 in enumerate(call_strikes):
                for s2 in call_strikes[i+1:]:
                    strategies.extend(self._create_call_spread(s1, s2, exp_date, target_price, 'bear'))
            
            # Bull Put Spread (Short lower strike put + Long higher strike put)
            for i, s1 in enumerate(put_strikes):
                for s2 in put_strikes[i+1:]:
                    strategies.extend(self._create_put_spread(s1, s2, exp_date, target_price, 'bull'))
            
            # Bear Put Spread (Long lower strike put + Short higher strike put)
            for i, s1 in enumerate(put_strikes):
                for s2 in put_strikes[i+1:]:
                    strategies.extend(self._create_put_spread(s1, s2, exp_date, target_price, 'bear'))
            
            # Straddle (Long/Short Call + Long/Short Put at same strike)
            common_strikes = set(call_strikes) & set(put_strikes)
            for strike in common_strikes:
                if price_min <= strike <= price_max:
                    # Long Straddle
                    strategies.extend(self._create_straddle(strike, exp_date, target_price, 'long'))
                    # Short Straddle
                    strategies.extend(self._create_straddle(strike, exp_date, target_price, 'short'))
            
            # Strangle (Call and Put at different strikes)
            for call_strike in call_strikes:
                for put_strike in put_strikes:
                    if put_strike < call_strike:
                        center = (put_strike + call_strike) / 2
                        if price_min <= center <= price_max:
                            # Long Strangle
                            strategies.extend(self._create_strangle(
                                put_strike, call_strike, exp_date, target_price, 'long'
                            ))
                            # Short Strangle
                            strategies.extend(self._create_strangle(
                                put_strike, call_strike, exp_date, target_price, 'short'
                            ))
        
        return strategies
    
    def _create_call_spread(self, s1: float, s2: float, exp_date: str, 
                           target_price: float, spread_type: str) -> List[StrategyComparison]:
        """Crée un Call Spread (bull ou bear)"""
        strategies = []
        
        try:
            call1_dict = self.calls_by_strike_exp.get((s1, exp_date))
            call2_dict = self.calls_by_strike_exp.get((s2, exp_date))
            
            if not all([call1_dict, call2_dict]):
                return strategies
            
            if spread_type == 'bull':
                # Bull Call Spread: Long lower + Short higher
                opt1 = dict_to_option(call1_dict, position='long', quantity=1)
                opt2 = dict_to_option(call2_dict, position='short', quantity=1)
                name = f"BullCallSpread {s1}/{s2}"
            else:
                # Bear Call Spread: Short lower + Long higher
                opt1 = dict_to_option(call1_dict, position='short', quantity=1)
                opt2 = dict_to_option(call2_dict, position='long', quantity=1)
                name = f"BearCallSpread {s1}/{s2}"
            
            if not all([opt1, opt2]):
                return strategies
            
            all_options = [opt1, opt2]
            net_cost = sum(opt.premium * opt.quantity * (-1 if opt.position == 'long' else 1) 
                          for opt in all_options)
            
            spread_width = s2 - s1
            
            if spread_type == 'bull':
                max_profit = spread_width - abs(net_cost)
                max_loss = -abs(net_cost)
                breakeven = s1 + abs(net_cost)
                profit_at_target = min(max(0, target_price - s1), spread_width) - abs(net_cost)
            else:
                max_profit = abs(net_cost)
                max_loss = -(spread_width - abs(net_cost))
                breakeven = s1 + abs(net_cost)
                profit_at_target = -min(max(0, target_price - s1), spread_width) + abs(net_cost)
            
            greeks = calculate_greeks_by_type(all_options)
            avg_iv = calculate_avg_implied_volatility(all_options)
            
            # Calcul des surfaces (centre = milieu des strikes)
            center_strike = (s1 + s2) / 2
            surfaces = self._calculate_surfaces(all_options, center_strike)
            
            strategy = StrategyComparison(
                strategy_name=name,
                strategy=None,
                target_price=target_price,
                max_profit=max_profit,
                max_loss=max_loss,
                breakeven_points=[breakeven],
                profit_range=(breakeven, s2) if spread_type == 'bull' else (0, breakeven),
                profit_zone_width=abs(s2 - breakeven),
                surface_profit=surfaces['profit_surface'],
                surface_loss=surfaces['loss_surface'],
                surface_gauss=surfaces['surface_gauss'],
                risk_reward_ratio=abs(max_loss) / max_profit if max_profit > 0 else 0,
                all_options=all_options,
                total_delta_calls=greeks['calls']['delta'],
                total_gamma_calls=greeks['calls']['gamma'],
                total_vega_calls=greeks['calls']['vega'],
                total_theta_calls=greeks['calls']['theta'],
                total_delta_puts=greeks['puts']['delta'],
                total_gamma_puts=greeks['puts']['gamma'],
                total_vega_puts=greeks['puts']['vega'],
                total_theta_puts=greeks['puts']['theta'],
                total_delta=greeks['total']['delta'],
                total_gamma=greeks['total']['gamma'],
                total_vega=greeks['total']['vega'],
                total_theta=greeks['total']['theta'],
                avg_implied_volatility=avg_iv,
                profit_at_target=profit_at_target,
                profit_at_target_pct=(profit_at_target / max_profit * 100) if max_profit > 0 else 0,
                score=0.0,
                rank=0
            )
            strategies.append(strategy)
            
        except Exception as e:
            print(f"⚠️ Erreur création {spread_type} call spread {s1}/{s2}: {e}")
        
        return strategies
    
    def _create_put_spread(self, s1: float, s2: float, exp_date: str,
                          target_price: float, spread_type: str) -> List[StrategyComparison]:
        """Crée un Put Spread (bull ou bear)"""
        strategies = []
        
        try:
            put1_dict = self.puts_by_strike_exp.get((s1, exp_date))
            put2_dict = self.puts_by_strike_exp.get((s2, exp_date))
            
            if not all([put1_dict, put2_dict]):
                return strategies
            
            if spread_type == 'bull':
                # Bull Put Spread: Short lower + Long higher
                opt1 = dict_to_option(put1_dict, position='short', quantity=1)
                opt2 = dict_to_option(put2_dict, position='long', quantity=1)
                name = f"BullPutSpread {s1}/{s2}"
            else:
                # Bear Put Spread: Long lower + Short higher
                opt1 = dict_to_option(put1_dict, position='long', quantity=1)
                opt2 = dict_to_option(put2_dict, position='short', quantity=1)
                name = f"BearPutSpread {s1}/{s2}"
            
            if not all([opt1, opt2]):
                return strategies
            
            all_options = [opt1, opt2]
            net_cost = sum(opt.premium * opt.quantity * (-1 if opt.position == 'long' else 1)
                          for opt in all_options)
            
            spread_width = s2 - s1
            
            if spread_type == 'bull':
                max_profit = abs(net_cost)
                max_loss = -(spread_width - abs(net_cost))
                breakeven = s2 - abs(net_cost)
                profit_at_target = -min(max(0, s2 - target_price), spread_width) + abs(net_cost)
            else:
                max_profit = spread_width - abs(net_cost)
                max_loss = -abs(net_cost)
                breakeven = s2 - abs(net_cost)
                profit_at_target = min(max(0, s2 - target_price), spread_width) - abs(net_cost)
            
            greeks = calculate_greeks_by_type(all_options)
            avg_iv = calculate_avg_implied_volatility(all_options)
            
            # Calcul des surfaces (centre = milieu des strikes)
            center_strike = (s1 + s2) / 2
            surfaces = self._calculate_surfaces(all_options, center_strike)
            
            strategy = StrategyComparison(
                strategy_name=name,
                strategy=None,
                target_price=target_price,
                max_profit=max_profit,
                max_loss=max_loss,
                breakeven_points=[breakeven],
                profit_range=(s1, breakeven) if spread_type == 'bear' else (breakeven, 999999),
                profit_zone_width=abs(breakeven - s1),
                surface_profit=surfaces['profit_surface'],
                surface_loss=surfaces['loss_surface'],
                surface_gauss=surfaces['surface_gauss'],
                risk_reward_ratio=abs(max_loss) / max_profit if max_profit > 0 else 0,
                all_options=all_options,
                total_delta_calls=greeks['calls']['delta'],
                total_gamma_calls=greeks['calls']['gamma'],
                total_vega_calls=greeks['calls']['vega'],
                total_theta_calls=greeks['calls']['theta'],
                total_delta_puts=greeks['puts']['delta'],
                total_gamma_puts=greeks['puts']['gamma'],
                total_vega_puts=greeks['puts']['vega'],
                total_theta_puts=greeks['puts']['theta'],
                total_delta=greeks['total']['delta'],
                total_gamma=greeks['total']['gamma'],
                total_vega=greeks['total']['vega'],
                total_theta=greeks['total']['theta'],
                avg_implied_volatility=avg_iv,
                profit_at_target=profit_at_target,
                profit_at_target_pct=(profit_at_target / max_profit * 100) if max_profit > 0 else 0,
                score=0.0,
                rank=0
            )
            strategies.append(strategy)
            
        except Exception as e:
            print(f"⚠️ Erreur création {spread_type} put spread {s1}/{s2}: {e}")
        
        return strategies
    
    def _create_straddle(self, strike: float, exp_date: str, target_price: float,
                        position: str) -> List[StrategyComparison]:
        """Crée un Straddle (Long ou Short)"""
        strategies = []
        
        try:
            call_dict = self.calls_by_strike_exp.get((strike, exp_date))
            put_dict = self.puts_by_strike_exp.get((strike, exp_date))
            
            if not all([call_dict, put_dict]):
                return strategies
            
            call_opt = dict_to_option(call_dict, position=position, quantity=1)
            put_opt = dict_to_option(put_dict, position=position, quantity=1)
            
            if not all([call_opt, put_opt]):
                return strategies
            
            all_options = [call_opt, put_opt]
            cost = sum(opt.premium for opt in all_options)
            
            if position == 'long':
                max_profit = float('inf')
                max_loss = -cost
                breakeven_low = strike - cost
                breakeven_high = strike + cost
                profit_at_target = abs(target_price - strike) - cost
                name = f"LongStraddle {strike}"
            else:
                max_profit = cost
                max_loss = float('-inf')
                breakeven_low = strike - cost
                breakeven_high = strike + cost
                profit_at_target = -abs(target_price - strike) + cost
                name = f"ShortStraddle {strike}"
            
            greeks = calculate_greeks_by_type(all_options)
            avg_iv = calculate_avg_implied_volatility(all_options)
            
            # Calcul des surfaces (centre = strike du straddle)
            center_strike = strike
            surfaces = self._calculate_surfaces(all_options, center_strike)
            
            strategy = StrategyComparison(
                strategy_name=name,
                strategy=None,
                target_price=target_price,
                max_profit=max_profit if max_profit != float('inf') else 999999.0,
                max_loss=max_loss if max_loss != float('-inf') else -999999.0,
                breakeven_points=[breakeven_low, breakeven_high],
                profit_range=(breakeven_low, breakeven_high) if position == 'short' else (0, breakeven_low),
                profit_zone_width=breakeven_high - breakeven_low,
                surface_profit=surfaces['profit_surface'],
                surface_loss=surfaces['loss_surface'],
                surface_gauss=surfaces['surface_gauss'],
                risk_reward_ratio=abs(max_loss) / max_profit if max_profit > 0 and max_profit != float('inf') else 0,
                all_options=all_options,
                total_delta_calls=greeks['calls']['delta'],
                total_gamma_calls=greeks['calls']['gamma'],
                total_vega_calls=greeks['calls']['vega'],
                total_theta_calls=greeks['calls']['theta'],
                total_delta_puts=greeks['puts']['delta'],
                total_gamma_puts=greeks['puts']['gamma'],
                total_vega_puts=greeks['puts']['vega'],
                total_theta_puts=greeks['puts']['theta'],
                total_delta=greeks['total']['delta'],
                total_gamma=greeks['total']['gamma'],
                total_vega=greeks['total']['vega'],
                total_theta=greeks['total']['theta'],
                avg_implied_volatility=avg_iv,
                profit_at_target=profit_at_target,
                profit_at_target_pct=0.0,
                score=0.0,
                rank=0
            )
            strategies.append(strategy)
            
        except Exception as e:
            print(f"⚠️ Erreur création {position} straddle {strike}: {e}")
        
        return strategies
    
    def _create_strangle(self, put_strike: float, call_strike: float, exp_date: str,
                        target_price: float, position: str) -> List[StrategyComparison]:
        """Crée un Strangle (Long ou Short)"""
        strategies = []
        
        try:
            call_dict = self.calls_by_strike_exp.get((call_strike, exp_date))
            put_dict = self.puts_by_strike_exp.get((put_strike, exp_date))
            
            if not all([call_dict, put_dict]):
                return strategies
            
            call_opt = dict_to_option(call_dict, position=position, quantity=1)
            put_opt = dict_to_option(put_dict, position=position, quantity=1)
            
            if not all([call_opt, put_opt]):
                return strategies
            
            all_options = [put_opt, call_opt]
            cost = sum(opt.premium for opt in all_options)
            
            if position == 'long':
                max_profit = float('inf')
                max_loss = -cost
                breakeven_low = put_strike - cost
                breakeven_high = call_strike + cost
                if target_price <= put_strike:
                    profit_at_target = (put_strike - target_price) - cost
                elif target_price >= call_strike:
                    profit_at_target = (target_price - call_strike) - cost
                else:
                    profit_at_target = -cost
                name = f"LongStrangle {put_strike}/{call_strike}"
            else:
                max_profit = cost
                max_loss = float('-inf')
                breakeven_low = put_strike - cost
                breakeven_high = call_strike + cost
                if target_price <= put_strike:
                    profit_at_target = -(put_strike - target_price) + cost
                elif target_price >= call_strike:
                    profit_at_target = -(target_price - call_strike) + cost
                else:
                    profit_at_target = cost
                name = f"ShortStrangle {put_strike}/{call_strike}"
            
            greeks = calculate_greeks_by_type(all_options)
            avg_iv = calculate_avg_implied_volatility(all_options)
            
            # Calcul des surfaces (centre = milieu entre les deux strikes)
            center_strike = (put_strike + call_strike) / 2
            surfaces = self._calculate_surfaces(all_options, center_strike)
            
            strategy = StrategyComparison(
                strategy_name=name,
                strategy=None,
                target_price=target_price,
                max_profit=max_profit if max_profit != float('inf') else 999999.0,
                max_loss=max_loss if max_loss != float('-inf') else -999999.0,
                breakeven_points=[breakeven_low, breakeven_high],
                profit_range=(breakeven_low, breakeven_high) if position == 'short' else (0, breakeven_low),
                profit_zone_width=breakeven_high - breakeven_low,
                surface_profit=surfaces['profit_surface'],
                surface_loss=surfaces['loss_surface'],
                surface_gauss=surfaces['surface_gauss'],
                risk_reward_ratio=abs(max_loss) / max_profit if max_profit > 0 and max_profit != float('inf') else 0,
                all_options=all_options,
                total_delta_calls=greeks['calls']['delta'],
                total_gamma_calls=greeks['calls']['gamma'],
                total_vega_calls=greeks['calls']['vega'],
                total_theta_calls=greeks['calls']['theta'],
                total_delta_puts=greeks['puts']['delta'],
                total_gamma_puts=greeks['puts']['gamma'],
                total_vega_puts=greeks['puts']['vega'],
                total_theta_puts=greeks['puts']['theta'],
                total_delta=greeks['total']['delta'],
                total_gamma=greeks['total']['gamma'],
                total_vega=greeks['total']['vega'],
                total_theta=greeks['total']['theta'],
                avg_implied_volatility=avg_iv,
                profit_at_target=profit_at_target,
                profit_at_target_pct=0.0,
                score=0.0,
                rank=0
            )
            strategies.append(strategy)
            
        except Exception as e:
            print(f"⚠️ Erreur création {position} strangle {put_strike}/{call_strike}: {e}")
        
        return strategies
    
    # ==================== 3 LEGS STRATEGIES ====================
    
    def _generate_three_leg_strategies(self,
                                       price_min: float,
                                       price_max: float,
                                       strike_min: float,
                                       strike_max: float,
                                       target_price: float,
                                       expiration_date: Optional[str] = None) -> List[StrategyComparison]:
        """Génère stratégies à 3 legs: Butterfly (call/put)"""
        strategies = []
        
        # Importer le générateur de Fly existant
        from myproject.option.fly_generator import FlyGenerator
        
        fly_gen = FlyGenerator({'calls': self.calls_data, 'puts': self.puts_data})
        
        # Call Butterfly
        strategies.extend(fly_gen.generate_all_flies(
            price_min, price_max, target_price, option_type='call', expiration_date=expiration_date))
        
        # Put Butterfly
        strategies.extend(fly_gen.generate_all_flies(
            price_min, price_max, strike_min, strike_max, target_price,
            option_type='put', expiration_date=expiration_date
        ))
        
        return strategies
    
    # ==================== 4 LEGS STRATEGIES ====================
    
    def _generate_four_leg_strategies(self,
                                      price_min: float,
                                      price_max: float,
                                      strike_min: float,
                                      strike_max: float,
                                      target_price: float,
                                      expiration_date: Optional[str] = None) -> List[StrategyComparison]:
        """Génère stratégies à 4 legs: Iron Condor, Call/Put Condor, Iron Butterfly"""
        strategies = []
        
        # Importer le générateur de Condor existant
        from myproject.option.condor_generator import CondorGenerator
        
        condor_gen = CondorGenerator({'calls': self.calls_data, 'puts': self.puts_data})
        
        # Iron Condor
        strategies.extend(condor_gen.generate_iron_condors(
            price_min, price_max, strike_min, strike_max, target_price,
            expiration_date=expiration_date
        ))
        
        # Call Condor
        strategies.extend(condor_gen.generate_call_condors(
            price_min, price_max, strike_min, strike_max, target_price,
            expiration_date=expiration_date
        ))
        
        # Put Condor
        strategies.extend(condor_gen.generate_put_condors(
            price_min, price_max, strike_min, strike_max, target_price,
            expiration_date=expiration_date
        ))
        
        return strategies
