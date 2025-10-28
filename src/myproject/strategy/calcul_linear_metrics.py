"""
Calcul Complet des Métriques de Stratégie d'Options
"""

from typing import List, Dict, Optional, Tuple
from myproject.option.option_class import Option
import numpy as np


def calculate_linear_metrics(
    options: List[Option],
    mixture: Optional[np.ndarray] = None,
    prices: Optional[np.ndarray] = None,
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
    total_gauss_pnl = 0.0
    
    # Accumulateurs pour les métriques basées sur la mixture
    total_average_pnl = 0.0
    total_sigma_pnl = 0.0
    has_mixture_data = False


    
    delta_calls = gamma_calls = vega_calls = theta_calls = 0.0
    delta_puts = gamma_puts = vega_puts = theta_puts = 0.0
    delta_total = gamma_total = vega_total = theta_total = 0.0
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
        # Multiplier par la quantité pour tenir compte des multiples contrats
        quantity = option.quantity if option.quantity is not None else 1
        leg_cost = option.premium * quantity * (-1 if option.position == 'long' else 1)
        premium += leg_cost
                
        # ============ GREEKS ============
        sign = 1 if option.position == 'long' else -1
        
        # Multiplier par la quantité (déjà calculée pour le premium)
        delta = (option.delta or 0.0) * sign * quantity
        gamma = (option.gamma or 0.0) * sign * quantity
        vega = (option.vega or 0.0) * sign * quantity
        theta = (option.theta or 0.0) * sign * quantity
        
        # ============ SURFACES ============
        if option.position == 'long':
            total_profit_surface += (option.profit_surface) * quantity
            total_loss_surface += (option.loss_surface) * quantity
        else:  # short
            total_profit_surface += (option.loss_surface) * quantity  # Inversé pour short
            total_loss_surface += (option.profit_surface) * quantity  # Inversé pour short
        
        # ============ CALCULS BASÉS SUR LA MIXTURE GAUSSIENNE ============
        # Seulement si mixture et prices sont fournis
        if mixture is not None and prices is not None:
            option.mixture = mixture
            # Calculer le P&L à l'expiration pour chaque prix
            option.pnl_array = option._pnl_at_expiry_array(prices)
            option.x = prices
            
            # Calculer les métriques pondérées
            option._pnl_ponderation_array(prices)
            avg_pnl = option._average_pnl()
            sigma_pnl = option._sigma_pnl()
            
            # Récupérer les surfaces calculées avec la mixture
            mixture_loss, mixture_profit = option.calcul_surface()
            
            # Accumuler selon la position
            if option.position == 'long':
                total_profit_surface += mixture_profit * quantity
                total_loss_surface += mixture_loss * quantity
                if avg_pnl is not None:
                    total_average_pnl += avg_pnl * quantity
                if sigma_pnl is not None:
                    # Pour l'écart-type, on cumule les variances puis on prendra la racine
                    total_sigma_pnl += (sigma_pnl ** 2) * (quantity ** 2)
            else:  # short
                # Inverser pour les positions short
                total_profit_surface += mixture_loss * quantity
                total_loss_surface += mixture_profit * quantity
                if avg_pnl is not None:
                    total_average_pnl -= avg_pnl * quantity  # Inverser le signe
                if sigma_pnl is not None:
                    # La variance est toujours positive, même pour short
                    total_sigma_pnl += (sigma_pnl ** 2) * (quantity ** 2)
            
            has_mixture_data = True
                
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
    
    # Calculer IV moyenne
    if total_weight > 0:
        avg_iv = weighted_iv_sum / total_weight
    else:
        # Fallback : moyenne simple
        ivs = [opt.implied_volatility for opt in options 
               if opt.implied_volatility is not None]
        avg_iv = sum(ivs) / len(ivs) if ivs else 0.0
    

    # Calculer l'écart-type total (racine de la somme des variances)
    if has_mixture_data and total_sigma_pnl > 0:
        total_sigma_pnl = np.sqrt(total_sigma_pnl)
    else:
        total_sigma_pnl = 0.0
    
    # ============ PRÉPARER LE DICTIONNAIRE DE RÉSULTATS ============
    result = {
        # Coût
        'premium': premium,
        # Greeks - Calls
        'delta_calls': delta_calls,
        'gamma_calls': gamma_calls,
        'vega_calls': vega_calls,
        'theta_calls': theta_calls,

        # MÉTRIQUES DE SURFACE
        'loss_surface' : total_loss_surface,
        'profit_surface' : total_profit_surface,
        'gauss_x_pnl': total_gauss_pnl,
        
        # MÉTRIQUES BASÉES SUR LA MIXTURE GAUSSIENNE
        'average_pnl': total_average_pnl if has_mixture_data else None,
        'sigma_pnl': total_sigma_pnl if has_mixture_data else None,
        'has_mixture': has_mixture_data,
        
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
