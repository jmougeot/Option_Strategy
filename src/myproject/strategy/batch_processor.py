"""
Batch Processor C++ pour le traitement des combinaisons d'options
"""

import numpy as np
from typing import Dict, List, Tuple, Optional 
import strategy_metrics_cpp

from myproject.option.option_class import Option
from myproject.strategy.strategy_class import StrategyComparison
from myproject.strategy.multi_ranking import MultiRankingResult
from myproject.strategy.strategy_naming import generate_strategy_name
from myproject.option.option_utils_v2 import get_expiration_info
from myproject.app.widget_filter import FilterData


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
    ivs = np.array([opt.implied_volatility for opt in options], dtype=np.float64)
    average_pnls = np.array([opt.average_pnl for opt in options], dtype=np.float64)
    sigma_pnls = np.array([opt.sigma_pnl for opt in options], dtype=np.float64)
    strikes = np.array([opt.strike for opt in options], dtype=np.float64)
    is_calls = np.array([opt.option_type.lower() == 'call' for opt in options], dtype=np.bool_)
    
    # Données de rolls
    rolls = np.array([opt.roll[0] if opt.roll else 0.0 for opt in options], dtype=np.float64)
    # Prix intra-vie et P&L intra-vie (calculés via Bachelier)
    # Le C++ attend une matrice (n_options x 5 dates) avec un seul prix par date
    # On calcule le prix moyen pondéré par la mixture si disponible
    n_intra_dates = 5
    intra_life_prices = np.zeros((n, n_intra_dates), dtype=np.float64)
    intra_life_pnl = np.zeros((n, n_intra_dates), dtype=np.float64)
    
    for i, opt in enumerate(options):
        if opt.intra_life_prices is not None:
            # intra_life_prices est maintenant une matrice (5 dates x N strikes)
            if isinstance(opt.intra_life_prices, np.ndarray) and opt.intra_life_prices.ndim == 2:
                # Calculer le prix moyen pour chaque date
                # Si on a la mixture et les prix, pondérer par la mixture
                for t in range(min(n_intra_dates, opt.intra_life_prices.shape[0])):
                    # Prix moyen simple sur tous les strikes
                    intra_life_prices[i, t] = np.mean(opt.intra_life_prices[t, :])
                    if opt.intra_life_pnl is not None and opt.intra_life_pnl.ndim == 2:
                        intra_life_pnl[i, t] = np.mean(opt.intra_life_pnl[t, :])
            elif len(opt.intra_life_prices) == n_intra_dates:
                # Ancienne structure: vecteur de 5 valeurs
                intra_life_prices[i] = opt.intra_life_prices
                if opt.intra_life_pnl is not None and len(opt.intra_life_pnl) == n_intra_dates:
                    intra_life_pnl[i] = opt.intra_life_pnl
        else:
            # Valeur de repli: utiliser le premium comme approximation
            intra_life_prices[i] = [opt.premium] * n_intra_dates
            intra_life_pnl[i] = [0.0] * n_intra_dates
    
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
        premiums,
        deltas,
        ivs,
        average_pnls,
        sigma_pnls,
        strikes,
        is_calls,
        rolls,
        intra_life_prices,
        intra_life_pnl,
        pnl_matrix,
        prices,
        mixture,
        average_mix,
    )
    
    return True

# =============================================================================
# TRAITEMENT C++ — MULTI-SCORING (N jeux de poids simultanés)
# =============================================================================

def process_batch_cpp_with_multi_scoring(
    n_legs: int,
    filter: FilterData,
    top_n: int = 10,
    weight_sets: Optional[List[Dict[str, float]]] = None,
) -> MultiRankingResult:
    """
    Traite un batch via C++ avec N jeux de poids simultanés.

    Le C++ fait :
      1. Génération parallèle des combinaisons
      2. Normalisation commune de toutes les métriques
      3. Scoring par jeu de poids → top_n par jeu
      4. Classement consensus par moyenne des rangs

    Fonctionne aussi avec un seul jeu de poids (N=1).

    Returns:
        MultiRankingResult contenant per_set + consensus
    """
    global _options_cache

    if not _options_cache:
        raise RuntimeError("Options cache is empty. Call init_cpp_cache() first.")

    if not weight_sets:
        raise ValueError("weight_sets ne peut pas être vide pour le multi-scoring")

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
        top_n,
        weight_dicts,
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
        
        # Récupérer les prix intra-vie depuis les métriques C++
        intra_life_prices = metrics.get('intra_life_prices', None)
        if intra_life_prices is not None:
            intra_life_prices = list(intra_life_prices)
        
        # Dates intermédiaires (fractions de temps: 0.2, 0.4, 0.6, 0.8, 1.0)
        intra_life_dates = [0.2, 0.4, 0.6, 0.8, 1.0] if intra_life_prices else None
        
        # Récupérer le P&L intra-vie
        intra_life_pnl = metrics.get('intra_life_pnl', None)
        if intra_life_pnl is not None:
            intra_life_pnl = list(intra_life_pnl)
        
        # Moyenne des P&L intra-vie
        avg_intra_life_pnl = metrics.get('avg_intra_life_pnl', None)
        
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
            total_delta=metrics.get('total_delta', 0.0),
            total_gamma=metrics.get('total_gamma', 0.0),
            total_vega=metrics.get('total_vega', 0.0),
            total_theta=metrics.get('total_theta', 0.0),
            avg_implied_volatility=metrics.get('total_iv', metrics.get('avg_implied_volatility', 0)),
            profit_at_target=0,
            score=metrics.get('score', 0.0),  # Score depuis C++ si disponible
            rank=metrics.get('rank', 0),      # Rank depuis C++ si disponible
            rolls_detail=total_rolls_detail,
            delta_levrage=metrics.get('delta_levrage', 0.0),
            avg_pnl_levrage=metrics.get('avg_pnl_levrage', 0.0),
            tail_penalty=metrics.get('tail_penalty', 0.0),
            intra_life_prices=intra_life_prices,
            intra_life_pnl=intra_life_pnl,
            intra_life_dates=intra_life_dates,
            avg_intra_life_pnl=avg_intra_life_pnl,
        )
                
        strategies.append(strat)
    
    return strategies