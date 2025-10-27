"""
Générateur V2 de Stratégies d'Options
======================================
Version simplifiée qui prend une liste d'objets Option et génère toutes les
combinaisons possibles (1 à 4 options) pour créer des StrategyComparison.

Utilise itertools.combinations pour générer efficacement toutes les combinaisons.
"""
from itertools import product
from typing import List, Dict, Tuple, Optional, Literal
from itertools import combinations
from myproject.option.option_class import Option
from myproject.option.comparison_class import StrategyComparison
from myproject.option.calcul_linear_metrics import calculate_linear_metrics
from myproject.option.option_filter import sort_options_by_expiration
from myproject.option.option_utils_v2 import get_expiration_info
from myproject.bloomberg.bloomberg_data_importer import import_euribor_options


class OptionStrategyGeneratorV2:
    """
    Génère toutes les stratégies possibles à partir d'une liste d'options.
    Teste toutes les combinaisons de 1 à 4 options avec différentes positions (long/short).
    """
    
    def __init__(self, options: List[Option]):
        """
        Initialise le générateur avec une liste d'options triées par expiration.
        
        Args:
            options: Liste d'objets Option récupérés depuis Bloomberg
        """
        # Trier les options par expiration une seule fois au début
        self.options = sort_options_by_expiration(options)
        self.price_min = None
        self.price_max = None
    
    @classmethod
    def from_bloomberg_data(cls,
                           underlying: str = "ER",
                           months: List[str] = [],
                           years: List[int] = [],
                           strikes: List[float] = [],
                           default_position: Literal['long', 'short'] = 'long',
                           default_quantity: int = 1,
                           price_min: Optional[float] = None,
                           price_max: Optional[float] = None,
                           calculate_surfaces: bool = True
                           ) -> "OptionStrategyGeneratorV2":
        """
        Crée un générateur à partir de données Bloomberg.
        
        Args:
            underlying: Symbole du sous-jacent (ex: "ER")
            months: Liste des mois Bloomberg (ex: ['M', 'U'])
            years: Liste des années (ex: [6, 7])
            strikes: Liste des strikes
            default_position: Position par défaut
            default_quantity: Quantité par défaut
            price_min: Prix min pour surfaces
            price_max: Prix max pour surfaces
            calculate_surfaces: Si True, calcule les surfaces
        """
        # Importer directement les options depuis Bloomberg
        options = import_euribor_options(
            underlying=underlying,
            months=months,
            years=years,
            strikes=strikes,
            default_position=default_position,
            default_quantity=default_quantity,
            price_min=price_min,
            price_max=price_max,
            calculate_surfaces=calculate_surfaces,
            num_points=200
        )
        
        if not options:
            print("⚠️ Aucune option valide après import Bloomberg")
        
        return cls(options)
    
    def generate_all_combinations(self,
                                  target_price: float,
                                  price_min: float,
                                  price_max: float,
                                  max_legs: int = 4,
                                  include_long: bool = True,
                                  include_short: bool = True) -> List[StrategyComparison]:
        """
        Génère toutes les combinaisons possibles d'options (1 à max_legs).
        """
        self.price_min = price_min
        self.price_max = price_max
        
        all_strategies = []
        
        # Générer les combinaisons pour chaque taille (1 à max_legs)
        for n_legs in range(1, min(max_legs + 1, 5)):  # Max 4 legs
            print(f"🔄 Génération des stratégies à {n_legs} leg(s)...")
            
            # Générer toutes les combinaisons de n_legs options
            for combo in combinations(self.options, n_legs):
                # Pour chaque combinaison, tester différentes configurations de positions
                strategies = self._generate_position_variants(
                    list(combo), 
                    target_price, 
                    include_long, 
                    include_short
                )
                all_strategies.extend(strategies)
        
        print(f"✅ {len(all_strategies)} stratégies générées au total")
        return all_strategies
    
    def _generate_position_variants(
        self,
        options: List[Option],
        target_price: float,
        include_long: bool,
        include_short: bool
    ) -> List[StrategyComparison]:
        """
        Génère les variantes de positions pour une combinaison d'options.
        Teste long/short selon include_long/include_short.
        
        Note: Les options sont déjà triées par expiration dans __init__.
        On vérifie simplement que la première et la dernière ont la même date.
        """
        n = len(options)
        if n == 0:
            return []
        
        # ===== Vérification d'échéance (ultra-rapide) =====
        # Comme les options sont triées, si première == dernière, toutes sont identiques
        if n > 1:
            first, last = options[0], options[-1]
            # Vérifier année, mois, semaine ET jour
            if (first.expiration_year != last.expiration_year or 
                first.expiration_month != last.expiration_month or
                first.expiration_week != last.expiration_week or
                first.expiration_day != last.expiration_day):
                return []  # Dates d'échéance différentes

        n = len(options)
        if n == 0:
            return []

        # ===== Espace des positions =====
        if include_long and include_short:
            # -1 = long, +1 = short (plus simple à manipuler que des strings)
            sign_space = list(product((-1, 1), repeat=n))
        elif include_long:
            sign_space = [(-1,) * n]
        elif include_short:
            sign_space = [(1,) * n]
        else:
            return []

        strategies: List[StrategyComparison] = []

        # ===== Génération des stratégies =====
        # Si tu veux conserver 'long'/'short', mappe le signe -> libellé à l’appel
        for signs in sign_space:
            positions = ['long' if s == -1 else 'short' for s in signs]
            strat = self._create_strategy(options, positions, target_price)
            if strat:
                strategies.append(strat)

        return strategies    

    def _create_strategy(self,
                        options: List[Option],
                        positions: List[str],
                        target_price: float) -> Optional[StrategyComparison]:
        """
        Crée un StrategyComparison à partir d'une combinaison d'options et de positions.
        
        Args:
            options: Liste d'options
            positions: Liste des positions correspondantes ('long' ou 'short')
            target_price: Prix cible
            
        Returns:
            StrategyComparison ou None si la stratégie est invalide
        """
        try:
            # Créer des copies des options avec les bonnes positions
            option_legs = []
            for opt, pos in zip(options, positions):
                # Assurer que pos est bien 'long' ou 'short'
                position_type = 'long' if pos == 'long' else 'short'
                
                # Créer une copie de l'option avec la position modifiée
                opt_copy = Option(
                    option_type=opt.option_type,
                    strike=opt.strike,
                    premium=opt.premium,
                    expiration_day=opt.expiration_day,
                    expiration_week=opt.expiration_week,
                    expiration_month=opt.expiration_month,
                    expiration_year=opt.expiration_year,
                    quantity=opt.quantity,
                    position=position_type,  # Utiliser la variable typée
                    ticker=opt.ticker,
                    underlying_symbol=opt.underlying_symbol,
                    bid=opt.bid,
                    ask=opt.ask,
                    delta=opt.delta,
                    gamma=opt.gamma,
                    vega=opt.vega,
                    theta=opt.theta,
                    implied_volatility=opt.implied_volatility
                )
                option_legs.append(opt_copy)
            
            # Générer le nom de la stratégie
            strategy_name = self._generate_strategy_name(option_legs)
            
            # ============ CALCUL DE TOUTES LES MÉTRIQUES EN UNE FOIS ============
            # calculate_linear_metrics calcule TOUT : linéaires + surfaces (si paramètres fournis)
            all_metrics = calculate_linear_metrics(
                option_legs,
                price_min=self.price_min,
                price_max=self.price_max,
                num_points=1000,  # Activer le calcul des surfaces
            )
            
            # Calculer max_profit, max_loss, breakevens (métriques non-linéaires)
            metrics = self._calculate_strategy_metrics(
                option_legs,
                target_price
            )
            
            # Extraire les informations d'expiration
            exp_info = get_expiration_info(option_legs)
            
            # Créer le StrategyComparison
            strategy = StrategyComparison(
                strategy_name=strategy_name,
                strategy=None,  # Pas d'objet OptionStrategy, juste les métriques
                target_price=target_price,
                expiration_day=exp_info.get('expiration_day'),
                expiration_week=exp_info.get('expiration_week'),
                expiration_month=exp_info.get('expiration_month', 'F'),
                expiration_year=exp_info.get('expiration_year', 6),
                max_profit=metrics['max_profit'],
                max_loss=metrics['max_loss'],
                breakeven_points=metrics['breakeven_points'],
                profit_range=metrics['profit_range'],
                profit_zone_width=metrics['profit_zone_width'],
                surface_profit=all_metrics['profit_surface'],
                surface_loss=all_metrics['loss_surface'],
                risk_reward_ratio=abs(metrics['max_loss']) / metrics['max_profit'] if metrics['max_profit'] > 0 else 0,
                all_options=option_legs,
                # Greeks (from all_metrics)
                total_delta_calls=all_metrics['delta_calls'],
                total_gamma_calls=all_metrics['gamma_calls'],
                total_vega_calls=all_metrics['vega_calls'],
                total_theta_calls=all_metrics['theta_calls'],
                total_delta_puts=all_metrics['delta_puts'],
                total_gamma_puts=all_metrics['gamma_puts'],
                total_vega_puts=all_metrics['vega_puts'],
                total_theta_puts=all_metrics['theta_puts'],
                total_delta=all_metrics['delta_total'],
                total_gamma=all_metrics['gamma_total'],
                total_vega=all_metrics['vega_total'],
                total_theta=all_metrics['theta_total'],
                avg_implied_volatility=all_metrics['avg_implied_volatility'],
                profit_at_target=metrics['profit_at_target'],
                profit_at_target_pct=(metrics['profit_at_target'] / metrics['max_profit'] * 100) 
                                     if metrics['max_profit'] > 0 and metrics['max_profit'] != float('inf') else 0,
                score=0.0,
                rank=0
            )
            
            return strategy
            
        except Exception as e:
            print(f"⚠️ Erreur création stratégie: {e}")
            return None  
    
    def _generate_strategy_name(self, options: List[Option]) -> str:
        """
        Génère un nom descriptif pour la stratégie.
        
        Args:
            options: Liste d'options
            
        Returns:
            Nom de la stratégie
        """
        n_legs = len(options)
        
        # Compter les calls et puts, long et short
        calls = [o for o in options if o.option_type == 'call']
        puts = [o for o in options if o.option_type == 'put']
        longs = [o for o in options if o.position == 'long']
        shorts = [o for o in options if o.position == 'short']
        
        # Récupérer les strikes uniques
        strikes = sorted(set(o.strike for o in options))
        strikes_str = '/'.join([f"{s:.2f}" for s in strikes])
        
        # Stratégies connues (reconnaissance de patterns)
        if n_legs == 1:
            opt = options[0]
            return f"{'Long' if opt.position == 'long' else 'Short'} {opt.option_type.capitalize()} {opt.strike:.2f}"
        
        elif n_legs == 2:
            # Spread, Straddle, Strangle
            if len(calls) == 2 and len(strikes) == 2:
                if len(longs) == 1 and len(shorts) == 1:
                    return f"CallSpread {strikes_str}"
            elif len(puts) == 2 and len(strikes) == 2:
                if len(longs) == 1 and len(shorts) == 1:
                    return f"PutSpread {strikes_str}"
            elif len(calls) == 1 and len(puts) == 1:
                if len(strikes) == 1:
                    return f"{'Long' if len(longs) == 2 else 'Short'}Straddle {strikes[0]:.2f}"
                else:
                    return f"{'Long' if len(longs) == 2 else 'Short'}Strangle {strikes_str}"
        
        elif n_legs == 3:
            # Butterfly
            if len(strikes) == 3:
                if len(calls) == 3:
                    return f"CallButterfly {strikes_str}"
                elif len(puts) == 3:
                    return f"PutButterfly {strikes_str}"
        
        elif n_legs == 4:
            # Condor, Iron Condor
            if len(strikes) == 4:
                if len(calls) == 4:
                    return f"CallCondor {strikes_str}"
                elif len(puts) == 4:
                    return f"PutCondor {strikes_str}"
                elif len(calls) == 2 and len(puts) == 2:
                    return f"IronCondor {strikes_str}"
        
        # Nom générique si non reconnu
        return f"{n_legs}Leg_{len(calls)}C{len(puts)}P_{strikes_str}"
    
    def _calculate_strategy_metrics(self,
                                    options: List[Option],
                                    target_price: float) -> Dict:
        """
        Calcule les métriques financières de la stratégie (max_profit, max_loss, breakevens).
        
        Args:
            options: Liste d'options
            net_cost: Coût net de la stratégie (négatif = crédit)
            target_price: Prix cible
            
        Returns:
            Dictionnaire avec les métriques
        """
        # Calculer le P&L pour une plage de prix
        strikes = sorted(set(opt.strike for opt in options))
        min_strike = min(strikes)
        max_strike = max(strikes)
        
        # Plage de prix pour calculer max_profit/max_loss
        price_range = [min_strike - 10, min_strike, *strikes, max_strike, max_strike + 10]
        
        pnl_values = []
        for price in price_range:
            pnl = self._calculate_pnl_at_price(options, price)
            pnl_values.append((price, pnl))
        
        # Trouver max_profit et max_loss
        max_profit = max(pnl for _, pnl in pnl_values)
        max_loss = min(pnl for _, pnl in pnl_values)
        
        # Limiter les valeurs infinies
        if max_profit == float('inf') or max_profit > 100000:
            max_profit = 999999.0
        if max_loss == float('-inf') or max_loss < -100000:
            max_loss = -999999.0
        
        # Calculer les breakevens (prix où P&L = 0)
        breakeven_points = self._find_breakevens(options, strikes)
        
        # Calculer profit_range et profit_zone_width
        if len(breakeven_points) >= 2:
            profit_range = (breakeven_points[0], breakeven_points[-1])
            profit_zone_width = breakeven_points[-1] - breakeven_points[0]
        elif len(breakeven_points) == 1:
            profit_range = (breakeven_points[0], max_strike + 10)
            profit_zone_width = max_strike + 10 - breakeven_points[0]
        else:
            profit_range = (min_strike, max_strike)
            profit_zone_width = max_strike - min_strike
        
        # Calculer profit_at_target
        profit_at_target = self._calculate_pnl_at_price(options, target_price)
        
        return {
            'max_profit': max_profit,
            'max_loss': max_loss,
            'breakeven_points': breakeven_points,
            'profit_range': profit_range,
            'profit_zone_width': profit_zone_width,
            'profit_at_target': profit_at_target
        }
    
    def _calculate_pnl_at_price(self, options: List[Option], price: float) -> float:
        """
        Calcule le P&L de la stratégie à un prix donné à l'expiration.
        
        Args:
            options: Liste d'options
            price: Prix du sous-jacent
            
        Returns:
            P&L total
        """
        total_pnl = 0.0
        
        for opt in options:
            # Coût initial (négatif si long, positif si short)
            cost = opt.premium * (-1 if opt.position == 'long' else 1)
            
            # Valeur intrinsèque à l'expiration
            if opt.option_type == 'call':
                intrinsic_value = max(0, price - opt.strike)
            else:  # put
                intrinsic_value = max(0, opt.strike - price)
            
            # P&L pour cette option
            if opt.position == 'long':
                pnl = intrinsic_value - opt.premium
            else:  # short
                pnl = opt.premium - intrinsic_value
            
            total_pnl += pnl
        
        return total_pnl
    
    def _find_breakevens(self, options: List[Option], strikes: List[float]) -> List[float]:
        """
        Trouve les points de breakeven (où P&L = 0).
        
        Args:
            options: Liste d'options
            strikes: Liste des strikes
            
        Returns:
            Liste des prix de breakeven
        """
        breakevens = []
        
        # Créer une plage de prix plus dense
        min_strike = min(strikes)
        max_strike = max(strikes)
        step = 0.1
        
        # Tester les prix de min_strike-10 à max_strike+10
        prices = []
        current = min_strike - 10
        while current <= max_strike + 10:
            prices.append(current)
            current += step
        
        # Calculer P&L pour chaque prix
        pnl_values = [(p, self._calculate_pnl_at_price(options, p)) for p in prices]
        
        # Trouver les points où P&L change de signe
        for i in range(len(pnl_values) - 1):
            price1, pnl1 = pnl_values[i]
            price2, pnl2 = pnl_values[i + 1]
            
            # Si changement de signe, il y a un breakeven entre price1 et price2
            if pnl1 * pnl2 < 0:
                # Interpolation linéaire pour trouver le breakeven exact
                breakeven = price1 - pnl1 * (price2 - price1) / (pnl2 - pnl1)
                breakevens.append(round(breakeven, 2))
        
        return sorted(breakevens)
