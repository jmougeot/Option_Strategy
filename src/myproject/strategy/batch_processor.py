"""
Batch Processor C++ pour le traitement des combinaisons d'options
==================================================================

Ce module dÃ©lÃ¨gue tous les calculs au module C++ strategy_metrics_cpp.

Architecture:
    1. init_cpp_cache(): Charge les donnÃ©es des options dans le cache C++
    2. prepare_batch_data_by_legs(): GÃ©nÃ¨re les indices des combinaisons
    3. process_batch_cpp(): Appelle le C++ pour traiter un batch
    4. batch_to_strategies(): Convertit les rÃ©sultats C++ en objets Python

Performance:
    - Le C++ traite toutes les combinaisons en une seule passe
    - Ã‰vite les aller-retours Python â†” C++ rÃ©pÃ©tÃ©s
    - Utilise des arrays NumPy pour les donnÃ©es
"""

import numpy as np
from typing import Dict, List, Tuple
from itertools import product, combinations_with_replacement
from math import comb
import strategy_metrics_cpp

from myproject.option.option_class import Option
from myproject.strategy.strategy_class import StrategyComparison
from myproject.strategy.strategy_naming import generate_strategy_name
from myproject.option.option_utils_v2 import get_expiration_info
from myproject.app.filter_widget import FilterData
from myproject.app.progress_tracker import get_step_for_leg


# =============================================================================
# INITIALISATION DU CACHE C++
# =============================================================================

def init_cpp_cache(options: List[Option]) -> bool:
    """
    Initialise le cache C++ avec toutes les donnÃ©es des options.
    
    Extrait les donnÃ©es des objets Option Python et les transmet au C++
    pour Ã©viter les conversions rÃ©pÃ©tÃ©es lors du traitement batch.
    
    Args:
        options: Liste des options Ã  charger dans le cache
        
    Returns:
        True si l'initialisation a rÃ©ussi, False sinon
    """
    if not options:
        return False
        
    # VÃ©rifier que les donnÃ©es sont valides
    if options[0].pnl_array is None or options[0].prices is None:
        return False
    
    n = len(options)
    pnl_length = len(options[0].pnl_array)
    
    # Extraction des donnÃ©es des options
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
    
    # DonnÃ©es de rolls
    rolls = np.array([opt.roll or 0.0 for opt in options], dtype=np.float64)
    rolls_quarterly = np.array([opt.roll_quarterly or 0.0 for opt in options], dtype=np.float64)
    rolls_sum = np.array([opt.roll_sum or 0.0 for opt in options], dtype=np.float64)
    
    # Matrice P&L
    pnl_matrix = np.zeros((n, pnl_length), dtype=np.float64)
    for i, opt in enumerate(options):
        if opt.pnl_array is not None:
            pnl_matrix[i] = opt.pnl_array
    
    # DonnÃ©es communes
    prices = np.array(options[0].prices, dtype=np.float64)
    mixture = np.asarray(options[0].mixture, dtype=np.float64)
    average_mix = float(options[0].average_mix) if options[0].average_mix else 0.0
    
    # Initialiser le cache C++
    strategy_metrics_cpp.init_options_cache(  # type: ignore
        premiums, deltas, gammas, vegas, thetas, ivs,
        average_pnls, sigma_pnls, strikes,
        is_calls, rolls, rolls_quarterly, rolls_sum,
        pnl_matrix, prices, mixture, average_mix
    )
    
    return True


# =============================================================================
# PRÃ‰PARATION DES COMBINAISONS
# =============================================================================

