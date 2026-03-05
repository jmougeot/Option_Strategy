"""
Batch Processor C++ pour le traitement des combinaisons d'options
"""

import numpy as np
from typing import Dict, List, Tuple, Optional 
import strategy_metrics_cpp

from option.option_class import Option
from strategy.strategy_class import StrategyComparison
from strategy.multi_ranking import MultiRankingResult
from strategy.strategy_naming import generate_strategy_name
from option.option_utils_v2 import get_expiration_info
from app.data_types import FilterData


# Cache global pour stocker les options (n�cessaire pour batch_to_strategies)
_options_cache: List[Option] = []


def clear_caches():
    """Libere la memoire des caches Python et C++ apres traitement."""
    global _options_cache
    _options_cache = []
    try:
        strategy_metrics_cpp.clear_options_cache()  # type: ignore
    except Exception:
        pass


# =============================================================================
# INITIALISATION DU CACHE C++
# =============================================================================

def init_cpp_cache(options: List[Option]) -> bool:
    """
    Initialise le cache C++ avec toutes les donnees des options.

    """
    global _options_cache
    
    if not options:
        return False
        
    # Stocker les options dans le cache global pour batch_to_strategies
    _options_cache = options
        
    if options[0].pnl_array is None or options[0].prices is None:
        return False
    
    n = len(options)
    pnl_length = len(options[0].pnl_array)
    
    # Extraction des donnees des options
    premiums = np.array([opt.premium for opt in options], dtype=np.float64)
    deltas = np.array([opt.delta for opt in options], dtype=np.float64)
    gammas = np.array([opt.gamma for opt in options], dtype=np.float64)
    thetas = np.array([opt.theta for opt in options], dtype=np.float64)
    ivs = np.array([opt.implied_volatility for opt in options], dtype=np.float64)
    average_pnls = np.array([opt.average_pnl for opt in options], dtype=np.float64)
    sigma_pnls = np.array([opt.sigma_pnl for opt in options], dtype=np.float64)
    strikes = np.array([opt.strike for opt in options], dtype=np.float64)
    is_calls = np.array([opt.option_type.lower() == 'call' for opt in options], dtype=np.bool_)
    
    # Donnees de rolls
    rolls = np.array([opt.roll[0] if opt.roll else 0.0 for opt in options], dtype=np.float64)

    # Matrice P&L
    pnl_matrix = np.zeros((n, pnl_length), dtype=np.float64)
    for i, opt in enumerate(options):
        if opt.pnl_array is not None:
            pnl_matrix[i] = opt.pnl_array
    
    # Donnees communes
    prices = np.array(options[0].prices, dtype=np.float64)
    mixture = np.asarray(options[0].mixture, dtype=np.float64)
    average_mix = float(options[0].average_mix) if options[0].average_mix else 0.0
    
    # Initialiser le cache C++
    strategy_metrics_cpp.init_options_cache(  # type: ignore
        premiums,
        deltas,
        gammas,
        thetas,
        ivs,
        average_pnls,
        sigma_pnls,
        strikes,
        is_calls,
        rolls,
        pnl_matrix,
        prices,
        mixture,
        average_mix,
    )
    
    return True

# =============================================================================
# TRAITEMENT C++  MULTI-SCORING (N jeux de poids simultanes)
# =============================================================================

def process_batch_cpp_with_multi_scoring(
    n_legs: int,
    filter: FilterData,
    top_n: int = 10,
    weight_sets: Optional[List[Dict[str, float]]] = None,
    leg_penalty: float = 0.0,
) -> MultiRankingResult:
    """
    Traite un batch via C++ avec N jeux de poids simultanes
    """
    global _options_cache

    if not _options_cache:
        raise RuntimeError("Options cache is empty. Call init_cpp_cache() first.")

    if not weight_sets:
        raise ValueError("weight_sets ne peut pas etre vide pour le multi-scoring")

    # Convertir en liste de dicts pour le C++
    weight_dicts = [dict(ws) for ws in weight_sets]

    raw = strategy_metrics_cpp.process_combinations_batch_with_multi_scoring(  # type: ignore
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
        filter.premium_only,
        filter.premium_only_left,
        filter.premium_only_right,
        top_n,
        weight_dicts,
        leg_penalty,
    )

    # raw est un dict {"per_set": [...], "consensus": [...], "n_weight_sets": N, "n_candidates": M}
    per_set_strategies: List[List[StrategyComparison]] = []
    for set_results in raw["per_set"]:
        per_set_strategies.append(batch_to_strategies(set_results, _options_cache))

    consensus_strategies = batch_to_strategies(raw["consensus"], _options_cache)

    return MultiRankingResult(
        per_set_strategies=per_set_strategies,
        consensus_strategies=consensus_strategies,
        weight_sets=weight_sets,
        n_candidates=int(raw.get("n_candidates", 0)),
    )


# =============================================================================
# CONVERSION DES RESULTATS
# =============================================================================

def batch_to_strategies(
    results: List,
    options: List[Option]
) -> List[StrategyComparison]:
    """
    Convertit les resultats du batch C++ en objets StrategyComparison.
    
    """
    strategies = []
    
    if not options or options[0].prices is None:
        return strategies
    
    prices = options[0].prices
    
    for indices, signs, metrics in results:
        # R�cup�rer les options correspondantes
        opts = [options[i] for i in indices]
        signs_arr = np.array([float(s) for s in signs], dtype=np.float64)
        
        # G�n�rer le nom et l'expiration
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
        
        # Cr�er la StrategyComparison
        strat = StrategyComparison(
            strategy_name=strategy_name,
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
            total_delta=metrics.get('total_delta', 0.0),
            total_gamma=metrics.get('total_gamma', 0.0),
            total_vega=metrics.get('total_vega', 0.0),
            total_theta=metrics.get('total_theta', 0.0),
            total_iv=metrics.get('total_iv', metrics.get('avg_implied_volatility', 0)),
            profit_at_target=0,
            score=metrics.get('score', 0.0),  # Score depuis C++ si disponible
            rank=metrics.get('rank', 0),      # Rank depuis C++ si disponible
            rolls_detail=total_rolls_detail,
            delta_levrage=metrics.get('delta_levrage', 0.0),
            avg_pnl_levrage=metrics.get('avg_pnl_levrage', 0.0),
        )
                
        strategies.append(strat)
    
    return strategies
