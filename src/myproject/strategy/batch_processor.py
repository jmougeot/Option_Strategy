"""
Batch Processor pour le traitement C++ des combinaisons
========================================================
Déplace toute la boucle de génération en C++ pour éliminer l'overhead Python.
"""

import numpy as np
from typing import Dict, List, Optional
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


def prepare_batch_data_by_legs(options: List[Option], n_legs: int, max_legs: int = 4):
    """
    Prépare les données pour un nombre de legs spécifique.
    
    Args:
        options: Liste des options
        n_legs: Nombre de legs à préparer
        max_legs: Nombre maximum de legs (pour le padding)
        
    Returns:
        Tuple (indices_batch, signs_batch, combo_sizes, n_combos)
    """
    n_options: int = len(options)
    option_to_idx = {id(opt): i for i, opt in enumerate(options)}
    
    all_combos = []
    all_signs = []
    all_sizes = []
    
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
        
        indices = [option_to_idx[id(opt)] for opt in combo]
        
        for signs in sign_variants:
            all_combos.append(indices)
            all_signs.append(list(signs))
            all_sizes.append(n_legs)
    
    if not all_combos:
        return None, None, None, 0
    
    n_combos = len(all_combos)
    
    indices_batch = np.full((n_combos, max_legs), -1, dtype=np.int32)
    signs_batch = np.zeros((n_combos, max_legs), dtype=np.int32)
    combo_sizes = np.array(all_sizes, dtype=np.int32)
    
    for i, (combo, signs) in enumerate(zip(all_combos, all_signs)):
        for j, (idx, sign) in enumerate(zip(combo, signs)):
            indices_batch[i, j] = idx
            signs_batch[i, j] = sign
    
    return indices_batch, signs_batch, combo_sizes, n_combos


