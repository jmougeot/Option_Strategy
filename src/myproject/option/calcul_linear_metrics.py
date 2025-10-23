"""
Calcul Complet des Métriques de Stratégie d'Options
===================================================
Fournit une fonction générale pour calculer TOUTES les métriques d'une stratégie :
- Métriques linéaires (coût, Greeks, IV) - calculées par simple addition
- Métriques de surface (profit/loss surfaces) - calculées en sommant les surfaces de chaque leg

Optimisé pour calculer toutes les métriques en une seule fonction.
Utilise les méthodes de la classe Option pour assurer la cohérence des calculs.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
from myproject.option.option_class import Option
import numpy as np


def calculate_linear_metrics(options: List[Option],
                           price_min: Optional[float] = None,
                           price_max: Optional[float] = None,
                           num_points: int = 1000) -> Dict:
    """
    Calcule TOUTES les métriques d'une stratégie d'options en une fois.
    
    Cette fonction est optimisée pour calculer :
    1. Métriques linéaires (coût, Greeks, IV) - en une passe sur les options
    2. Métriques de surface (profit/loss) - par calcul vectorisé si demandé
    
    Args:
        options: Liste d'options constituant la stratégie
        price_min: Prix minimum pour le calcul des surfaces (optionnel)
        price_max: Prix maximum pour le calcul des surfaces (optionnel)
        num_points: Nombre de points pour l'intégration des surfaces
        calculate_surfaces: Si True, calcule aussi les surfaces (plus lent)
        
    Returns:
        Dict avec toutes les métriques (linéaires + surfaces si demandé)
    """
    # Initialiser les accumulateurs
    net_cost = 0.0
    total_premium_paid = 0.0
    total_premium_received = 0.0
    total_loss_surface = 0.0
    total_profit_surface = 0.0
    total_gauss_pnl = 0.0

    
    # Greeks par type
    delta_calls = gamma_calls = vega_calls = theta_calls = 0.0
    delta_puts = gamma_puts = vega_puts = theta_puts = 0.0
    delta_total = gamma_total = vega_total = theta_total = 0.0
    
    # Volatilité implicite
    weighted_iv_sum = 0.0
    total_weight = 0.0
    
    # Compteurs
    n_legs = len(options)
    n_calls = n_puts = n_long = n_short = 0
    
    # Parcourir toutes les options UNE SEULE FOIS
    for option in options:
        # ============ COMPTEURS ============
        if option.option_type == 'call':
            n_calls += 1
        else:
            n_puts += 1
        
        if option.position == 'long':
            n_long += 1
        else:
            n_short += 1
        
        # ============ COÛT NET ============
        leg_cost = option.premium * (-1 if option.position == 'long' else 1)
        net_cost += leg_cost
        
        if option.position == 'long':
            total_premium_paid += option.premium
        else:
            total_premium_received += option.premium
        
        # ============ GREEKS ============
        sign = 1 if option.position == 'long' else -1
        
        delta = (option.delta or 0.0) * sign
        gamma = (option.gamma or 0.0) * sign
        vega = (option.vega or 0.0) * sign
        theta = (option.theta or 0.0) * sign
        loss_surface = (option.loss_surface or 0.0) * sign
        profit_surface = (option.profit_surface or 0.0)* sign

        
        # Accumuler par type
        if option.option_type == 'call':
            delta_calls += delta
            gamma_calls += gamma
            vega_calls += vega
            theta_calls += theta
        else:  # put
            delta_puts += delta
            gamma_puts += gamma
            vega_puts += vega
            theta_puts += theta
        
        # Accumuler total
        delta_total += delta
        gamma_total += gamma
        vega_total += vega
        theta_total += theta
        total_loss_surface += loss_surface
        total_profit_surface += profit_surface 
        
        # ============ VOLATILITÉ IMPLICITE ============
        if option.implied_volatility is not None and option.premium > 0:
            weight = abs(option.premium)
            weighted_iv_sum += option.implied_volatility * weight
            total_weight += weight
    
    # Calculer IV moyenne
    if total_weight > 0:
        avg_iv = weighted_iv_sum / total_weight
    else:
        # Fallback : moyenne simple
        ivs = [opt.implied_volatility for opt in options 
               if opt.implied_volatility is not None]
        avg_iv = sum(ivs) / len(ivs) if ivs else 0.0
    
    # ============ PRÉPARER LE DICTIONNAIRE DE RÉSULTATS ============
    result = {
        # Coût
        'net_cost': net_cost,
        'total_premium_paid': total_premium_paid,
        'total_premium_received': total_premium_received,
        
        # Greeks - Calls
        'delta_calls': delta_calls,
        'gamma_calls': gamma_calls,
        'vega_calls': vega_calls,
        'theta_calls': theta_calls,

        #METRIQUE

        'loss_surface' : total_loss_surface,
        'profit_surface' : total_profit_surface,
        'gauss_x_pnl': total_gauss_pnl,
        
        # Greeks - Puts
        'delta_puts': delta_puts,
        'gamma_puts': gamma_puts,

        'vega_puts': vega_puts,
        'theta_puts': theta_puts,
        
        # Greeks - Total
        'delta_total': delta_total,
        'gamma_total': gamma_total,
        'vega_total': vega_total,
        'theta_total': theta_total,
        
        # Volatilité
        'avg_implied_volatility': avg_iv,
        
        # Compteurs
        'n_legs': n_legs,
        'n_calls': n_calls,
        'n_puts': n_puts,
        'n_long': n_long,
        'n_short': n_short
    }

    return result
