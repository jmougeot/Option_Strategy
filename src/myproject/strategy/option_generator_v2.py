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
from myproject.strategy.calcul_cached import OptionsDataCache, create_strategy_from_cache, CPP_AVAILABLE
from myproject.option.option_filter import sort_options_by_expiration
from myproject.app.filter_widget import FilterData

# Import direct du module C++ pour le batch
try:
    import strategy_metrics_cpp
    BATCH_CPP_AVAILABLE = True
except ImportError:
    BATCH_CPP_AVAILABLE = False


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
        if BATCH_CPP_AVAILABLE:
            self.mode = "batch"
            self.cache = None
            self.option_to_index = None
            print(f"🚀🚀 Mode BATCH C++ ACTIVÉ ({len(self.options)} options)")
        elif CPP_AVAILABLE:
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
        
        # ===== MODE BATCH C++ (ULTRA RAPIDE) =====
        if self.mode == "batch" and BATCH_CPP_AVAILABLE:
            strategies = self._generate_batch_cpp(max_loss, max_premium, ouvert, max_legs)
            return strategies
        
        # ===== MODES CLASSIQUES (Python loop) =====
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
        mode = "🚀 C++ avec cache" if (self.cache is not None and self.cache.valid) else "🐢 Python pur"
        
        print(f"\n📊 Résumé ({mode}):")
        print(f"  • Total combos testées: {total_combos_tested:,}")
        print(f"  • Total variantes signes: {total_sign_variants:,}")
        print(f"  • Total combos filtrées: {total_combos_filtered:,} ({total_combos_filtered/total_combos_tested*100:.1f}%)")
        print(f"  • Stratégies générées: {len(all_strategies):,}")
        print(f"  • Temps total: {elapsed:.2f}s")
        print(f"  • Vitesse: {total_sign_variants/elapsed:,.0f} évaluations/sec")
        return all_strategies

    def _generate_batch_cpp(
        self,
        max_loss: float,
        max_premium: float,
        ouvert: bool,
        max_legs: int = 4
    ) -> List[StrategyComparison]:
        """
        Génère toutes les stratégies en mode batch C++ ultra-rapide.
        Toute la boucle est exécutée en C++ pour éviter l'overhead Python.
        """
        import time
        start = time.perf_counter()
        
        n_opts = len(self.options)
        pnl_len = len(self.options[0].pnl_array)
        
        # ===== Étape 1: Extraire toutes les données des options =====
        print("📦 Extraction des données...")
        premiums = np.array([opt.premium for opt in self.options], dtype=np.float64)
        deltas = np.array([opt.delta for opt in self.options], dtype=np.float64)
        gammas = np.array([opt.gamma for opt in self.options], dtype=np.float64)
        vegas = np.array([opt.vega for opt in self.options], dtype=np.float64)
        thetas = np.array([opt.theta for opt in self.options], dtype=np.float64)
        ivs = np.array([opt.implied_volatility for opt in self.options], dtype=np.float64)
        avg_pnls = np.array([opt.average_pnl for opt in self.options], dtype=np.float64)
        sigma_pnls = np.array([opt.sigma_pnl for opt in self.options], dtype=np.float64)
        strikes = np.array([opt.strike for opt in self.options], dtype=np.float64)
        profit_surf = np.array([opt.profit_surface_ponderated for opt in self.options], dtype=np.float64)
        loss_surf = np.array([opt.loss_surface_ponderated for opt in self.options], dtype=np.float64)
        is_calls = np.array([opt.option_type == 'call' for opt in self.options], dtype=np.bool_)
        
        pnl_matrix = np.zeros((n_opts, pnl_len), dtype=np.float64)
        for i, opt in enumerate(self.options):
            pnl_matrix[i] = opt.pnl_array
        prices = np.array(self.options[0].prices, dtype=np.float64)
        
        # Extraire les expirations pour le filtrage
        expirations = [(opt.expiration_year, opt.expiration_month, opt.expiration_week, opt.expiration_day) 
                       for opt in self.options]
        
        extract_time = time.perf_counter() - start
        print(f"  ✓ Extraction: {extract_time:.2f}s")
        
        # ===== Étape 2: Initialiser le cache C++ =====
        cache_start = time.perf_counter()
        strategy_metrics_cpp.init_options_cache(
            premiums, deltas, gammas, vegas, thetas, ivs,
            avg_pnls, sigma_pnls, strikes, profit_surf, loss_surf,
            is_calls, pnl_matrix, prices
        )
        cache_time = time.perf_counter() - cache_start
        print(f"  ✓ Init cache C++: {cache_time:.3f}s")
        
        # ===== Étape 3: Générer les combinaisons (en Python, c'est rapide) =====
        combo_start = time.perf_counter()
        all_indices = []
        all_signs = []
        all_sizes = []
        
        for n_legs in range(1, max_legs + 1):
            sign_variants = list(product([-1, 1], repeat=n_legs))
            for combo in combinations_with_replacement(range(n_opts), n_legs):
                # Vérifier même expiration
                if n_legs > 1:
                    exp_first = expirations[combo[0]]
                    exp_last = expirations[combo[-1]]
                    if exp_first != exp_last:
                        continue
                
                for signs in sign_variants:
                    all_indices.append(list(combo) + [-1] * (max_legs - n_legs))
                    all_signs.append(list(signs) + [0] * (max_legs - n_legs))
                    all_sizes.append(n_legs)
        
        n_combos = len(all_sizes)
        combo_time = time.perf_counter() - combo_start
        print(f"  ✓ Génération combos: {combo_time:.2f}s ({n_combos:,} combinaisons)")
        
        if n_combos == 0:
            return []
        
        # Convertir en arrays numpy
        indices_batch = np.array(all_indices, dtype=np.int32)
        signs_batch = np.array(all_signs, dtype=np.int32)
        combo_sizes = np.array(all_sizes, dtype=np.int32)
        
        # ===== Étape 4: Traitement batch C++ =====
        cpp_start = time.perf_counter()
        results = strategy_metrics_cpp.process_combinations_batch(
            indices_batch, signs_batch, combo_sizes,
            max_loss, max_premium, ouvert
        )
        cpp_time = time.perf_counter() - cpp_start
        
        n_valid = len(results)
        print(f"  ✓ Traitement C++: {cpp_time:.2f}s ({n_combos/cpp_time:,.0f} évals/sec)")
        print(f"  ✓ Stratégies valides: {n_valid:,} ({n_valid/n_combos*100:.2f}%)")
        
        # ===== Étape 5: Conversion en StrategyComparison =====
        conv_start = time.perf_counter()
        strategies = []
        
        from myproject.strategy.strategy_naming_v2 import generate_strategy_name
        from myproject.option.option_utils_v2 import get_expiration_info
        
        for indices, signs, metrics in results:
            opts = [self.options[i] for i in indices]
            signs_arr = np.array([float(s) for s in signs], dtype=np.float64)
            
            strategy_name = generate_strategy_name(opts, signs_arr)
            exp_info = get_expiration_info(opts)
            
            strat = StrategyComparison(
                strategy_name=strategy_name,
                strategy=None,
                target_price=98,
                premium=metrics['total_premium'],
                all_options=opts,
                signs=signs_arr,
                call_count=metrics['call_count'],
                put_count=metrics['put_count'],
                expiration_day=exp_info.get("expiration_day"),
                expiration_week=exp_info.get("expiration_week"),
                expiration_month=exp_info.get("expiration_month", "F"),
                expiration_year=exp_info.get("expiration_year", 6),
                max_profit=metrics['max_profit'],
                max_loss=metrics['max_loss'],
                breakeven_points=metrics['breakeven_points'],
                profit_range=(metrics['min_profit_price'], metrics['max_profit_price']),
                profit_zone_width=metrics['profit_zone_width'],
                surface_profit=metrics['surface_profit'],
                surface_loss=metrics['surface_loss'],
                surface_profit_ponderated=metrics['surface_profit_ponderated'],
                surface_loss_ponderated=metrics['surface_loss_ponderated'],
                average_pnl=metrics['total_average_pnl'],
                sigma_pnl=metrics['total_sigma_pnl'],
                pnl_array=metrics['pnl_array'],
                prices=prices,
                risk_reward_ratio=0,
                risk_reward_ratio_ponderated=0,
                total_delta=metrics['total_delta'],
                total_gamma=metrics['total_gamma'],
                total_vega=metrics['total_vega'],
                total_theta=metrics['total_theta'],
                avg_implied_volatility=metrics['total_iv'],
                profit_at_target=0,
                profit_at_target_pct=0,
                score=0.0,
                rank=0,
            )
            strategies.append(strat)
        
        conv_time = time.perf_counter() - conv_start
        total_time = time.perf_counter() - start
        
        print(f"\n📊 Résumé (🚀🚀 BATCH C++):")
        print(f"  • Total évaluations: {n_combos:,}")
        print(f"  • Stratégies générées: {len(strategies):,}")
        print(f"  • Temps total: {total_time:.2f}s")
        print(f"  • Vitesse globale: {n_combos/total_time:,.0f} évals/sec")
        
        return strategies

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
        # ===== Génération des stratégies (optimisé avec cache) =====
        if self.cache is not None and self.cache.valid:
            # Mode ultra-optimisé: utiliser le cache pré-extrait
            indices = [self.option_to_index[id(opt)] for opt in options]
            for signs in sign_arrays:
                strat = create_strategy_from_cache(self.cache, indices, signs, max_loss, max_premium, ouvert)
                if strat is not None:
                    strategies.append(strat)
        else:
            # Fallback: mode classique
            for signs in sign_arrays:
                strat = create_strategy_fast_with_signs(options, signs, max_loss, max_premium, ouvert)
                if strat is not None:
                    strategies.append(strat)
        
        return strategies
