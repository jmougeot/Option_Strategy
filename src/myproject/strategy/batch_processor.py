"""
Batch Processor pour le traitement C++ des combinaisons
========================================================
Déplace toute la boucle de génération en C++ pour éliminer l'overhead Python.
"""

import numpy as np
from typing import List, Optional
from itertools import product, combinations_with_replacement

from myproject.option.option_class import Option
from myproject.strategy.comparison_class import StrategyComparison
from myproject.app.filter_widget import FilterData

# Import du module C++
try:
    import strategy_metrics_cpp
    BATCH_CPP_AVAILABLE = True
except ImportError:
    BATCH_CPP_AVAILABLE = False
    print("⚠️ Module C++ non disponible pour le batch processing")


def prepare_batch_data(options: List[Option], max_legs: int = 4):
    """
    Prépare toutes les données pour le traitement batch en C++.
    
    Args:
        options: Liste des options
        max_legs: Nombre maximum de legs par stratégie
        
    Returns:
        Tuple (indices_batch, signs_batch, combo_sizes, n_options)
    """
    n_options = len(options)
    
    # Créer un mapping option -> index
    option_to_idx = {id(opt): i for i, opt in enumerate(options)}
    
    # Pré-calculer toutes les combinaisons avec leurs variantes de signes
    all_combos = []
    all_signs = []
    all_sizes = []
    
    for n_legs in range(1, max_legs + 1):
        sign_variants = list(product([-1, 1], repeat=n_legs))
        
        for combo in combinations_with_replacement(options, n_legs):
            # Vérifier que toutes les options ont la même expiration
            if n_legs > 1:
                first, last = combo[0], combo[-1]
                if (
                    first.expiration_year != last.expiration_year
                    or first.expiration_month != last.expiration_month
                    or first.expiration_week != last.expiration_week
                    or first.expiration_day != last.expiration_day
                ):
                    continue
            
            # Pour chaque combo valide, ajouter toutes les variantes de signes
            indices = [option_to_idx[id(opt)] for opt in combo]
            
            for signs in sign_variants:
                all_combos.append(indices)
                all_signs.append(list(signs))
                all_sizes.append(n_legs)
    
    if not all_combos:
        return None, None, None, 0
    
    # Convertir en arrays numpy avec padding
    n_combos = len(all_combos)
    
    indices_batch = np.full((n_combos, max_legs), -1, dtype=np.int32)
    signs_batch = np.zeros((n_combos, max_legs), dtype=np.int32)
    combo_sizes = np.array(all_sizes, dtype=np.int32)
    
    for i, (combo, signs) in enumerate(zip(all_combos, all_signs)):
        for j, (idx, sign) in enumerate(zip(combo, signs)):
            indices_batch[i, j] = idx
            signs_batch[i, j] = sign
    
    return indices_batch, signs_batch, combo_sizes, len(options)


def init_cpp_cache(options: List[Option]) -> bool:
    """
    Initialise le cache C++ avec toutes les données des options.
    """
    if not BATCH_CPP_AVAILABLE:
        return False
    
    n = len(options)
    
    # Vérifier que les données sont valides
    if options[0].pnl_array is None or options[0].prices is None:
        return False
    
    # Extraire toutes les données
    premiums = np.array([opt.premium for opt in options], dtype=np.float64)
    deltas = np.array([opt.delta for opt in options], dtype=np.float64)
    gammas = np.array([opt.gamma for opt in options], dtype=np.float64)
    vegas = np.array([opt.vega for opt in options], dtype=np.float64)
    thetas = np.array([opt.theta for opt in options], dtype=np.float64)
    ivs = np.array([opt.implied_volatility for opt in options], dtype=np.float64)
    average_pnls = np.array([opt.average_pnl for opt in options], dtype=np.float64)
    sigma_pnls = np.array([opt.sigma_pnl for opt in options], dtype=np.float64)
    strikes = np.array([opt.strike for opt in options], dtype=np.float64)
    profit_surfaces = np.array([opt.profit_surface_ponderated for opt in options], dtype=np.float64)
    loss_surfaces = np.array([opt.loss_surface_ponderated for opt in options], dtype=np.float64)
    is_calls = np.array([opt.option_type.lower() == 'call' for opt in options], dtype=np.bool_)
    
    # Construire la matrice P&L
    pnl_length = len(options[0].pnl_array)
    pnl_matrix = np.zeros((n, pnl_length), dtype=np.float64)
    for i, opt in enumerate(options):
        if opt.pnl_array is not None:
            pnl_matrix[i] = opt.pnl_array
    
    prices = np.array(options[0].prices, dtype=np.float64)
    
    # Initialiser le cache C++
    strategy_metrics_cpp.init_options_cache(
        premiums, deltas, gammas, vegas, thetas, ivs,
        average_pnls, sigma_pnls, strikes, profit_surfaces, loss_surfaces,
        is_calls, pnl_matrix, prices) 
    return True


