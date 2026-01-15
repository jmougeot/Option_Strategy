"""
Générateur V2 de Stratégies d'Options
======================================
Version simplifiée qui prend une liste d'objets Option et génère toutes les
combinaisons possibles (1 à 4 options) pour créer des StrategyComparison.

Utilise itertools.combinations pour générer efficacement toutes les combinaisons.

OPTIMISATION: Supporte le mode BATCH C++ pour un traitement ultra-rapide.
"""

from itertools import product
from typing import List
from itertools import combinations_with_replacement
import numpy as np
from myproject.option.option_class import Option
from myproject.strategy.comparison_class import StrategyComparison
from myproject.strategy.calcul_linear_metrics_cpp import create_strategy_fast_with_signs
from myproject.strategy.calcul_cached import OptionsDataCache, CPP_AVAILABLE
from myproject.option.option_filter import sort_options_by_expiration
from myproject.app.filter_widget import FilterData


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
        
        # Déterminer le mode d'exécution
        if CPP_AVAILABLE:
            # Pré-extraire toutes les données des options (optimisation majeure)
            self.mode = "cached"
            self.cache = OptionsDataCache(self.options)
            # Créer un mapping option -> index pour recherche rapide
            self.option_to_index = {id(opt): i for i, opt in enumerate(self.options)}
            print(f"🚀 Mode C++ avec cache ({len(self.options)} options)")
        else:
            self.mode = "python"
            self.cache = None
            self.option_to_index = None
            print("⚠️ Mode Python pur (C++ non disponible)")

    def generate_all_combinations(
        self, price_min: float, price_max: float, filter: FilterData, max_legs: int = 4, 
    ) -> List[StrategyComparison]:
        """
        Génère toutes les combinaisons possibles d'options (1 à max_legs).
        """
        import time
        start_time = time.perf_counter()
        
        self.price_min = price_min
        self.price_max = price_max
        
        all_strategies = []
        
        # Compteurs pour statistiques
        total_combos_tested = 0
        total_combos_filtered = 0
        total_sign_variants = 0

        for n_legs in range(1, max_legs + 1):
            print(f"🔄 Génération des stratégies à {n_legs} leg(s)...")
            combos_this_level = 0
            filtered_this_level = 0

            # Générer toutes les combinaisons de n_legs options
            for combo in combinations_with_replacement(self.options, n_legs):
                combos_this_level += 1
                total_sign_variants += 2 ** n_legs  # Nombre de variantes de signes
                # Pour chaque combinaison, tester différentes configurations de positions
                strategies = self._generate_position_variants(list(combo), filter)
                if not strategies:
                    filtered_this_level += 1
                all_strategies.extend(strategies)
            
            total_combos_tested += combos_this_level
            total_combos_filtered += filtered_this_level

        elapsed = time.perf_counter() - start_time
        mode = " C++" if (self.cache is not None and self.cache.valid) else "Python"
        
        print(f"\n📊 Résumé ({mode}):")
        print(f"  • Total combos testées: {total_combos_tested:,}")
        print(f"  • Total variantes signes: {total_sign_variants:,}")
        print(f"  • Total combos filtrées: {total_combos_filtered:,} ({total_combos_filtered/total_combos_tested*100:.1f}%)")
        print(f"  • Stratégies générées: {len(all_strategies):,}")
        print(f"  • Temps total: {elapsed:.2f}s")
        print(f"  • Vitesse: {total_sign_variants/elapsed:,.0f} évaluations/sec")
        return all_strategies

    def _generate_position_variants(
        self,
        options: List[Option],
        filter,
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

        # OPTIMISATION MAJEURE: Utiliser le cache de signes pré-calculés
        sign_arrays = self.SIGN_ARRAYS_CACHE.get(n)
        if sign_arrays is None:
            print("pblm with sign array")
            sign_arrays = [np.array(combo, dtype=np.float64) for combo in product([-1.0, 1.0], repeat=n)]
        
        strategies: List[StrategyComparison] = []

        # ===== Génération des stratégies (optimisé) =====
        for signs in sign_arrays:
            strat = create_strategy_fast_with_signs(options, signs, filter)
            if strat is not None:  # Vérification explicite plus rapide que if strat
                strategies.append(strat)
        
        return strategies