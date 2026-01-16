"""
Générateur V2 de Stratégies d'Options
======================================
Version simplifiée qui prend une liste d'objets Option et génère toutes les
combinaisons possibles (1 à 4 options) pour créer des StrategyComparison.

Utilise itertools.combinations pour générer efficacement toutes les combinaisons.
"""

from itertools import product
from typing import List
from itertools import combinations_with_replacement
import numpy as np
from myproject.option.option_class import Option
from myproject.strategy.comparison_class import StrategyComparison
from myproject.strategy.calcul_linear_metrics import create_strategy_fast_with_signs
from myproject.option.option_filter import sort_options_by_expiration, sort_options_by_strike
from myproject.app.filter_widget import FilterData, StrategyType, STRATEGYTYPE


class OptionStrategyGeneratorV2:
    """
    Génère toutes les stratégies possibles à partir d'une liste d'options.
    Teste toutes les combinaisons de 1 à 4 options avec différentes positions (long/short).
    """

    # Cache pré-calculé des arrays de signes (np.array)
    SIGN_ARRAYS_CACHE = {
        1: [np.array([s], dtype=np.float64) for s in [-1.0, 1.0]],
        2: [np.array(combo, dtype=np.float64) for combo in product([-1.0, 1.0], repeat=2)],
        3: [np.array(combo, dtype=np.float64) for combo in product([-1.0, 1.0], repeat=3)],
        4: [np.array(combo, dtype=np.float64) for combo in product([-1.0, 1.0], repeat=4)],
        5: [np.array(combo, dtype=np.float64) for combo in product([-1.0, 1.0], repeat=5)],
        6: [np.array(combo, dtype=np.float64) for combo in product([-1.0, 1.0], repeat=6)],
    }
    
    # Cache des tuples de signes pour lookup rapide (tuple hashable)
    SIGN_TUPLES_CACHE = {
        1: [tuple(s for s in [-1.0, 1.0])],
        2: [combo for combo in product((-1.0, 1.0), repeat=2)],
        3: [combo for combo in product((-1.0, 1.0), repeat=3)],
        4: [combo for combo in product((-1.0, 1.0), repeat=4)],
        5: [combo for combo in product((-1.0, 1.0), repeat=5)],
        6: [combo for combo in product((-1.0, 1.0), repeat=6)],
    }

    def __init__(self, options: List[Option]):
        """
        Initialise le générateur avec une liste d'options triées par expiration puis par strike.

        Args:
            options: Liste d'objets Option récupérés depuis Bloomberg
        """
        # Trier les options par expiration puis par strike croissant
        sorted_by_exp = sort_options_by_expiration(options)
        self.options = sort_options_by_strike(sorted_by_exp)
        self.price_min = None
        self.price_max = None
        
        # Cache pour les patterns de signes valides (pré-calculé une fois)
        self._valid_sign_patterns_cache = {}

    def _get_valid_sign_patterns(
        self, 
        n_legs: int, 
        all_calls: bool, 
        all_puts: bool, 
        strategies_include: StrategyType
    ) -> set:
        """
        Retourne un set de tuples de signes valides pour le filtrage.
        Utilise un cache pour éviter les recalculs.
        """
        # Clé de cache: (n_legs, all_calls, all_puts, tuple des stratégies sélectionnées)
        strat_key = (
            strategies_include.put_condor,
            strategies_include.call_condor,
            strategies_include.put_ladder,
            strategies_include.call_ladder,
            strategies_include.put_fly,
            strategies_include.call_fly,
        )
        cache_key = (n_legs, all_calls, all_puts, strat_key)
        
        if cache_key in self._valid_sign_patterns_cache:
            return self._valid_sign_patterns_cache[cache_key]
        
        valid_patterns = set()
        
        for strat_name, strat_config in STRATEGYTYPE.items():
            # Vérifier si ce type est sélectionné
            if not getattr(strategies_include, strat_name, False):
                continue
            
            expected_type = strat_config["option_type"]
            expected_signs = strat_config["signs"]
            
            # Vérifier le nombre de legs
            if len(expected_signs) != n_legs:
                continue
            
            # Vérifier le type d'options
            if expected_type == "call" and not all_calls:
                continue
            if expected_type == "put" and not all_puts:
                continue
            
            # Ajouter le pattern (converti en tuple de floats)
            valid_patterns.add(tuple(float(s) for s in expected_signs))
        
        self._valid_sign_patterns_cache[cache_key] = valid_patterns
        return valid_patterns

    def generate_all_combinations(
        self, price_min: float, price_max: float, filter: FilterData, max_legs: int = 4, 
    ) -> List[StrategyComparison]:
        """
        Génère toutes les combinaisons possibles d'options (1 à max_legs).
        """
        self.price_min = price_min
        self.price_max = price_max
        all_strategies = []
        
        # Compteurs pour statistiques
        total_combos_tested = 0
        total_combos_filtered = 0

        for n_legs in range(1, max_legs + 1):
            print(f"🔄 Génération des stratégies à {n_legs} leg(s)...")
            combos_this_level = 0
            filtered_this_level = 0

            # Générer toutes les combinaisons de n_legs options
            for combo in combinations_with_replacement(self.options, n_legs):
                combos_this_level += 1
                # Pour chaque combinaison, tester différentes configurations de positions
                strategies = self._generate_position_variants(list(combo), filter)
                if not strategies:
                    filtered_this_level += 1
                all_strategies.extend(strategies)
            
            total_combos_tested += combos_this_level
            total_combos_filtered += filtered_this_level

        print(f"\n📊 Résumé:")
        print(f"  • Total combos testées: {total_combos_tested:,}")
        print(f"  • Total combos filtrées: {total_combos_filtered:,} ({total_combos_filtered/total_combos_tested*100:.1f}%)")
        print(f"  • Stratégies générées: {len(all_strategies):,}")
        return all_strategies

    def _generate_position_variants(
        self,
        options: List[Option],
        filter,
    ) -> List[StrategyComparison]:
        """
        Génère les variantes de positions pour une combinaison d'options.
        Teste long/short selon include_long/include_short.
        Filtre par type de stratégie si filter_type est activé.

        Note: Les options sont déjà triées par strike dans __init__.
        On vérifie simplement que la première et la dernière ont la même date d'expiration.
        """
        n = len(options)
        if n == 0:
            return []

        # Comme les options sont triées, si première == dernière, toutes sont identiques
        if n > 1:
            first, last = options[0], options[-1]
            # Vérifier année, mois, semaine ET jour
            if (
                first.expiration_year != last.expiration_year
                or first.expiration_month != last.expiration_month
                or first.expiration_week != last.expiration_week
                or first.expiration_day != last.expiration_day
            ):
                return []

        # OPTIMISATION: Pré-calculer le type d'options une seule fois
        use_strategy_filter = filter.filter_type and filter.strategies_include is not None
        valid_patterns = None
        
        if use_strategy_filter:
            # Calculer le type d'options UNE SEULE FOIS pour cette combinaison
            option_types = [opt.option_type.lower() for opt in options]
            all_calls = all(t == "call" for t in option_types)
            all_puts = all(t == "put" for t in option_types)
            
            # Si mix call/put, aucune stratégie standard ne correspond
            if not all_calls and not all_puts:
                return []
            
            # Obtenir les patterns valides (avec cache)
            valid_patterns = self._get_valid_sign_patterns(
                n, all_calls, all_puts, filter.strategies_include
            )
            
            # Si aucun pattern valide, retourner vide
            if not valid_patterns:
                return []

        # OPTIMISATION: Utiliser le cache de signes pré-calculés
        sign_arrays = self.SIGN_ARRAYS_CACHE.get(n)
        sign_tuples = self.SIGN_TUPLES_CACHE.get(n)
        
        if sign_arrays is None:
            sign_arrays = [np.array(combo, dtype=np.float64) for combo in product([-1.0, 1.0], repeat=n)]
            sign_tuples = [combo for combo in product((-1.0, 1.0), repeat=n)]
        
        strategies: List[StrategyComparison] = []

        # ===== Génération des stratégies (optimisé) =====
        for i, signs in enumerate(sign_arrays):
            # Filtrage RAPIDE par type de stratégie (lookup O(1) dans un set)
            if use_strategy_filter:
                if sign_tuples[i] not in valid_patterns:
                    continue
            
            strat = create_strategy_fast_with_signs(options, signs, filter)
            if strat is not None:
                strategies.append(strat)
        
        return strategies