def process_batch_cpp(
    indices_batch: np.ndarray,
    signs_batch: np.ndarray,
    combo_sizes: np.ndarray,
    filter: FilterData
) -> List:
    """
    Traite un batch de combinaisons en C++.
    
    Returns:
        Liste de tuples (indices, signs, metrics_dict)
    """
    if not BATCH_CPP_AVAILABLE:
        return []
    
    max_loss = filter.max_loss
    max_premium = filter.max_premium
    ouvert_gauche = filter.ouvert_gauche
    ouvert_droite = filter.ouvert_droite
    min_premium_sell = filter.min_premium_sell
    
    return strategy_metrics_cpp.process_combinations_batch(
        indices_batch, signs_batch, combo_sizes,
        max_loss, max_premium, ouvert_gauche, ouvert_droite, min_premium_sell
    )


def batch_to_strategies(
    results: List,
    options: List[Option]
) -> List[StrategyComparison]:
    """
    Convertit les résultats du batch C++ en objets StrategyComparison.
    """
    from myproject.strategy.strategy_naming_v2 import generate_strategy_name
    from myproject.option.option_utils_v2 import get_expiration_info
    
    strategies = []
    
    if not options or options[0].prices is None:
        return strategies
    
    prices = options[0].prices
    
    for indices, signs, metrics in results:
        # Récupérer les options correspondantes
        opts = [options[i] for i in indices]
        signs_arr = np.array([float(s) for s in signs], dtype=np.float64)
        
        # Générer le nom et l'expiration
        strategy_name = generate_strategy_name(opts, signs_arr)
        exp_info = get_expiration_info(opts)
        
        # Créer la StrategyComparison
        strat = StrategyComparison(
            strategy_name=strategy_name,
            strategy=None,
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
    
    return strategies


def generate_all_strategies_batch(
    options: List[Option],
    filter: FilterData,
    max_legs: int = 4
) -> List[StrategyComparison]:
    """
    Génère toutes les stratégies en mode batch C++.
    
    C'est la fonction principale qui remplace la boucle Python complète.
    """
    import time
    start = time.perf_counter()
    
    if not BATCH_CPP_AVAILABLE:
        print("❌ Batch C++ non disponible")
        return []
    
    # Étape 1: Préparer les données batch
    print(f"🔄 Préparation du batch pour {len(options)} options...")
    indices_batch, signs_batch, combo_sizes, n_opts = prepare_batch_data(options, max_legs)
    
    if indices_batch is None or signs_batch is None or combo_sizes is None:
        return []
    
    n_combos = len(combo_sizes)
    prep_time = time.perf_counter() - start
    print(f"  • {n_combos:,} combinaisons×signes à tester")
    
    # Étape 2: Initialiser le cache C++
    cache_start = time.perf_counter()
    if not init_cpp_cache(options):
        print("❌ Échec d'initialisation du cache C++")
        return []
    cache_time = time.perf_counter() - cache_start
    print(f"  • Init cache C++: {cache_time:.3f}s")
    
    # Étape 3: Traiter en batch C++
    cpp_start = time.perf_counter()
    results = process_batch_cpp(
        indices_batch, signs_batch, combo_sizes, filter
    )
    cpp_time = time.perf_counter() - cpp_start
    
    n_valid = len(results)
    print(f"  • Traitement C++: {cpp_time:.2f}s ({n_combos/cpp_time:,.0f} évals/sec)")
    print(f"  • Stratégies valides: {n_valid:,} ({n_valid/n_combos*100:.1f}%)")
    
    # Étape 4: Convertir en StrategyComparison
    conv_start = time.perf_counter()
    strategies = batch_to_strategies(results, options)
    conv_time = time.perf_counter() - conv_start
    print(f"  • Conversion Python: {conv_time:.2f}s")
    
    total_time = time.perf_counter() - start
    print(f"\n✅ Total: {total_time:.2f}s pour {n_combos:,} évaluations")
    print(f"   Vitesse globale: {n_combos/total_time:,.0f} évals/sec")
    
    return strategies
