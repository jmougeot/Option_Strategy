"""
Calcul Complet et Optimisé des Métriques de Stratégie d'Options
Version ultra-optimisée avec NumPy vectorization et calcul en une passe
"""

from typing import List, Optional
from myproject.option.option_class import Option
from myproject.strategy.comparison_class import StrategyComparison
from myproject.strategy.strategy_naming_v2 import generate_strategy_name
from myproject.option.option_utils_v2 import get_expiration_info
import numpy as np


def create_strategy_fast_with_signs(
    options: List[Option], signs: np.ndarray, target_price: float
) -> Optional[StrategyComparison]:
    """
    Version optimisée qui prend les signes directement (évite les copies d'options).

    Args:
        options: Liste d'options (positions originales ignorées)
        signs: Array NumPy des signes (+1 pour long, -1 pour short)
        target_price: Prix cible pour les calculs

    Returns:
        StrategyComparison complète ou None si invalide
    """
    if not options or len(options) != len(signs):
        return None

    # Extraction vectorisée ultra-rapide
    n_options = len(options)
    premiums = np.empty(n_options, dtype=np.float64)
    deltas = np.empty(n_options, dtype=np.float64)
    gammas = np.empty(n_options, dtype=np.float64)
    vegas = np.empty(n_options, dtype=np.float64)
    thetas = np.empty(n_options, dtype=np.float64)
    ivs = np.empty(n_options, dtype=np.float64)
    profit_surfaces_ponderated = np.empty(n_options, dtype=np.float64)
    loss_surfaces_ponderated = np.empty(n_options, dtype=np.float64)
    average_pnls = np.empty(n_options, dtype=np.float64)
    sigma_pnls = np.empty(n_options, dtype=np.float64)
    is_call = np.empty(n_options, dtype=bool)
  
    for i, opt in enumerate(options):
        premiums[i] = opt.premium
        deltas[i] = opt.delta
        gammas[i] = opt.gamma
        vegas[i] = opt.vega
        thetas[i] = opt.theta
        ivs[i] = opt.implied_volatility
        profit_surfaces_ponderated[i] = opt.profit_surface_ponderated
        loss_surfaces_ponderated[i] = opt.loss_surface_ponderated
        average_pnls[i] = opt.average_pnl
        sigma_pnls[i] = opt.sigma_pnl
        is_call[i] = opt.option_type == "call"

    # Calculer call_count vectorisé (conversion en int pour l'arithmétique)
    call_count = int(np.sum((signs < 0) & is_call, dtype=np.int32) - np.sum((signs > 0) & is_call, dtype=np.int32))

    if call_count >= 1:
        return None
    
    is_long = signs > 0
    total_premium = np.sum(signs * premiums)
    total_delta = np.sum(signs * deltas)
    total_gamma = np.sum(signs * gammas)
    total_vega = np.sum(signs * vegas)
    total_theta = np.sum(signs * thetas)
    total_iv = np.sum(signs * ivs)


    # Filtrage précoce AVANT calculs coûteux
    if total_premium > 0.05 or total_premium < -0.1:
        return None
    if abs(total_delta) > 0.7:
        return None
    
    total_profit_surface = np.sum(np.where(is_long, profit_surfaces_ponderated, -loss_surfaces_ponderated))
    total_loss_surface = np.sum(np.where(is_long, loss_surfaces_ponderated, -profit_surfaces_ponderated))
    total_average_pnl = np.sum(signs * average_pnls)
    total_sigma_pnl = np.sqrt(np.sum(sigma_pnls**2))

    if total_average_pnl < 0:
        return None
    # P&L Array - Extraction vectorisée
    prices = options[0].prices
    if prices is None:
        return None

    pnl_arrays = np.array([opt.pnl_array for opt in options if opt.pnl_array is not None])
    total_pnl_array = np.sum(pnl_arrays * signs[:, np.newaxis], axis=0)

    max_profit = float(np.max(total_pnl_array))
    max_loss = float(np.min(total_pnl_array))

    if max_loss < -0.10:
        return None
    if max_loss < 0:
        risk_reward_ratio = abs(max_profit / max_loss)
    else:
        risk_reward_ratio = float("inf") if max_profit > 0 else 0.0

    # Breakeven points (vectorisé)
    sign_changes = total_pnl_array[:-1] * total_pnl_array[1:] < 0
    breakeven_indices = np.where(sign_changes)[0]

    if len(breakeven_indices) > 0:
        idx = breakeven_indices
        t = -total_pnl_array[idx] / (total_pnl_array[idx + 1] - total_pnl_array[idx])
        breakeven_points = (prices[idx] + (prices[idx + 1] - prices[idx]) * t).tolist()
    else:
        breakeven_points = []

    # Profit zone
    profitable_mask = total_pnl_array > 0
    profitable_indices = np.where(profitable_mask)[0]

    if len(profitable_indices) > 0:
        min_profit_price = float(prices[profitable_indices[0]])
        max_profit_price = float(prices[profitable_indices[-1]])
        profit_zone_width = max_profit_price - min_profit_price
        profit_range = (min_profit_price, max_profit_price)
    else:
        profit_range = (0.0, 0.0)
        profit_zone_width = 0.0

    # Profit au prix cible
    profit_at_target = float(np.interp(target_price, prices, total_pnl_array))
    
    if abs(profit_at_target) > 100:
        return None
    
    profit_at_target_pct = 0.0
    if max_profit > 0:
        profit_at_target_pct = (profit_at_target / max_profit) * 100.0

    # Surfaces non pondérées (calcul optimisé)
    # Si les prix sont uniformément espacés, pas besoin de np.mean
    dx = prices[1] - prices[0]  # Beaucoup plus rapide que np.mean(np.diff(prices))
    
    positive_pnl = np.maximum(total_pnl_array, 0.0)
    negative_pnl = np.minimum(total_pnl_array, 0.0)
    surface_profit_nonponderated = float(np.sum(positive_pnl) * dx)
    surface_profit_nonponderated = float(np.sum(positive_pnl) * dx)
    surface_loss_nonponderated = float(np.abs(np.sum(negative_pnl)) * dx)

    # Calcul du nom et expiration SEULEMENT si on va créer la stratégie (calculs coûteux)
    strategy_name = generate_strategy_name(options, signs)
    exp_info = get_expiration_info(options)

    try:
        strategy = StrategyComparison(
            strategy_name=strategy_name,
            strategy=None,
            target_price=target_price,
            premium=float(total_premium),
            all_options=options,
            signs=signs,  # Stocker les signes utilisés
            call_count=call_count,
            expiration_day=exp_info.get("expiration_day"),
            expiration_week=exp_info.get("expiration_week"),
            expiration_month=exp_info.get("expiration_month", "F"),
            expiration_year=exp_info.get("expiration_year", 6),
            max_profit=max_profit,
            max_loss=max_loss,
            breakeven_points=breakeven_points,
            profit_range=profit_range,
            profit_zone_width=profit_zone_width,
            surface_profit=surface_profit_nonponderated,
            surface_loss=surface_loss_nonponderated,
            surface_profit_ponderated=float(total_profit_surface),
            surface_loss_ponderated=float(total_loss_surface),
            average_pnl=float(total_average_pnl),
            sigma_pnl=float(total_sigma_pnl),
            pnl_array=total_pnl_array,
            prices=prices,
            risk_reward_ratio=risk_reward_ratio,
            risk_reward_ratio_ponderated=risk_reward_ratio,
            total_delta=float(total_delta),
            total_gamma=float(total_gamma),
            total_vega=float(total_vega),
            total_theta=float(total_theta),
            avg_implied_volatility=float(total_iv),
            profit_at_target=profit_at_target,
            profit_at_target_pct=profit_at_target_pct,
            score=0.0,
            rank=0,
        )
        return strategy
    except Exception as e:
        print(f"⚠️ Erreur création stratégie: {e}")
        return None
