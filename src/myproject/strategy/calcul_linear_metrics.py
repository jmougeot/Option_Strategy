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


def create_strategy_fast(
    options: List[Option],
    target_price: float
) -> Optional[StrategyComparison]:
    """
    Crée une StrategyComparison complète en une seule passe (ultra-optimisé).
    
    Calcule toutes les métriques (linéaires + non-linéaires) avec vectorisation NumPy
    et retourne directement un objet StrategyComparison sans dictionnaire intermédiaire.
    
    Args:
        options: Liste d'options constituant la stratégie
        target_price: Prix cible pour les calculs
        
    Returns:
        StrategyComparison complète ou None si invalide
    """
    if not options:
        return None
    
    # ========== PHASE 1: Extraction vectorisée des données ==========
    short_call_count = sum(1 for opt in options if opt.is_short() and opt.is_call())
    if short_call_count > 3:
        return None

    # Pré-allouer les arrays NumPy pour éviter les réallocations
    is_long = np.array([opt.position == 'long' for opt in options], dtype=bool)
    signs = np.where(is_long, 1.0, -1.0)  # +1 pour long, -1 pour short
    
    # Extraire toutes les valeurs en une fois (vectorisé)
    premiums = np.array([opt.premium for opt in options], dtype=np.float64)
    deltas = np.array([opt.delta for opt in options], dtype=np.float64)
    gammas = np.array([opt.gamma for opt in options], dtype=np.float64)
    vegas = np.array([opt.vega for opt in options], dtype=np.float64)
    thetas = np.array([opt.theta for opt in options], dtype=np.float64)
    ivs = np.array([opt.implied_volatility for opt in options], dtype=np.float64)
    
    profit_surfaces_ponderated = np.array([opt.profit_surface_ponderated for opt in options], dtype=np.float64)
    loss_surfaces_ponderated = np.array([opt.loss_surface_ponderated for opt in options], dtype=np.float64)
    average_pnls = np.array([opt.average_pnl for opt in options], dtype=np.float64)
    sigma_pnls = np.array([opt.sigma_pnl for opt in options], dtype=np.float64)
    
    # ========== PHASE 2: Calculs vectorisés des totaux ==========
    # Long: +values, Short: -values (fait en une opération matricielle)
    total_premium = np.sum(signs * premiums)
    total_delta = np.sum(signs * deltas)
    total_gamma = np.sum(signs * gammas)
    total_vega = np.sum(signs * vegas)
    total_theta = np.sum(signs * thetas)
    total_iv = np.sum(signs * ivs)
    
    # Pour surfaces: long ajoute profit/loss, short inverse
    total_profit_surface = np.sum(np.where(is_long, profit_surfaces_ponderated, -loss_surfaces_ponderated))
    total_loss_surface = np.sum(np.where(is_long, loss_surfaces_ponderated, -profit_surfaces_ponderated))
    total_average_pnl = np.sum(signs * average_pnls)
    total_sigma_pnl = np.sqrt(np.sum(sigma_pnls ** 2))
    
    # ========== FILTRAGE PRÉCOCE (Early Exit pour Optimisation) ==========

    # 1. Premium extrême (filtre le plus discriminant)
    if total_premium > 0.05 or total_premium < -0.1:
        return None
    
    # 2. Delta total extrême
    if abs(total_delta) > 100:
        return None
    
    # 3. Gamma total extrême
    if abs(total_gamma) > 50:
        return None
    if total_average_pnl < 0 : 
        return None
    
    # ========== PHASE 3: P&L Array (construction optimisée) ==========
    prices = options[0].prices
    if prices is None:
        return None  # Stratégie invalide
    total_pnl_array = np.zeros_like(prices, dtype=np.float64)
    
    for i, option in enumerate(options):
        if option.pnl_array is not None:
            total_pnl_array += signs[i] * option.pnl_array
    
    # ========== PHASE 4: Métriques non-linéaires (vectorisées) ==========
    max_profit = float(np.max(total_pnl_array))
    max_loss = float(np.min(total_pnl_array))
    
    # ========== FILTRAGE PHASE 2 (après max_profit/max_loss) ==========
    
    if max_loss < -0.10:
        return None
    
    # Risk/Reward ratio
    if max_loss < 0:
        risk_reward_ratio = abs(max_profit / max_loss)
    elif max_profit > 0:
        risk_reward_ratio = float('inf')
    else:
        risk_reward_ratio = 0.0

    
    # Breakeven points (recherche vectorisée des changements de signe)
    sign_changes = total_pnl_array[:-1] * total_pnl_array[1:] < 0
    breakeven_indices = np.where(sign_changes)[0]
    
    breakeven_points = []
    for idx in breakeven_indices:
        # Interpolation linéaire pour point exact
        price_be = prices[idx] + (prices[idx + 1] - prices[idx]) * (
            -total_pnl_array[idx] / (total_pnl_array[idx + 1] - total_pnl_array[idx])
        )
        breakeven_points.append(float(price_be))
    
    # Profit zone (zones où P&L > 0)
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
    
    # Profit au prix cible (interpolation rapide)
    profit_at_target = float(np.interp(target_price, prices, total_pnl_array))
    
    profit_at_target_pct = 0.0
    if max_profit > 0:
        profit_at_target_pct = (profit_at_target / max_profit) * 100.0
    
    # Calcul des surfaces non pondérées (intégration par la méthode des trapèzes)
    dx = float(np.mean(np.diff(prices)))  # Pas moyen
    
    # Surface de profit: intégration des valeurs positives de P&L
    positive_pnl = np.maximum(total_pnl_array, 0.0)
    surface_profit_nonponderated = float(np.sum(positive_pnl) * dx)
    
    # Surface de perte: intégration des valeurs négatives de P&L (en valeur absolue)
    negative_pnl = np.minimum(total_pnl_array, 0.0)
    surface_loss_nonponderated = float(np.abs(np.sum(negative_pnl)) * dx)
    
    # ========== FILTRAGE PHASE 3 (filtres finaux) ==========
    
    # 10. Profit at target extrême
    if abs(profit_at_target) > 100:
        return None
    
    # 11. Surfaces extrêmes
    if abs(total_profit_surface) > 1000 or abs(total_loss_surface) > 1000:
        return None
    
    # ========== PHASE 5: Informations de la stratégie ==========
    strategy_name = generate_strategy_name(options)
    exp_info = get_expiration_info(options)
    
    # ========== PHASE 6: Construction directe du StrategyComparison ==========
    try:
        strategy = StrategyComparison(
            # Identité
            strategy_name=strategy_name,
            strategy=None,
            target_price=target_price,
            premium=float(total_premium),
            all_options=options,
            
            # Expiration
            expiration_day=exp_info.get('expiration_day'),
            expiration_week=exp_info.get('expiration_week'),
            expiration_month=exp_info.get('expiration_month', 'F'),
            expiration_year=exp_info.get('expiration_year', 6),
            
            # Métriques non-linéaires
            max_profit=max_profit,
            max_loss=max_loss,
            breakeven_points=breakeven_points,
            profit_range=profit_range,
            profit_zone_width=profit_zone_width,
            
            # Surfaces
            surface_profit=surface_profit_nonponderated,
            surface_loss=surface_loss_nonponderated,
            surface_profit_ponderated=float(total_profit_surface),
            surface_loss_ponderated=float(total_loss_surface),
            
            # Métriques pondérées
            average_pnl=float(total_average_pnl),
            sigma_pnl=float(total_sigma_pnl),
            
            # Arrays
            pnl_array=total_pnl_array,
            prices=prices,
            
            # Risk/Reward
            risk_reward_ratio=risk_reward_ratio,
            risk_reward_ratio_ponderated=risk_reward_ratio,
            
            # Greeks
            total_delta=float(total_delta),
            total_gamma=float(total_gamma),
            total_vega=float(total_vega),
            total_theta=float(total_theta),
            avg_implied_volatility=float(total_iv),
            
            # Performance au prix cible
            profit_at_target=profit_at_target,
            profit_at_target_pct=profit_at_target_pct,
            
            # Score (sera calculé par le comparateur)
            score=0.0,
            rank=0
        )
        
        return strategy
        
    except Exception as e:
        print(f"⚠️ Erreur création stratégie: {e}")
        return None
