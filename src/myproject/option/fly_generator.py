"""
Générateur Automatique de Butterflies - Version Simplifiée
===========================================================
Génère directement des objets StrategyComparison sans classe intermédiaire.
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from myproject.option.option_class import Option
from myproject.option.option_utils import (
    dict_to_option,
    calculate_greeks_by_type,
    calculate_avg_implied_volatility,
    calculate_all_surfaces,
    get_expiration_key
)
from myproject.option.comparison_class import StrategyComparison


class FlyGenerator:
    """
    Générateur de stratégies Butterfly qui retourne directement des StrategyComparison
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
        
        # Paramètres pour le calcul des surfaces (seront mis à jour par generate_butterflies)
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
    
    def generate_all_flies(self,
                          price_min: float,
                          price_max: float,
                          target_price: float,
                          option_type: str = 'call',
                          expiration_date: Optional[str] = None,
                          require_symmetric: bool = False,
                          min_wing_width: float = 0.25,
                          max_wing_width: float = 5.0) -> List[StrategyComparison]:
        """
        Génère toutes les combinaisons possibles de Butterfly directement en StrategyComparison
        
        Butterfly = Long 1 lower + Short 2 middle + Long 1 upper
        
        Args:
            price_min: Prix minimum pour le strike central
            price_max: Prix maximum pour le strike central  
            strike_min: Strike minimum
            strike_max: Strike maximum
            target_price: Prix cible du sous-jacent
            option_type: 'call' ou 'put'
            expiration_date: Date d'expiration (optionnel)
            require_symmetric: N'accepter que les structures symétriques
            min_wing_width: Largeur minimale des ailes
            max_wing_width: Largeur maximale des ailes
            
        Returns:
            Liste de StrategyComparison
        """
        # Stocker les paramètres de prix pour le calcul des surfaces
        self.price_min = price_min
        self.price_max = price_max
        
        strategies = []
        
        # Déterminer les expirations
        if expiration_date:
            expirations = [expiration_date]
        else:
            expirations = self.get_available_expirations(option_type)
        
        # Pour chaque expiration
        for exp_date in expirations:
            # Récupérer les strikes disponibles
            available_strikes = self.get_available_strikes(option_type, exp_date)
            
            # Filtrer dans les bornes
            valid_strikes = [s for s in available_strikes]
            
            if len(valid_strikes) < 3:
                continue  # Pas assez de strikes pour un Butterfly
            
            # Générer toutes les combinaisons de 3 strikes
            for i, lower_strike in enumerate(valid_strikes):
                for j, middle_strike in enumerate(valid_strikes[i+1:], start=i+1):
                    for k, upper_strike in enumerate(valid_strikes[j+1:], start=j+1):
                        # Calculer les métriques
                        wing_width_lower = middle_strike - lower_strike
                        wing_width_upper = upper_strike - middle_strike
                        
                        # Vérifier que le middle strike est dans l'intervalle de prix
                        if not (price_min <= middle_strike <= price_max):
                            continue
                        
                        # Vérifier les contraintes de largeur
                        if wing_width_lower < min_wing_width or wing_width_lower > max_wing_width:
                            continue
                        if wing_width_upper < min_wing_width or wing_width_upper > max_wing_width:
                            continue
                        
                        # Vérifier la symétrie si requis
                        if require_symmetric and abs(wing_width_lower - wing_width_upper) > 0.01:
                            continue
                        
                        # Récupérer les options
                        index = self.calls_by_strike_exp if option_type.lower() == 'call' else self.puts_by_strike_exp
                        
                        lower_opt = index.get((lower_strike, exp_date))
                        middle_opt = index.get((middle_strike, exp_date))
                        upper_opt = index.get((upper_strike, exp_date))
                        
                        # Vérifier que toutes les options existent
                        if not lower_opt or not middle_opt or not upper_opt:
                            continue
                        
                        # À ce stade, on sait que lower_opt, middle_opt, upper_opt ne sont pas None
                        # Créer la stratégie directement
                        strategy = self._create_butterfly_strategy(
                            lower_strike, middle_strike, upper_strike,
                            exp_date, target_price, option_type,
                            lower_opt, middle_opt, upper_opt,
                            wing_width_lower, wing_width_upper
                        )
                        
                        if strategy:
                            strategies.append(strategy)
        
        return strategies
    
    def _create_butterfly_strategy(self, lower_strike: float, middle_strike: float, upper_strike: float,
                                   exp_date: str, target_price: float, option_type: str,
                                   lower_opt_dict: Dict, middle_opt_dict: Dict, upper_opt_dict: Dict,
                                   wing_width_lower: float, wing_width_upper: float) -> Optional[StrategyComparison]:
        """Crée un objet StrategyComparison pour un Butterfly"""
        try:
            # Construire la liste d'options (Long 1 + Short 2 + Long 1)
            all_options = []
            
            opt1 = dict_to_option(lower_opt_dict, position='long', quantity=1)
            if opt1: all_options.append(opt1)
            
            opt2 = dict_to_option(middle_opt_dict, position='short', quantity=2)
            if opt2: all_options.append(opt2)
            
            opt3 = dict_to_option(upper_opt_dict, position='long', quantity=1)
            if opt3: all_options.append(opt3)
            
            if len(all_options) != 3:
                return None
            
            # Calculer débit net
            net_debit = sum(
                opt.premium * opt.quantity * (-1 if opt.position == 'long' else 1)
                for opt in all_options
            )
            debit = abs(net_debit)
            
            # Métriques financières
            wing_width = min(wing_width_lower, wing_width_upper)
            max_profit = max(0, wing_width - debit)
            max_loss = -debit
            
            # Breakeven
            breakeven_points = [
                lower_strike + debit,
                upper_strike - debit
            ]
            profit_range = (breakeven_points[0], breakeven_points[1])
            profit_zone_width = profit_range[1] - profit_range[0]
            
            # Risk/Reward
            risk_reward_ratio = abs(max_loss) / max_profit if max_profit > 0 else 0
            
            # Profit au prix cible
            profit_at_target = self._calculate_butterfly_pnl(
                target_price, lower_strike, middle_strike, upper_strike, debit, wing_width
            )
            profit_at_target_pct = (profit_at_target / max_profit * 100) if max_profit > 0 else 0
            
            # Greeks
            greeks = calculate_greeks_by_type(all_options)
            avg_iv = calculate_avg_implied_volatility(all_options)
            
            # Calcul des surfaces (centre = middle_strike du butterfly)
            center_strike = middle_strike
            surfaces = self._calculate_surfaces(all_options, center_strike)


            # Date d'expiration
            expiration_month = all_options[0].expiration_month
            expiration_year = all_options[0].expiration_year
            
            return StrategyComparison(
                strategy_name=f"{'Call' if option_type == 'call' else 'Put'}Fly {lower_strike}/{middle_strike}/{upper_strike}",
                strategy=None,
                expiration_day=None,
                expiration_week=None,
                expiration_month= expiration_month,
                expiration_year=expiration_year,
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
            print(f"⚠️ Erreur création Butterfly {lower_strike}/{middle_strike}/{upper_strike}: {e}")
            return None
    
    def _calculate_butterfly_pnl(self, price: float, lower_strike: float, middle_strike: float, 
                                upper_strike: float, debit: float, wing_width: float) -> float:
        """Calcule le P&L d'un Butterfly à un prix donné"""
        if price <= lower_strike or price >= upper_strike:
            return -debit
        elif price < middle_strike:
            return (price - lower_strike) - debit
        elif price > middle_strike:
            return (upper_strike - price) - debit
        else:  # price == middle_strike
            return wing_width - debit
