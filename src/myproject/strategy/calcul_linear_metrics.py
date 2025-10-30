"""
Calcul Complet des Métriques de Stratégie d'Options
"""

from typing import List, Dict, Optional, Tuple
from myproject.option.option_class import Option
import numpy as np


def calculate_linear_metrics(
    options: List[Option],
) -> Dict:
    """
    Calcule TOUTES les métriques d'une stratégie d'options en une fois.
    
    Cette fonction est optimisée pour calculer :
    1. Métriques linéaires (coût, Greeks, IV) - en une passe sur les options
    2. Métriques de surface (profit/loss) - par calcul vectorisé si demandé
    3. Métriques pondérées par mixture gaussienne (si fournie)
    
    Args:
        options: Liste d'options constituant la stratégie
        mixture: Distribution de probabilité gaussienne (optionnel)
                 Si fournie, calcule les métriques pondérées
        prices: Grille de prix correspondant à la mixture (optionnel)
                Requis si mixture est fourni
        min_price: Prix minimum pour les calculs (optionnel)
        max_price: Prix maximum pour les calculs (optionnel)
        
    Returns:
        Dict avec toutes les métriques (linéaires + pondérées par mixture si applicable)
        
    Examples:
        # Sans mixture (calculs classiques)
        metrics = calculate_linear_metrics([call, put])
        
        # Avec mixture gaussienne
        prices = np.linspace(80, 120, 500)
        mixture = create_gaussian_mixture(prices, centers=[100], std_devs=[5])
        metrics = calculate_linear_metrics([call, put], mixture=mixture, prices=prices)
    """
    # Initialiser les accumulateurs
    premium = 0.0
    total_loss_surface = 0.0
    total_profit_surface = 0.0
    total_average_pnl = 0.0
    total_pnl_array: np.ndarray = np.array([])
    
    # Accumulateurs pour les métriques basées sur la mixture
    total_average_pnl = 0.0
    total_sigma_pnl = 0.0
    has_mixture = False  # Indicateur si au moins une option a une mixture
    
    # Accumulateur pour le P&L array (stratégie complète)

    delta_calls = gamma_calls = vega_calls = theta_calls = 0.0
    delta_puts = gamma_puts = vega_puts = theta_puts = 0.0
    delta_total = gamma_total = vega_total = theta_total = 0.0
    weighted_iv_sum = 0.0
    total_weight = 0.0
    
    # Compteurs
    n_legs = len(options)
    
    # Parcourir toutes les options UNE SEULE FOIS
    for option in options:
        # ============ COÛT NET ============
        # Multiplier par la quantité pour tenir compte des multiples contrats
        quantity = option.quantity if option.quantity is not None else 1
        leg_cost: float = option.premium * quantity * (-1 if option.position == 'long' else 1)
        premium += leg_cost
                
        # ============ GREEKS ============
        sign = 1 if option.position == 'long' else -1
        
        # Multiplier par la quantité (déjà calculée pour le premium)
        delta = (option.delta or 0.0) * sign * quantity
        gamma = (option.gamma or 0.0) * sign * quantity
        vega = (option.vega or 0.0) * sign * quantity
        theta = (option.theta or 0.0) * sign * quantity
        
                
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
        
        # ============ VOLATILITÉ IMPLICITE ============
        if option.implied_volatility is not None and option.premium > 0:
            # Pondérer par le premium total (premium * quantity)
            weight = abs(option.premium * quantity)
            weighted_iv_sum += option.implied_volatility * weight
            total_weight += weight
        
        # ============ SURFACES (stockées dans chaque option) ============
        # Accumuler les surfaces de profit et de perte
        if option.position == 'long':
            total_profit_surface += option.profit_surface
            total_loss_surface += option.loss_surface
            total_average_pnl +=option.average_pnl
            total_pnl_array += option.pnl_array
            total_sigma_pnl += (option.sigma_pnl ** 2)


        if option.position == 'short':
            total_profit_surface -= option.loss_surface
            total_loss_surface -= option.profit_surface
            total_average_pnl -=option.average_pnl
            total_pnl_array -= option.pnl_array
            total_sigma_pnl += (option.sigma_pnl ** 2)

    
    total_sigma_pnl = np.sqrt(total_sigma_pnl)
    prices = options[0].prices
    ivs = [opt.implied_volatility for opt in options ]
    


    
    # ============ PRÉPARER LE DICTIONNAIRE DE RÉSULTATS ============
    result = {
        # Coût
        'premium': premium,
        
        # Greeks - Calls
        'delta_calls': delta_calls,
        'gamma_calls': gamma_calls,
        'vega_calls': vega_calls,
        'theta_calls': theta_calls,

        # MÉTRIQUES DE SURFACE (accumulées depuis les options)
        'loss_surface': total_loss_surface,
        'profit_surface': total_profit_surface,
        
        # MÉTRIQUES PONDÉRÉES PAR MIXTURE (si disponibles)
        'average_pnl': total_average_pnl,
        'sigma_pnl': total_sigma_pnl,
        'has_mixture': has_mixture,
        
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
        'avg_implied_volatility': ivs,
        'pnl_array': total_pnl_array,
        'prices': prices
    }

    return result