def prepare_batch_data_by_legs(
    options: List[Option], 
    n_legs: int, 
    max_legs: int = 4
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    """
    PrÃ©pare les donnÃ©es pour un nombre de legs spÃ©cifique.
    
    GÃ©nÃ¨re toutes les combinaisons d'indices d'options avec leurs variantes
    de signes (long/short) pour un nombre de legs donnÃ©.
    
    Args:
        options: Liste des options
        n_legs: Nombre de legs Ã  prÃ©parer
        max_legs: Nombre maximum de legs (pour le padding des arrays)
        
    Returns:
        Tuple (indices_batch, signs_batch, combo_sizes, n_combos)
        Retourne (None, None, None, 0) si aucune combinaison valide
    """
    option_to_idx = {id(opt): i for i, opt in enumerate(options)}
    
    all_combos = []
    all_signs = []
    all_sizes = []
    
    # Toutes les combinaisons de signes possibles pour ce nombre de legs
    sign_variants = list(product([-1, 1], repeat=n_legs))
    
    # Combinaisons avec rÃ©pÃ©tition (mÃªme option peut apparaÃ®tre plusieurs fois)
    for combo in combinations_with_replacement(options, n_legs):
        # VÃ©rifier que toutes les options ont la mÃªme expiration
        if n_legs > 1:
            first, last = combo[0], combo[-1]
            if (first.expiration_year != last.expiration_year or 
                first.expiration_month != last.expiration_month):
                continue
        
        indices = [option_to_idx[id(opt)] for opt in combo]
        
        # Ajouter toutes les variantes de signes
        for signs in sign_variants:
            all_combos.append(indices)
            all_signs.append(list(signs))
            all_sizes.append(n_legs)
    
    if not all_combos:
        return None, None, None, 0  # type: ignore
    
    n_combos = len(all_combos)
    
    # CrÃ©er les arrays numpy avec padding
    indices_batch = np.full((n_combos, max_legs), -1, dtype=np.int32)
    signs_batch = np.zeros((n_combos, max_legs), dtype=np.int32)
    combo_sizes = np.array(all_sizes, dtype=np.int32)
    
    for i, (combo, signs) in enumerate(zip(all_combos, all_signs)):
        for j, (idx, sign) in enumerate(zip(combo, signs)):
            indices_batch[i, j] = idx
            signs_batch[i, j] = sign
    
    return indices_batch, signs_batch, combo_sizes, n_combos


# =============================================================================
# TRAITEMENT C++
# =============================================================================

def process_batch_cpp(
    indices_batch: np.ndarray,
    signs_batch: np.ndarray,
    combo_sizes: np.ndarray,
    filter: FilterData
) -> List:
    """
    Traite un batch de combinaisons via le module C++.
    
    Args:
        indices_batch: Array 2D des indices d'options par combinaison
        signs_batch: Array 2D des signes par combinaison
        combo_sizes: Array 1D du nombre de legs par combinaison
        filter: Filtres Ã  appliquer
        
    Returns:
        Liste de tuples (indices, signs, metrics_dict) pour les stratÃ©gies valides
    """
    return strategy_metrics_cpp.process_combinations_batch(  # type: ignore
        indices_batch, 
        signs_batch, 
        combo_sizes,
        filter.max_loss_left,
        filter.max_loss_right,
        filter.max_premium,
        filter.ouvert_gauche,
        filter.ouvert_droite,
        filter.min_premium_sell,
        filter.delta_min,
        filter.delta_max,
        filter.limit_left,
        filter.limit_right
    )


# =============================================================================
# CONVERSION DES RÃ‰SULTATS
# =============================================================================

def batch_to_strategies(
    results: List,
    options: List[Option]
) -> List[StrategyComparison]:
    """
    Convertit les rÃ©sultats du batch C++ en objets StrategyComparison.
    
    Args:
        results: Liste de tuples (indices, signs, metrics) du C++
        options: Liste des options originales
        
    Returns:
        Liste d'objets StrategyComparison
    """
    strategies = []
    
    if not options or options[0].prices is None:
        return strategies
    
    prices = options[0].prices
    
    for indices, signs, metrics in results:
        # RÃ©cupÃ©rer les options correspondantes
        opts = [options[i] for i in indices]
        signs_arr = np.array([float(s) for s in signs], dtype=np.float64)
        
        # GÃ©nÃ©rer le nom et l'expiration
        strategy_name = generate_strategy_name(opts, signs_arr)
        exp_info = get_expiration_info(opts)
        
        # Calculer rolls_detail (agrÃ©gation des rolls par expiry)
        total_rolls_detail: Dict[str, float] = {}
        for i, opt in enumerate(opts):
            if opt.rolls_detail:
                for label, value in opt.rolls_detail.items():
                    if label not in total_rolls_detail:
                        total_rolls_detail[label] = 0.0
                    total_rolls_detail[label] += float(signs_arr[i]) * value
        
        # CrÃ©er la StrategyComparison
        strat = StrategyComparison(
            strategy_name=strategy_name,
            strategy=None,
            premium=metrics['total_premium'],
            all_options=opts,
            signs=signs_arr,
            call_count=metrics.get('call_count', 0),
            put_count=metrics.get('put_count', 0),
            expiration_month=exp_info.get("expiration_month", "F"),
            expiration_year=exp_info.get("expiration_year", 6),
            max_profit=metrics['max_profit'],
            max_loss=metrics['max_loss'],
            breakeven_points=metrics.get('breakeven_points', []),
            profit_range=(
                metrics.get('min_profit_price', 0), 
                metrics.get('max_profit_price', 0)
            ),
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
            rolls_detail=total_rolls_detail,
        )
        strategies.append(strat)
    
    return strategies


# =============================================================================
# FONCTION PRINCIPALE
# =============================================================================

def generate_all_strategies_batch(
    progress_tracker,
    options: List[Option],
    filter: FilterData,
    max_legs: int = 4,
) -> Tuple[List[StrategyComparison], int]:
    """
    GÃ©nÃ¨re toutes les stratÃ©gies en mode batch C++.
    
    Traite chaque nombre de legs sÃ©parÃ©ment pour permettre 
    la mise Ã  jour de la progression.
    
    Args:
        progress_tracker: Tracker de progression (peut Ãªtre None)
        options: Liste des options
        filter: Filtres Ã  appliquer
        max_legs: Nombre maximum de legs
        
    Returns:
        Tuple (liste des stratÃ©gies valides, nombre total de combinaisons)
    """
    print(f"ðŸš€ MODE BATCH C++ ACTIVÃ‰")

    # Initialiser le cache C++ (une seule fois)
    if not init_cpp_cache(options):
        return [], 0
    
    # PrÃ©-calculer le nombre total de combinaisons
    n_options = len(options)
    combos_per_leg = {}
    grand_total = 0
    
    for n_legs in range(1, max_legs + 1):
        # C(n+r-1, r) * 2^r (combinaisons avec rÃ©pÃ©tition * variantes de signes)
        n_combos_raw = comb(n_options + n_legs - 1, n_legs) * (2 ** n_legs)
        combos_per_leg[n_legs] = n_combos_raw
        grand_total += n_combos_raw
    
    all_strategies: List[StrategyComparison] = []
    total_combos_done = 0
    total_valid = 0
    
    # Traiter chaque nombre de legs sÃ©parÃ©ment
    for n_legs in range(1, max_legs + 1):
        
        # Mettre Ã  jour la progression
        if progress_tracker:
            step = get_step_for_leg(n_legs)
            pct = total_combos_done / grand_total * 100 if grand_total > 0 else 0
            progress_tracker.update(
                step, 
                f"[{total_combos_done:,} / {grand_total:,}] Traitement {n_legs} leg(s)... ({pct:.0f}%)"
            )
        
        # PrÃ©parer les donnÃ©es pour ce nombre de legs
        indices_batch, signs_batch, combo_sizes, n_combos = prepare_batch_data_by_legs(
            options, n_legs, max_legs
        )
        
        if indices_batch is None:
            continue
        
        # Traiter en batch C++
        results = process_batch_cpp(indices_batch, signs_batch, combo_sizes, filter)
        n_valid = len(results)
        total_valid += n_valid
        total_combos_done += n_combos
        
        # Convertir en StrategyComparison
        strategies = batch_to_strategies(results, options)
        all_strategies.extend(strategies)
        
        pct_done = total_combos_done / grand_total * 100 if grand_total > 0 else 0
        print(f"  â€¢ {n_legs} leg(s): {n_combos:,} â†’ {n_valid:,} valides | "
              f"Cumul: {total_combos_done:,}/{grand_total:,} ({pct_done:.0f}%)")
        
        # Mettre Ã  jour les stats dans le progress tracker
        if progress_tracker:
            progress_tracker.update_substep(
                1.0,
                f"[{total_combos_done:,} / {grand_total:,}] {total_valid:,} stratÃ©gies valides"
            )
    
    return all_strategies, grand_total

