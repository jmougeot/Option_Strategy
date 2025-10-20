"""
Générateur Automatique de Condors - Version Simplifiée
=======================================================
Génère directement des objets StrategyComparison sans classe intermédiaire.
"""

from typing import List, Dict, Optional, Literal
from myproject.option.option_class import Option
from myproject.option.option_utils import (
    dict_to_option, 
    calculate_greeks_by_type, 
    calculate_avg_implied_volatility,
    get_expiration_info,
    get_expiration_key,
    calculate_all_surfaces
)
from myproject.option.comparison_class import StrategyComparison


class CondorGenerator:
    """
    Générateur de stratégies Condor qui retourne directement des StrategyComparison
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
        
        # Paramètres pour le calcul des surfaces (seront mis à jour par generate_*)
        self.price_min = None
        self.price_max = None
    
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
    
    def _index_options(self):
        """Crée des index pour accès rapide par strike et expiration"""
        self.calls_by_strike_exp = {}
        self.puts_by_strike_exp = {}
        
        for call in self.calls_data:
            # Créer clé d'expiration à partir de day/month/year
            exp_key = get_expiration_key(
                call.get('day_of_expiration', 1),
                call.get('month_of_expiration', 'F'),
                call.get('year_of_expiration', 2025)
            )
            key = (call['strike'], exp_key)
            self.calls_by_strike_exp[key] = call
        
        for put in self.puts_data:
            # Créer clé d'expiration à partir de day/month/year
            exp_key = get_expiration_key(
                put.get('day_of_expiration', 1),
                put.get('month_of_expiration', 'F'),
                put.get('year_of_expiration', 2025)
            )
            key = (put['strike'], exp_key)
            self.puts_by_strike_exp[key] = put
    
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
    
    def generate_iron_condors(self,
                              price_min: float,
                              price_max: float,
                              target_price: float,
                              expiration_date: Optional[str] = None,
                              require_symmetric: bool = False,
                              ) -> List[StrategyComparison]:
        """
        Génère toutes les combinaisons possibles d'Iron Condor directement en StrategyComparison
        
        Iron Condor = Short Put Spread + Short Call Spread
        Structure: Long Put (strike1) + Short Put (strike2) + Short Call (strike3) + Long Call (strike4)
        """
        # Stocker les paramètres de prix pour le calcul des surfaces
        self.price_min = price_min
        self.price_max = price_max
        
        strategies = []
        
        # Déterminer les expirations
        if expiration_date:
            expirations = [expiration_date]
        else:
            call_exps = set(self.get_available_expirations('call'))
            put_exps = set(self.get_available_expirations('put'))
            expirations = sorted(call_exps & put_exps)
        
        # Pour chaque expiration
        for exp_date in expirations:
            call_strikes = self.get_available_strikes('call', exp_date)
            put_strikes = self.get_available_strikes('put', exp_date)
            common_strikes = sorted(set(call_strikes) & set(put_strikes))
            valid_strikes = [s for s in common_strikes]
            
            if len(valid_strikes) < 4:
                continue
            
            # Générer toutes les combinaisons de 4 strikes
            for i, s1 in enumerate(valid_strikes):
                for j, s2 in enumerate(valid_strikes[i+1:], start=i+1):
                    for k, s3 in enumerate(valid_strikes[j+1:], start=j+1):
                        for l, s4 in enumerate(valid_strikes[k+1:], start=k+1):
                            # Calculer les métriques
                            lower_spread = s2 - s1
                            upper_spread = s4 - s3
                            body = s3 - s2
                            center = (s2 + s3) / 2
                            
                            # Vérifier contraintes
                            if not (price_min <= center <= price_max):
                                continue
                            if require_symmetric and abs(lower_spread - upper_spread) > 0.01:
                                continue
                            
                            # Récupérer les options
                            put1 = self.puts_by_strike_exp.get((s1, exp_date))
                            put2 = self.puts_by_strike_exp.get((s2, exp_date))
                            call3 = self.calls_by_strike_exp.get((s3, exp_date))
                            call4 = self.calls_by_strike_exp.get((s4, exp_date))
                            
                            if not all([put1, put2, call3, call4]):
                                continue
                            
                            # Créer la stratégie directement
                            strategy = self._create_iron_condor_strategy(
                                s1, s2, s3, s4, exp_date, target_price,
                                put1, put2, call3, call4,
                                lower_spread, upper_spread, body, center
                            )
                            
                            if strategy:
                                strategies.append(strategy)
        
        return strategies
    
    def _create_iron_condor_strategy(self, s1: float, s2: float, s3: float, s4: float,
                                    exp_date: str, target_price: float,
                                    put1: Dict, put2: Dict, call3: Dict, call4: Dict,
                                    lower_spread: float, upper_spread: float,
                                    body: float, center: float) -> Optional[StrategyComparison]:
        """Crée un objet StrategyComparison pour un Iron Condor"""
        try:
            # Construire la liste d'options
            all_options = []
            
            opt1 = dict_to_option(put1, position='long', quantity=1)
            if opt1: all_options.append(opt1)
            
            opt2 = dict_to_option(put2, position='short', quantity=1)
            if opt2: all_options.append(opt2)
            
            opt3 = dict_to_option(call3, position='short', quantity=1)
            if opt3: all_options.append(opt3)
            
            opt4 = dict_to_option(call4, position='long', quantity=1)
            if opt4: all_options.append(opt4)
            
            if len(all_options) != 4:
                return None
            
            # Calculer crédit net
            net_credit = sum(
                opt.premium * opt.quantity * (-1 if opt.position == 'long' else 1)
                for opt in all_options
            )
            
            # Métriques financières
            max_profit = net_credit
            max_spread = max(lower_spread, upper_spread)
            max_loss = -(max_spread - net_credit)
            
            # Breakeven
            breakeven_points = [s2 - net_credit, s3 + net_credit]
            profit_range = (breakeven_points[0], breakeven_points[1])
            profit_zone_width = profit_range[1] - profit_range[0]
            
            # Risk/Reward
            risk_reward_ratio = abs(max_loss) / max_profit if max_profit > 0 else 0
            
            # Profit au prix cible
            profit_at_target = self._calculate_iron_condor_pnl(target_price, s1, s2, s3, s4, net_credit)
            profit_at_target_pct = (profit_at_target / max_profit * 100) if max_profit > 0 else 0
            
            # Greeks
            greeks = calculate_greeks_by_type(all_options)
            avg_iv = calculate_avg_implied_volatility(all_options)
            
            # Calcul des surfaces (centre = milieu entre s2 et s3, le body du condor)
            center_strike = (s2 + s3) / 2
            surfaces = self._calculate_surfaces(all_options, center_strike)
            
            # Date d'expiration
            exp_info = get_expiration_info(all_options)
            
            return StrategyComparison(
                strategy_name=f"IronCondor {s1}/{s2}/{s3}/{s4}",
                strategy=None,
                target_price=target_price,
                max_profit=max_profit,
                max_loss=max_loss,
                breakeven_points=breakeven_points,
                profit_range=profit_range,
                profit_zone_width=profit_zone_width,
                surface_profit=surfaces['profit_surface'],
                surface_loss=surfaces['loss_surface'],
                surface_gauss=surfaces['surface_gauss'],
                risk_reward_ratio=risk_reward_ratio,
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
                profit_at_target_pct=profit_at_target_pct,
                score=0.0,
                rank=0
            )
        except Exception as e:
            print(f"⚠️ Erreur création Iron Condor {s1}/{s2}/{s3}/{s4}: {e}")
            return None
    
    def _calculate_iron_condor_pnl(self, price: float, s1: float, s2: float, s3: float, s4: float, credit: float) -> float:
        """Calcule le P&L d'un Iron Condor à un prix donné"""
        if price <= s1:
            lower_spread = s2 - s1
            return -(lower_spread - credit)
        elif price < s2:
            return -((s2 - price) - credit)
        elif price >= s4:
            upper_spread = s4 - s3
            return -(upper_spread - credit)
        elif price > s3:
            return -((price - s3) - credit)
        else:  # Entre s2 et s3
            return credit
    
    def generate_call_condors(self, *args, **kwargs) -> List[StrategyComparison]:
        """Génère des Call Condors"""
        kwargs['option_type'] = 'call'
        return self._generate_single_type_condors(*args, **kwargs)
    
    def generate_put_condors(self, *args, **kwargs) -> List[StrategyComparison]:
        """Génère des Put Condors"""
        kwargs['option_type'] = 'put'
        return self._generate_single_type_condors(*args, **kwargs)
    
    def _generate_single_type_condors(self,
                                     price_min: float,
                                     price_max: float,
                                     strike_min: float,
                                     strike_max: float,
                                     target_price: float,
                                     option_type: str,
                                     expiration_date: Optional[str] = None,
                                     require_symmetric: bool = False,
                                     min_wing_width: float = 0.25,
                                     max_wing_width: float = 5.0,
                                     min_body_width: float = 0.5,
                                     max_body_width: float = 10.0) -> List[StrategyComparison]:
        """Génère des Condors d'un seul type (call ou put)"""
        # Stocker les paramètres de prix pour le calcul des surfaces
        self.price_min = price_min
        self.price_max = price_max
        
        strategies = []
        
        # Déterminer les expirations
        if expiration_date:
            expirations = [expiration_date]
        else:
            expirations = self.get_available_expirations(option_type)
        
        for exp_date in expirations:
            available_strikes = self.get_available_strikes(option_type, exp_date)
            valid_strikes = [s for s in available_strikes if strike_min <= s <= strike_max]
            
            if len(valid_strikes) < 4:
                continue
            
            for i, s1 in enumerate(valid_strikes):
                for j, s2 in enumerate(valid_strikes[i+1:], start=i+1):
                    for k, s3 in enumerate(valid_strikes[j+1:], start=j+1):
                        for l, s4 in enumerate(valid_strikes[k+1:], start=k+1):
                            lower_wing = s2 - s1
                            upper_wing = s4 - s3
                            body = s3 - s2
                            center = (s2 + s3) / 2
                            
                            # Vérifier contraintes
                            if not (price_min <= center <= price_max):
                                continue
                            if lower_wing < min_wing_width or lower_wing > max_wing_width:
                                continue
                            if upper_wing < min_wing_width or upper_wing > max_wing_width:
                                continue
                            if body < min_body_width or body > max_body_width:
                                continue
                            if require_symmetric and abs(lower_wing - upper_wing) > 0.01:
                                continue
                            
                            # Récupérer les options
                            index = self.calls_by_strike_exp if option_type == 'call' else self.puts_by_strike_exp
                            opt1_dict = index.get((s1, exp_date))
                            opt2_dict = index.get((s2, exp_date))
                            opt3_dict = index.get((s3, exp_date))
                            opt4_dict = index.get((s4, exp_date))
                            
                            if not all([opt1_dict, opt2_dict, opt3_dict, opt4_dict]):
                                continue
                            
                            # Créer la stratégie
                            strategy = self._create_single_type_condor_strategy(
                                s1, s2, s3, s4, exp_date, target_price, option_type,
                                opt1_dict, opt2_dict, opt3_dict, opt4_dict,
                                lower_wing, upper_wing, body
                            )
                            
                            if strategy:
                                strategies.append(strategy)
        
        return strategies
    
    def _create_single_type_condor_strategy(self, s1: float, s2: float, s3: float, s4: float,
                                           exp_date: str, target_price: float, option_type: str,
                                           opt1_dict: Dict, opt2_dict: Dict, opt3_dict: Dict, opt4_dict: Dict,
                                           lower_wing: float, upper_wing: float, body: float) -> Optional[StrategyComparison]:
        """Crée un StrategyComparison pour un Call/Put Condor"""
        try:
            # Construire la liste d'options (Long 1 + Short 2 + Long 1)
            all_options = []
            
            opt1 = dict_to_option(opt1_dict, position='long', quantity=1)
            if opt1: all_options.append(opt1)
            
            opt2 = dict_to_option(opt2_dict, position='short', quantity=1)
            if opt2: all_options.append(opt2)
            
            opt3 = dict_to_option(opt3_dict, position='short', quantity=1)
            if opt3: all_options.append(opt3)
            
            opt4 = dict_to_option(opt4_dict, position='long', quantity=1)
            if opt4: all_options.append(opt4)
            
            if len(all_options) != 4:
                return None
            
            # Calculer débit net
            net_debit = sum(
                opt.premium * opt.quantity * (-1 if opt.position == 'long' else 1)
                for opt in all_options
            )
            debit = abs(net_debit)
            
            # Métriques financières
            max_profit = max(0, body - debit)
            max_loss = -debit
            
            # Breakeven
            breakeven_points = [s1 + debit, s4 - debit]
            profit_range = (breakeven_points[0], breakeven_points[1])
            profit_zone_width = profit_range[1] - profit_range[0]
            
            risk_reward_ratio = abs(max_loss) / max_profit if max_profit > 0 else 0
            
            # Profit au prix cible
            profit_at_target = self._calculate_single_condor_pnl(target_price, s1, s2, s3, s4, debit, body)
            profit_at_target_pct = (profit_at_target / max_profit * 100) if max_profit > 0 else 0
            
            # Greeks
            greeks = calculate_greeks_by_type(all_options)
            avg_iv = calculate_avg_implied_volatility(all_options)
            
            # Calcul des surfaces (centre = milieu du body entre s2 et s3)
            center_strike = (s2 + s3) / 2
            surfaces = self._calculate_surfaces(all_options, center_strike)
            
            return StrategyComparison(
                strategy_name=f"Long{'Call' if option_type == 'call' else 'Put'}Condor {s1}/{s2}/{s3}/{s4}",
                strategy=None,
                target_price=target_price,
                max_profit=max_profit,
                max_loss=max_loss,
                breakeven_points=breakeven_points,
                profit_range=profit_range,
                profit_zone_width=profit_zone_width,
                surface_profit=surfaces['profit_surface'],
                surface_loss=surfaces['loss_surface'],
                surface_gauss=surfaces['surface_gauss'],
                risk_reward_ratio=risk_reward_ratio,
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
                profit_at_target_pct=profit_at_target_pct,
                score=0.0,
                rank=0
            )
        except Exception as e:
            print(f"⚠️ Erreur création {option_type} Condor {s1}/{s2}/{s3}/{s4}: {e}")
            return None
    
    def _calculate_single_condor_pnl(self, price: float, s1: float, s2: float, s3: float, s4: float, 
                                    debit: float, body: float) -> float:
        """Calcule le P&L d'un Call/Put Condor à un prix donné"""
        if price <= s1 or price >= s4:
            return -debit
        elif price < s2:
            return (price - s1) - debit
        elif price > s3:
            return (s4 - price) - debit
        else:  # Dans le corps
            return body - debit
