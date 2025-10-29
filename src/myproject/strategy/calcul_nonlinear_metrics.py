"""
Calcul des Métriques Non-Linéaires de Stratégie d'Options
==========================================================
Ce module calcule les métriques qui nécessitent le P&L array complet :
- Max profit, Max loss
- Breakeven points
- Profit zone width
- Risk/Reward ratio
"""

from typing import List, Dict, Optional, Tuple
import numpy as np


def calculate_nonlinear_metrics(
    all_metrics: Dict,
    target_price: float
) -> Dict:
    """
    Calcule les métriques non-linéaires à partir du P&L array.
    
    Args:
        all_metrics: Dictionnaire retourné par calculate_linear_metrics
                     doit contenir 'pnl_array' et 'prices'
        target_price: Prix cible de la stratégie
        
    Returns:
        Dict avec les métriques non-linéaires calculées
    """
    pnl_array = all_metrics.get('pnl_array')
    prices = all_metrics.get('prices')
    
    # Valeurs par défaut si pas de données
    if pnl_array is None or prices is None:
        return {
            'max_profit': 0.0,
            'max_loss': 0.0,
            'breakeven_points': [],
            'profit_zone_width': 0.0,
            'profit_range': (0.0, 0.0),
            'risk_reward_ratio': 0.0,
            'profit_at_target': 0.0,
            'profit_at_target_pct': 0.0
        }
    
    # ========== MAX PROFIT ET MAX LOSS ==========
    max_profit = float(np.max(pnl_array))
    max_loss = float(np.min(pnl_array))
    
    # ========== BREAKEVEN POINTS ==========
    breakeven_points = find_breakeven_points(prices, pnl_array)
    
    # ========== PROFIT ZONE ==========
    profit_range, profit_zone_width = calculate_profit_zone(prices, pnl_array)
    
    # ========== RISK/REWARD RATIO ==========
    risk_reward_ratio = 0.0
    if max_loss < 0:  # Il y a un risque
        risk_reward_ratio = abs(max_profit / max_loss)
    elif max_profit > 0:  # Profit sans risque
        risk_reward_ratio = float('inf')
    
    # ========== PROFIT AU PRIX CIBLE ==========
    profit_at_target = interpolate_pnl_at_price(prices, pnl_array, target_price)
    
    # Pourcentage du max profit
    profit_at_target_pct = 0.0
    if max_profit > 0:
        profit_at_target_pct = (profit_at_target / max_profit) * 100.0
    
    return {
        'max_profit': max_profit,
        'max_loss': max_loss,
        'breakeven_points': breakeven_points,
        'profit_zone_width': profit_zone_width,
        'profit_range': profit_range,
        'risk_reward_ratio': risk_reward_ratio,
        'profit_at_target': profit_at_target,
        'profit_at_target_pct': profit_at_target_pct
    }


def find_breakeven_points(prices: np.ndarray, pnl_array: np.ndarray) -> List[float]:
    """
    Trouve les points de breakeven (où P&L = 0).
    
    Args:
        prices: Array des prix
        pnl_array: Array des P&L correspondants
        
    Returns:
        Liste des prix de breakeven
    """
    breakeven_points = []
    
    # Chercher les changements de signe
    for i in range(len(pnl_array) - 1):
        # Si le P&L change de signe entre deux points
        if pnl_array[i] * pnl_array[i + 1] < 0:
            # Interpolation linéaire pour trouver le point exact
            price_be = prices[i] + (prices[i + 1] - prices[i]) * (
                -pnl_array[i] / (pnl_array[i + 1] - pnl_array[i])
            )
            breakeven_points.append(float(price_be))
        # Si le P&L est exactement 0
        elif abs(pnl_array[i]) < 1e-10:
            breakeven_points.append(float(prices[i]))
    
    return breakeven_points


def calculate_profit_zone(
    prices: np.ndarray,
    pnl_array: np.ndarray
) -> Tuple[Tuple[float, float], float]:
    """
    Calcule la zone de profit (plage de prix où P&L > 0).
    
    Args:
        prices: Array des prix
        pnl_array: Array des P&L correspondants
        
    Returns:
        Tuple ((min_profit_price, max_profit_price), width)
    """
    # Trouver les indices où le P&L est positif
    profitable_indices = np.where(pnl_array > 0)[0]
    
    if len(profitable_indices) == 0:
        return ((0.0, 0.0), 0.0)
    
    # Plage de prix profitable
    min_profit_price = float(prices[profitable_indices[0]])
    max_profit_price = float(prices[profitable_indices[-1]])
    
    # Largeur de la zone
    profit_zone_width = max_profit_price - min_profit_price
    
    return ((min_profit_price, max_profit_price), profit_zone_width)


def interpolate_pnl_at_price(
    prices: np.ndarray,
    pnl_array: np.ndarray,
    target_price: float
) -> float:
    """
    Interpole le P&L à un prix donné.
    
    Args:
        prices: Array des prix
        pnl_array: Array des P&L correspondants
        target_price: Prix pour lequel calculer le P&L
        
    Returns:
        P&L interpolé au prix cible
    """
    # Si le prix cible est en dehors de la plage
    if target_price <= prices[0]:
        return float(pnl_array[0])
    if target_price >= prices[-1]:
        return float(pnl_array[-1])
    
    # Interpolation linéaire
    return float(np.interp(target_price, prices, pnl_array))


def update_metrics_with_nonlinear(
    all_metrics: Dict,
    target_price: float
) -> Dict:
    """
    Met à jour le dictionnaire de métriques avec les calculs non-linéaires.
    
    Args:
        all_metrics: Dictionnaire de calculate_linear_metrics
        target_price: Prix cible
        
    Returns:
        Dictionnaire mis à jour avec toutes les métriques
    """
    nonlinear_metrics = calculate_nonlinear_metrics(all_metrics, target_price)
    
    # Fusionner les deux dictionnaires
    all_metrics.update(nonlinear_metrics)
    
    return all_metrics
