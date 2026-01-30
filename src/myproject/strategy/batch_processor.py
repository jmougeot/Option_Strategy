"""
Batch Processor C++ pour le traitement des combinaisons d'options
"""

import numpy as np
from typing import Dict, List, Tuple, Optional 
import strategy_metrics_cpp

from myproject.option.option_class import Option
from myproject.strategy.strategy_class import StrategyComparison
from myproject.strategy.strategy_naming import generate_strategy_name
from myproject.option.option_utils_v2 import get_expiration_info
from myproject.app.filter_widget import FilterData


# Cache global pour stocker les options (nécessaire pour batch_to_strategies)
_options_cache: List[Option] = []


# =============================================================================
# INITIALISATION DU CACHE C++
# =============================================================================

def init_cpp_cache(options: List[Option]) -> bool:
    """
    Initialise le cache C++ avec toutes les données des options.

    """
    global _options_cache
    
    if not options:
        return False
        
    # Stocker les options dans le cache global pour batch_to_strategies
    _options_cache = options
        
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

def process_batch_cpp_with_scoring(
    n_legs: int,
    filter: FilterData,
    top_n: int = 5,
    custom_weights: Optional[Dict[str, float]] = None
) -> List[StrategyComparison]:
    """
    Traite un batch de combinaisons via le module C++ AVEC scoring et ranking.

    Returns:
        Liste de StrategyComparison pour les top_n stratégies (défaut: 5)
    """
    global _options_cache
    
    if not _options_cache:
        raise RuntimeError("Options cache is empty. Call init_cpp_cache() first.")
    
    weights_dict = custom_weights if custom_weights else {}
    
    raw_results = strategy_metrics_cpp.process_combinations_batch_with_scoring(  # type: ignore
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
        filter.limit_right,
        top_n,
        weights_dict
    )
    strategies = batch_to_strategies(raw_results, _options_cache)

    
    return strategies


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
            average_pnl=metrics.get('total_average_pnl', metrics.get('average_pnl', 0)),
            sigma_pnl=metrics.get('total_sigma_pnl', metrics.get('sigma_pnl', 0)),
            pnl_array=np.array(metrics.get('pnl_array', []), dtype=np.float64),
            prices=prices,
            total_delta=metrics['total_delta'],
            total_gamma=metrics['total_gamma'],
            total_vega=metrics['total_vega'],
            total_theta=metrics['total_theta'],
            avg_implied_volatility=metrics.get('total_iv', metrics.get('avg_implied_volatility', 0)),
            profit_at_target=0,
            score=metrics.get('score', 0.0),  # Score depuis C++ si disponible
            rank=metrics.get('rank', 0),      # Rank depuis C++ si disponible
            rolls_detail=total_rolls_detail,
        )
                
        strategies.append(strat)
    
    return strategies