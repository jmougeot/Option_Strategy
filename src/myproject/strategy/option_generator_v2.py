"""
Générateur V2 de Stratégies d'Options
======================================
Version simplifiée qui prend une liste d'objets Option et génère toutes les
combinaisons possibles (1 à 4 options) pour créer des StrategyComparison.

Utilise itertools.combinations pour générer efficacement toutes les combinaisons.
"""
from itertools import product
from typing import List, Tuple, Optional
from itertools import combinations_with_replacement
from myproject.option.option_class import Option
from myproject.strategy.comparison_class import StrategyComparison
from myproject.strategy.calcul_linear_metrics import create_strategy_fast
from myproject.option.option_filter import sort_options_by_expiration
from myproject.strategy.strategy_filter import filter_extreme_strategies


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
        
        for n_legs in range(1, max_legs + 1):
            print(f"🔄 Génération des stratégies à {n_legs} leg(s)...")
            
            # Générer toutes les combinaisons de n_legs options
            for combo in combinations_with_replacement(self.options, n_legs):
                # Pour chaque combinaison, tester différentes configurations de positions
                strategies = self._generate_position_variants(
                    list(combo), 
                    target_price, 
                    include_long, 
                    include_short
                )
                all_strategies.extend(strategies)
        
        print(f"{len(all_strategies)} stratégies générées au total")
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
        
        # Comme les options sont triées, si première == dernière, toutes sont identiques
        if n > 1:
            first, last = options[0], options[-1]
            # Vérifier année, mois, semaine ET jour
            if (first.expiration_year != last.expiration_year or 
                first.expiration_month != last.expiration_month or
                first.expiration_week != last.expiration_week or
                first.expiration_day != last.expiration_day):
                return [] 

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
        for signs in sign_space:
            positions: List[str] = ['long' if s == -1 else 'short' for s in signs]
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
                    # Obligatoires
                    option_type=opt.option_type,
                    strike=opt.strike,
                    premium=opt.premium,
                    
                    # Expiration
                    expiration_day=opt.expiration_day,
                    expiration_week=opt.expiration_week,
                    expiration_month=opt.expiration_month,
                    expiration_year=opt.expiration_year,
                    
                    # Position
                    quantity=opt.quantity,
                    position=position_type,
                    
                    # Identification
                    ticker=opt.ticker,
                    underlying_symbol=opt.underlying_symbol,
                    
                    # Prix
                    bid=opt.bid,
                    ask=opt.ask,
                    
                    # Greeks
                    delta=opt.delta,
                    gamma=opt.gamma,
                    vega=opt.vega,
                    theta=opt.theta,
                    
                    # Volatilité
                    implied_volatility=opt.implied_volatility,
                    
                    # Surfaces calculées (copiées depuis l'option originale)
                    loss_surface_ponderated=opt.loss_surface_ponderated,
                    profit_surface_ponderated=opt.profit_surface_ponderated,
                    
                    # Arrays et mixture (si disponibles)
                    prices=opt.prices,
                    mixture=opt.mixture,
                    pnl_array=opt.pnl_array,
                    pnl_ponderation=opt.pnl_ponderation,
                    
                    # Métriques calculées avec la mixture
                    average_pnl=opt.average_pnl,
                    sigma_pnl=opt.sigma_pnl,
                )
                
                # Copier l'attribut dynamique _dx si présent
                if hasattr(opt, '_dx'):
                    opt_copy._dx = opt._dx
                
                option_legs.append(opt_copy)
            
            # ========== VERSION ULTRA-OPTIMISÉE ==========
            # Calcul direct de TOUTES les métriques en une seule passe
            # Retourne un StrategyComparison complet (pas de dict intermédiaire)
            strategy = create_strategy_fast(option_legs, target_price)
            
            return strategy
            
        except Exception as e:
            print(f"⚠️ Erreur création stratégie: {e}")
            return None  