def prepare_batch_data(options: List[Option], max_legs: int = 4):
    """
    Prépare toutes les données pour le traitement batch en C++.
    
    Args:
        options: Liste des options
        max_legs: Nombre maximum de legs par stratégie
        
    Returns:
        Tuple (indices_batch, signs_batch, combo_sizes, n_options)
    """
    n_options: int = len(options)
    
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
    is_calls = np.array([opt.option_type.lower() == 'call' for opt in options], dtype=np.bool_)
    
    # Nouvelles données: rolls
    rolls = np.array([opt.roll if opt.roll is not None else 0.0 for opt in options], dtype=np.float64)
    rolls_quarterly = np.array([opt.roll_quarterly if opt.roll_quarterly is not None else 0.0 for opt in options], dtype=np.float64)
    rolls_sum = np.array([opt.roll_sum if opt.roll_sum is not None else 0.0 for opt in options], dtype=np.float64)
    
    # Construire la matrice P&L
    pnl_length = len(options[0].pnl_array)
    pnl_matrix = np.zeros((n, pnl_length), dtype=np.float64)
    for i, opt in enumerate(options):
        if opt.pnl_array is not None:
            pnl_matrix[i] = opt.pnl_array
    
    prices = np.array(options[0].prices, dtype=np.float64)
    
    # Récupérer la mixture (identique pour toutes les options)
    if options[0].mixture is None:
        print("⚠️ Mixture non disponible pour init_cpp_cache")
        return False
    mixture = np.asarray(options[0].mixture, dtype=np.float64)
    
    # Récupérer average_mix (point de séparation left/right)
    average_mix = float(options[0].average_mix) if options[0].average_mix else 0.0
    
    # Initialiser le cache C++
    strategy_metrics_cpp.init_options_cache(
        premiums, deltas, gammas, vegas, thetas, ivs,
        average_pnls, sigma_pnls, strikes,
        is_calls, rolls, rolls_quarterly, rolls_sum,
        pnl_matrix, prices, mixture, average_mix) 
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
    
    # Nouveaux paramètres de filtrage
    max_loss_left = filter.max_loss_left
    max_loss_right = filter.max_loss_right
    max_premium = filter.max_premium
    ouvert_gauche = filter.ouvert_gauche
    ouvert_droite = filter.ouvert_droite
    min_premium_sell = filter.min_premium_sell
    delta_min = filter.delta_min
    delta_max = filter.delta_max
    
    return strategy_metrics_cpp.process_combinations_batch(
        indices_batch, signs_batch, combo_sizes,
        max_loss_left, max_loss_right, max_premium, 
        ouvert_gauche, ouvert_droite, min_premium_sell,
        delta_min, delta_max
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
        
        # Calculer rolls_detail en Python (agrégation des rolls par expiry)
        total_rolls_detail: Dict[str, float] = {}
        for i, opt in enumerate(opts):
            if opt.rolls_detail:
                for label, value in opt.rolls_detail.items():
                    if label not in total_rolls_detail:
                        total_rolls_detail[label] = 0.0
                    total_rolls_detail[label] += float(signs_arr[i]) * value
        
        # Créer la StrategyComparison
        strat = StrategyComparison(
            strategy_name=strategy_name,
            strategy=None,
            premium=metrics['total_premium'],
            all_options=opts,
            signs=signs_arr,
            call_count=metrics.get('call_count', 0),
            put_count=metrics.get('put_count', 0),
            expiration_day=exp_info.get("expiration_day"),
            expiration_week=exp_info.get("expiration_week"),
            expiration_month=exp_info.get("expiration_month", "F"),
            expiration_year=exp_info.get("expiration_year", 6),
            max_profit=metrics['max_profit'],
            max_loss=metrics['max_loss'],
            breakeven_points=metrics.get('breakeven_points', []),
            profit_range=(metrics.get('min_profit_price', 0), metrics.get('max_profit_price', 0)),
            profit_zone_width=metrics.get('profit_zone_width', 0),
            average_pnl=metrics['total_average_pnl'],
            sigma_pnl=metrics.get('total_sigma_pnl', 0),
            pnl_array=np.array(metrics.get('pnl_array', []), dtype=np.float64),
            prices=prices,
            total_delta=metrics['total_delta'],
            total_gamma=metrics['total_gamma'],
            total_vega=metrics['total_vega'],
            total_theta=metrics['total_theta'],
            avg_implied_volatility=metrics.get('total_iv', 0),
            profit_at_target=0,
            score=0.0,
            rank=0,
            roll=metrics.get('total_roll', 0),
            roll_quarterly=metrics.get('total_roll_quarterly', 0),
            roll_sum=metrics.get('total_roll_sum', 0),
            rolls_detail=total_rolls_detail,
        )
        strategies.append(strat)
    
    return strategies


def generate_all_strategies_batch(
    options: List[Option],
    filter: FilterData,
    max_legs: int = 4,
    progress_tracker=None
) -> List[StrategyComparison]:
    """
    Génère toutes les stratégies en mode batch C++.
    
    Fait un appel C++ par nombre de legs pour permettre la mise à jour de la progression.
    
    Args:
        options: Liste des options
        filter: Filtres à appliquer
        max_legs: Nombre maximum de legs
        progress_tracker: Tracker de progression optionnel (ProgressTracker)
    """
    import time
    from myproject.app.progress_tracker import ProcessingStep, get_step_for_leg
    
    start = time.perf_counter()
    
    print(f"\n{'='*60}")
    print(f"🚀 MODE BATCH C++ ACTIVÉ")
    print(f"   Un appel C++ par nombre de legs (avec progression)")
    print(f"{'='*60}\n")
    
    if not BATCH_CPP_AVAILABLE:
        print("❌ Batch C++ non disponible")
        return []
    
    # Initialiser le cache C++ (une seule fois)
    print(f"🔄 Initialisation du cache C++ pour {len(options)} options...")
    cache_start = time.perf_counter()
    if not init_cpp_cache(options):
        print("❌ Échec d'initialisation du cache C++")
        return []
    cache_time = time.perf_counter() - cache_start
    print(f"  • Init cache C++: {cache_time:.3f}s")
    
    # Pré-calculer le nombre total de combinaisons (très rapide, juste de la combinatoire)
    from math import comb
    n_options = len(options)
    combos_per_leg = {}
    grand_total = 0
    for n_legs in range(1, max_legs + 1):
        # C(n+r-1, r) * 2^r (combinaisons avec répétition * variantes de signes)
        n_combos_raw = comb(n_options + n_legs - 1, n_legs) * (2 ** n_legs)
        combos_per_leg[n_legs] = n_combos_raw
        grand_total += n_combos_raw
    
    print(f"  • Total à analyser: {grand_total:,} combinaisons")
    
    all_strategies: List[StrategyComparison] = []
    total_combos_done = 0
    total_valid = 0
    
    # Traiter chaque nombre de legs séparément
    for n_legs in range(1, max_legs + 1):
        leg_start = time.perf_counter()
        
        # Mettre à jour la progression avec compteur
        if progress_tracker:
            step = get_step_for_leg(n_legs)
            pct = total_combos_done / grand_total * 100 if grand_total > 0 else 0
            progress_tracker.update(
                step, 
                f"[{total_combos_done:,} / {grand_total:,}] Traitement {n_legs} leg(s)... ({pct:.0f}%)"
            )
        
        # Préparer les données pour ce nombre de legs
        indices_batch, signs_batch, combo_sizes, n_combos = prepare_batch_data_by_legs(
            options, n_legs, max_legs
        )
        
        if indices_batch is None or n_combos == 0:
            print(f"  • {n_legs} leg(s): 0 combinaisons (filtrées par expiration)")
            total_combos_done += combos_per_leg.get(n_legs, 0)
            continue
        
        # Traiter en batch C++
        results = process_batch_cpp(indices_batch, signs_batch, combo_sizes, filter)
        n_valid = len(results)
        total_valid += n_valid
        total_combos_done += n_combos
        
        # Convertir en StrategyComparison
        strategies = batch_to_strategies(results, options)
        all_strategies.extend(strategies)
        
        leg_time = time.perf_counter() - leg_start
        pct_done = total_combos_done / grand_total * 100 if grand_total > 0 else 0
        print(f"  • {n_legs} leg(s): {n_combos:,} → {n_valid:,} valides | Cumul: {total_combos_done:,}/{grand_total:,} ({pct_done:.0f}%)")
        
        # Mettre à jour les stats dans le progress tracker
        if progress_tracker:
            progress_tracker.update_substep(
                1.0,
                f"[{total_combos_done:,} / {grand_total:,}] {total_valid:,} stratégies valides"
            )
    
    total_time = time.perf_counter() - start
    
    print(f"\n{'='*60}")
    print(f"✅ BATCH C++ TERMINÉ")
    print(f"   Total: {total_combos_done:,} combinaisons testées")
    print(f"   Valides: {total_valid:,} stratégies ({total_valid/total_combos_done*100:.1f}%)" if total_combos_done > 0 else "   Valides: 0")
    print(f"   Temps: {total_time:.2f}s ({total_combos_done/total_time:,.0f} évals/sec)" if total_time > 0 else "")
    print(f"{'='*60}\n")
    
    return all_strategies
