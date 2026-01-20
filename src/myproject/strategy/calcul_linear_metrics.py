"""
Calcul Complet et Optimisé des Métriques de Stratégie d'Options
Version ultra-optimisée avec NumPy vectorization et calcul en une passe
"""

from typing import List, Optional, Dict, Tuple
from myproject.option.option_class import Option
from myproject.strategy.comparison_class import StrategyComparison
from myproject.strategy.strategy_naming_v2 import generate_strategy_name
from myproject.option.option_utils_v2 import get_expiration_info
from myproject.app.filter_widget import FilterData
import numpy as np


# Cache global pour les données extraites des options (évite re-extraction)
_options_data_cache: Dict[int, Tuple[np.ndarray, ...]] = {}


def _extract_options_data(options: List[Option]) -> Optional[Tuple[np.ndarray, ...]]:
    """
    Extrait toutes les données des options en UNE SEULE passe.
    Retourne un tuple de arrays pour éviter les allocations répétées.
    """
    n = len(options)
    opt0 = options[0]
    
    if opt0.prices is None or opt0.pnl_array is None:
        return None
    
    pnl_length = len(opt0.pnl_array)
    
    # Pré-allouer tous les arrays
    premiums = np.empty(n, dtype=np.float64)
    deltas = np.empty(n, dtype=np.float64)
    gammas = np.empty(n, dtype=np.float64)
    vegas = np.empty(n, dtype=np.float64)
    thetas = np.empty(n, dtype=np.float64)
    ivs = np.empty(n, dtype=np.float64)
    average_pnls = np.empty(n, dtype=np.float64)
    is_call = np.empty(n, dtype=bool)
    pnl_stack = np.empty((n, pnl_length), dtype=np.float64)
    rolls = np.empty(n, dtype=np.float64)
    rolls_quarterly = np.empty(n, dtype=np.float64)
    rolls_sum = np.empty(n, dtype=np.float64)
    strikes = np.empty(n, dtype=np.float64)
    
    # UNE SEULE boucle pour tout extraire
    for i, opt in enumerate(options):
        if opt.pnl_array is None:
            return None
        premiums[i] = opt.premium
        deltas[i] = opt.delta
        gammas[i] = opt.gamma
        vegas[i] = opt.vega
        thetas[i] = opt.theta
        ivs[i] = opt.implied_volatility
        average_pnls[i] = opt.average_pnl
        is_call[i] = opt.option_type.lower() == "call"
        pnl_stack[i] = opt.pnl_array
        rolls[i] = opt.roll if opt.roll is not None else 0.0
        rolls_quarterly[i] = opt.roll_quarterly if opt.roll_quarterly is not None else 0.0
        rolls_sum[i] = opt.roll_sum if opt.roll_sum is not None else 0.0
        strikes[i] = opt.strike
    
    return (premiums, deltas, gammas, vegas, thetas, ivs, average_pnls, 
            is_call, pnl_stack, rolls, rolls_quarterly, rolls_sum, strikes)


