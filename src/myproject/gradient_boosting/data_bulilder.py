import numpy as np
import pandas as pd
from myproject.strategy.comparison_class import StrategyComparison
from typing import List, Tuple
from sklearn.model_selection import train_test_split
from lightgbm import LGBMRegressor
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error


def calculate_strategy_score(strategy: StrategyComparison) -> float:
    """
    Calcule un score continu pour une stratégie (0-100).
    Plus le score est élevé, meilleure est la stratégie.
    
    Args:
        strategy: Stratégie à évaluer
        
    Returns:
        Score entre 0 et 100
    """
    score = 0.0

    if strategy.call_count > 2:
        score -= 50
    elif strategy.call_count > 1 :
        score -= 20

    # 1. Score de profit attendu (0-25 points)
    avg_pnl = strategy.average_pnl or 0
    score += min(avg_pnl * 500, 30)  # Bonus pour profit positif
    max_loss = abs(strategy.max_loss or 0)

    if max_loss > 0.10:
        score -= 5
    elif max_loss > 0.15:
        score -= 15
    elif max_loss > 0.20:
        score -= 30
    elif max_loss > 0.50:
        score -= 50
    else:
        score -= min(max_loss * 50, 10) 
        
    
    zone_width = strategy.profit_zone_width or 0
    score += min(zone_width * 50, 10)
    sigma = strategy.sigma_pnl or 0

    if sigma > 0.05:
        score -= 7

    premium = strategy.premium
    if premium < 0:
        score += min(abs(premium) * 100, 8)
    elif premium < -0.10:
        score -= 15
    elif premium > 0.05:
        score -= 10
    elif premium > 0.1:
        score -= 25

    delta = strategy.total_delta
    if abs(delta) > 100:
        score -= 30

    strategy_name_lower = strategy.strategy_name.lower()
    if 'fly' in strategy_name_lower or 'butterfly' in strategy_name_lower or 'condor' in strategy_name_lower:
        score += 5

    return max(0, min(score, 100))


def data_frame_bloomberg(strategies: List[StrategyComparison]) -> Tuple[pd.DataFrame, np.ndarray]:
    """
    Convertit une liste de stratégies en DataFrame de features et array de labels.
    Args:
        strategies: Liste de StrategyComparison
    Returns:
        Tuple (X, y) ou X est le DataFrame des features et y les labels
    """

    feature_list = []
    labels = []
    
    feature_names = [
        'original',
        'underlying',
        'month_expiracy',
        'year_expiray',
        'normalized',
        'strategy_type',
        'option_type',
        'strikes',
        'REF O',
        'REF C',
        'DELTA',
        'what is closed',
        'CLOSE SIZE',
        'CLOSE PRICE',
        'CLOSE DATE',
        'call_count',
        'average_pnl',
        'num_breakevens',
        'max_profit',
        'max_loss',
        'premium',
        'profit_at_target',
        'profit_range_min',
        'profit_range_max',
        'sigma_pnl',
        'surface_loss_ponderated',
        'surface_profit_ponderated',
        'surface_loss',
        'surface_profit',
        'risk_reward_ratio',
        'total_delta',
        'total_theta',
        'total_gamma',
        'total_vega',
        'profit_zone_width',
        'max_loss_penalty',
        'IV',
        'is_trade_monitor_data'
    ]
    
    for s in strategies:
        feats = []
        # Informations de base
        feats.append(s.strategy_name if hasattr(s, 'strategy_name') else None)  # original
        feats.append(getattr(s, 'underlying', None))  # underlying
        feats.append(s.expiration_month if hasattr(s, 'expiration_month') else None)  # month_expiracy
        feats.append(s.expiration_year if hasattr(s, 'expiration_year') else None)  # year_expiray
        feats.append(None)  # normalized (pas d'attribut direct)
        feats.append(getattr(s, 'strategy_type', None))  # strategy_type
        feats.append(getattr(s, 'option_type', None))  # option_type
        feats.append(str([opt.strike for opt in s.all_options]) if hasattr(s, 'all_options') else None)  # strikes
        feats.append(getattr(s, 'ref_o', None))  # REF O
        feats.append(getattr(s, 'ref_c', None))  # REF C
        feats.append(getattr(s, 'delta_trade', None))  # DELTA
        feats.append(getattr(s, 'what_is_closed', None))  # what is closed
        feats.append(getattr(s, 'close_size', None))  # CLOSE SIZE
        feats.append(getattr(s, 'close_price_trade', None))  # CLOSE PRICE
        feats.append(getattr(s, 'close_date', None))  # CLOSE DATE
        feats.append(s.call_count if s.call_count else None)
        feats.append(s.average_pnl if s.average_pnl else None)
        feats.append(len(s.breakeven_points) if s.breakeven_points else 0)
        feats.append(s.max_profit if s.max_profit else None)
        feats.append(s.max_loss if s.max_loss else None)
        feats.append(s.premium if s.premium else None)
        feats.append(s.profit_at_target if s.profit_at_target else None)
        feats.append(s.profit_range[0] if s.profit_range else None)
        feats.append(s.profit_range[1] if s.profit_range else None)
        feats.append(s.sigma_pnl if s.sigma_pnl else None)
        feats.append(s.surface_loss_ponderated if s.surface_loss_ponderated else None)
        feats.append(s.surface_profit_ponderated if s.surface_profit_ponderated else None)
        feats.append(s.surface_loss if s.surface_loss else None)
        feats.append(s.surface_profit if s.surface_profit else None)
        feats.append(s.risk_reward_ratio_ponderated if s.risk_reward_ratio_ponderated else None)
        feats.append(s.total_delta if s.total_delta else None)
        feats.append(s.total_theta if s.total_theta else None)
        feats.append(s.total_gamma if s.total_gamma else None)
        feats.append(s.total_vega if s.total_vega else None)
        feats.append(s.profit_zone_width if s.profit_zone_width else None)
        feats.append(s.max_loss if s.max_loss else None)  # max_loss_penalty
        feats.append(s.avg_implied_volatility if s.avg_implied_volatility else None)
        feats.append(getattr(s, 'is_trade_monitor_data', False))  # is_trade_monitor_data
        
        feature_list.append(feats)
        
        # Calculer le score continu (0-100) au lieu de label binaire
        score = calculate_strategy_score(s)
        labels.append(score)
    
    X = pd.DataFrame(feature_list, columns=feature_names)
    y = np.array(labels)  # Scores continus entre 0 et 100
    
    return X, y 
