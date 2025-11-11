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
from myproject.option.option_filter import sort_options_by_expiration


class OptionStrategyGeneratorV2:
    """
    Génère toutes les stratégies possibles à partir d'une liste d'options.
    Teste toutes les combinaisons de 1 à 4 options avec différentes positions (long/short).
    """

    SIGN_ARRAYS_CACHE = {
        1: [np.array([s], dtype=np.float64) for s in [-1.0, 1.0]],
        2: [np.array(combo, dtype=np.float64) for combo in product([-1.0, 1.0], repeat=2)],
        3: [np.array(combo, dtype=np.float64) for combo in product([-1.0, 1.0], repeat=3)],
        4: [np.array(combo, dtype=np.float64) for combo in product([-1.0, 1.0], repeat=4)],
        5: [np.array(combo, dtype=np.float64) for combo in product([-1.0, 1.0], repeat=5)],
        6: [np.array(combo, dtype=np.float64) for combo in product([-1.0, 1.0], repeat=6)],
    }

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

    def generate_all_combinations(
        self, target_price: float, price_min: float, price_max: float, max_legs: int = 4
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
                strategies = self._generate_position_variants(
                    list(combo),
                    target_price,
                )
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
        target_price: float,
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
            if (
                first.expiration_year != last.expiration_year
                or first.expiration_month != last.expiration_month
                or first.expiration_week != last.expiration_week
                or first.expiration_day != last.expiration_day
            ):
                return []

            deltas = np.array([opt.delta for opt in options])
            pos_deltas = np.sum(deltas[deltas > 0])
            neg_deltas = np.sum(np.abs(deltas[deltas < 0]))
            min_possible_delta = abs(pos_deltas - neg_deltas)
            if min_possible_delta > 0.7:
                return []

        # OPTIMISATION MAJEURE: Utiliser le cache de signes pré-calculés
        sign_arrays = self.SIGN_ARRAYS_CACHE.get(n)
        if sign_arrays is None:
            # Fallback pour n > 4 (ne devrait jamais arriver avec max_legs=4)
            sign_arrays = [np.array(combo, dtype=np.float64) for combo in product([-1.0, 1.0], repeat=n)]
        
        strategies: List[StrategyComparison] = []

        # ===== Génération des stratégies (optimisé) =====
        for signs in sign_arrays:
            strat = create_strategy_fast_with_signs(options, signs, target_price)
            if strat is not None:  # Vérification explicite plus rapide que if strat
                strategies.append(strat)
        
        return strategies
