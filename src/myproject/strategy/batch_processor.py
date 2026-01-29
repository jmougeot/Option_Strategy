"""
Batch Processor C++ pour le traitement des combinaisons d'options
==================================================================

Architecture:
    1. init_cpp_cache(): Charge les données des options dans le cache C++
    2. prepare_batch_data_by_legs(): Génére les indices des combinaisons
    3. process_batch_cpp(): Appelle le C++ pour traiter un batch
    4. batch_to_strategies(): Convertit les rÃ©sultats C++ en objets Python
"""

import numpy as np
from typing import Dict, List, Tuple
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
    Initialise le cache C++ avec toutes les données des options.

    """
    if not options:
        return False
        
    # Vérifier que les donées sont valides
    if options[0].pnl_array is None or options[0].prices is None:
        return False
    
    n = len(options)
    pnl_length = len(options[0].pnl_array)
    
    # Extraction des données des options
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
    
    # Données de rolls
    rolls = np.array([opt.roll or 0.0 for opt in options], dtype=np.float64)
    rolls_quarterly = np.array([opt.roll_quarterly or 0.0 for opt in options], dtype=np.float64)
    rolls_sum = np.array([opt.roll_sum or 0.0 for opt in options], dtype=np.float64)
    
    # Matrice P&L
    pnl_matrix = np.zeros((n, pnl_length), dtype=np.float64)
    for i, opt in enumerate(options):
        if opt.pnl_array is not None:
            pnl_matrix[i] = opt.pnl_array
    
    # Données communes
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
# TRAITEMENT C++
# =============================================================================

def process_batch_cpp(
    n_legs: int,
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
        n_legs,
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
# CONVERSION DES RESULTATS
# =============================================================================

def batch_to_strategies(
    results: List,
    options: List[Option]
) -> List[StrategyComparison]:
    """
    Convertit les résultats du batch C++ en objets StrategyComparison.
    
    """
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
        
        # Calculer rolls_detail
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
    Génére toutes les stratégies en mode batch C++.
    
    Args:
        progress_tracker: Tracker de progression (peut être None)
        options: Liste des options
        filter: Filtres à  appliquer
        max_legs: Nombre maximum de legs
    """

    # Initialiser le cache C++ (une seule fois)
    if not init_cpp_cache(options):
        return [], 0
    
    n_options = len(options)
    combos_per_leg = {}
    grand_total = 0
    
    for n_legs in range(1, max_legs + 1):
        n_combos_raw = comb(n_options + n_legs - 1, n_legs) * (2 ** n_legs)
        combos_per_leg[n_legs] = n_combos_raw
        grand_total += n_combos_raw
    
    all_strategies: List[StrategyComparison] = []
    total_combos_done = 0
    total_valid = 0
    
    for n_legs in range(1, max_legs + 1):
        
        if progress_tracker:
            step = get_step_for_leg(n_legs)
            pct = total_combos_done / grand_total * 100 if grand_total > 0 else 0
            progress_tracker.update(
                step, 
                f"[{total_combos_done:,} / {grand_total:,}] Traitement {n_legs} leg(s)... ({pct:.0f}%)"
            )
        
        n_combos = (len(options)*4)**max_legs
        
        # Traiter en batch C++
        results = process_batch_cpp(n_legs, filter)
        n_valid = len(results)
        total_valid += n_valid
        total_combos_done += n_combos
        
        # Convertir en StrategyComparison
        strategies = batch_to_strategies(results, options)
        all_strategies.extend(strategies)
                
        # Mettre à jour les stats dans le progress tracker
        if progress_tracker:
            progress_tracker.update_substep(
                1.0,
                f"[{total_combos_done:,} / {grand_total:,}] {total_valid:,} stratégies valides"
            )
    
    return all_strategies, grand_total