def create_strategy_fast_with_signs(
    options: List[Option], signs: np.ndarray, filter: FilterData
) -> Optional[StrategyComparison]:
    """
    Version ultra-optimisée qui prend les signes directement.
    - Extraction des données en une seule passe
    - Filtrage précoce (early return) avant calculs coûteux
    - Calcul du sigma/roll seulement si nécessaire
    """
    n_options = len(options)
    if n_options == 0 or n_options != len(signs):
        return None

    # Extraction en une seule passe (ou depuis cache si disponible)
    opt0 = options[0]
    prices = opt0.prices
    if prices is None:
        return None
    
    # Créer une clé de cache basée sur les ids des options
    cache_key = hash(tuple(id(opt) for opt in options))
    
    if cache_key in _options_data_cache:
        data = _options_data_cache[cache_key]
    else:
        data = _extract_options_data(options)
        if data is None:
            return None
        # Limiter la taille du cache
        if len(_options_data_cache) > 10000:
            _options_data_cache.clear()
        _options_data_cache[cache_key] = data
    
    (premiums, deltas, gammas, vegas, thetas, ivs, average_pnls, 
     is_call, pnl_stack, rolls, rolls_quarterly, rolls_sum, strikes) = data

    # ===== FILTRES PRÉCOCES (avant calculs coûteux) =====
    
    # Éliminer la vente d'option qui ne rapporte rien
    short_mask = signs < 0
    if np.any(short_mask & (premiums < filter.min_premium_sell)):
        return None
    
    # Vérifier doublons (même type + même strike + signes opposés)
    if n_options > 1:
        for i in range(n_options - 1):
            # Trouver les options avec même type et même strike
            same_type_strike = (is_call[i+1:] == is_call[i]) & (strikes[i+1:] == strikes[i])
            if np.any(same_type_strike):
                # Vérifier si signes opposés
                j_indices = np.where(same_type_strike)[0] + i + 1
                if np.any(signs[j_indices] != signs[i]):
                    return None
    
    # Calculs rapides des compteurs
    long_mask = signs > 0
    long_call_count = np.count_nonzero(long_mask & is_call)
    short_call_count = np.count_nonzero(short_mask & is_call)
    long_put_count = np.count_nonzero(long_mask & (~is_call))
    short_put_count = np.count_nonzero(short_mask & (~is_call))

    if short_put_count - long_put_count > filter.ouvert_gauche:
        return None
    
    if short_call_count - long_call_count > filter.ouvert_droite:
        return None

    # Premium (calcul rapide avec dot product)
    total_premium = float(np.dot(signs, premiums))
    if abs(total_premium) > filter.max_premium:
        return None
    
    # Delta (vérifier que le delta est dans la plage demandée)
    total_delta = float(np.dot(signs, deltas))
    if total_delta < filter.delta_min or total_delta > filter.delta_max:
        return None

    # Average PnL (filtre important)
    total_average_pnl = float(np.dot(signs, average_pnls))
    if total_average_pnl < 0:
        return None

    # ===== CALCULS P&L (après filtres) =====
    total_pnl_array = np.dot(signs, pnl_stack)
    idx = np.searchsorted(prices, options[0].average_mix)

    # Partie gauche = prix bas (avant average_mix)
    if idx > 0:
        total_pnl_array_left = total_pnl_array[:idx]
        max_loss_left = float(np.min(total_pnl_array_left))
        if max_loss_left < -filter.max_loss_left:
            return None
    
    # Partie droite = prix hauts (après average_mix)
    if idx < len(total_pnl_array):
        total_pnl_array_right = total_pnl_array[idx:]
        max_loss_right = float(np.min(total_pnl_array_right))
        if max_loss_right < -filter.max_loss_right:
            return None
    
    max_profit = float(np.max(total_pnl_array))

    # ===== CALCULS GRECS (après tous les filtres) =====
    total_gamma = float(np.dot(signs, gammas))
    total_vega = float(np.dot(signs, vegas))
    total_theta = float(np.dot(signs, thetas))
    total_iv = float(np.dot(signs, ivs))

    # Breakeven points
    sign_changes = total_pnl_array[:-1] * total_pnl_array[1:] < 0
    breakeven_indices = np.where(sign_changes)[0]

    if len(breakeven_indices) > 0:
        idx = breakeven_indices
        denom = total_pnl_array[idx + 1] - total_pnl_array[idx]
        # Éviter division par zéro
        safe_denom = np.where(denom != 0, denom, 1.0)
        t = -total_pnl_array[idx] / safe_denom
        breakeven_points = (prices[idx] + (prices[idx + 1] - prices[idx]) * t).tolist()
    else:
        breakeven_points = []

    # Profit zone
    profitable_indices = np.where(total_pnl_array > 0)[0]

    if len(profitable_indices) > 0:
        min_profit_price = float(prices[profitable_indices[0]])
        max_profit_price = float(prices[profitable_indices[-1]])
        profit_zone_width = max_profit_price - min_profit_price
        profit_range = (min_profit_price, max_profit_price)
    else:
        profit_range = (0.0, 0.0)
        profit_zone_width = 0.0

    dx = prices[1] - prices[0]
    
    # Roll (déjà extrait, simple dot product)
    total_roll = float(np.dot(signs, rolls))
    total_roll_quarterly = float(np.dot(signs, rolls_quarterly))
    total_roll_sum = float(np.dot(signs, rolls_sum))
    
    # Sigma (calcul UNIQUEMENT après tous les filtres passés)
    mixture = opt0.mixture
    if mixture is not None:
        mass = np.sum(mixture) * dx
        if mass > 0:
            diff_sq = (total_pnl_array - total_average_pnl) ** 2
            var = np.sum(mixture * diff_sq) * dx / mass
            total_sigma_pnl = float(np.sqrt(max(var, 0.0)))
        else:
            total_sigma_pnl = 0.0
    else:
        total_sigma_pnl = 0.0

    # Nom et expiration (après tous les filtres)
    strategy_name = generate_strategy_name(options, signs)
    exp_info = get_expiration_info(options)

    try:
        strategy = StrategyComparison(
            strategy_name=strategy_name,
            strategy=None,
            target_price=98,
            premium=float(total_premium),
            all_options=options,
            signs=signs,  # Stocker les signes utilisés
            call_count=0,
            put_count=0,
            expiration_day=exp_info.get("expiration_day"),
            expiration_week=exp_info.get("expiration_week"),
            expiration_month=exp_info.get("expiration_month", "F"),
            expiration_year=exp_info.get("expiration_year", 6),
            max_profit=max_profit,
            max_loss=min(max_loss_left, max_loss_right),
            breakeven_points=breakeven_points,
            profit_range=profit_range,
            profit_zone_width=profit_zone_width,
            average_pnl=float(total_average_pnl),
            sigma_pnl=float(total_sigma_pnl),
            pnl_array=total_pnl_array,
            prices=prices,
            total_delta=float(total_delta),
            total_gamma=float(total_gamma),
            total_vega=float(total_vega),
            total_theta=float(total_theta),
            avg_implied_volatility=float(total_iv),
            profit_at_target=0,
            score=0.0,
            rank=0,
            roll=total_roll,
            roll_quarterly=total_roll_quarterly,
            roll_sum=total_roll_sum,
        )
        return strategy
    except Exception as e:
        print(f"⚠️ Erreur création stratégie: {e}")
        return None