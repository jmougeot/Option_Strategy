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
    total_premium = 0.0
    total_loss_surface = 0.0
    total_profit_surface = 0.0
    total_average_pnl = 0.0
    total_pnl_array: Optional[np.ndarray] = None  # Initialisé à None, sera créé au premier usage
    
    # Accumulateurs pour les métriques basées sur la mixture
    total_average_pnl = 0.0
    total_sigma_pnl = 0.0
    
    # Accumulateur pour le P&L array (stratégie complète)
    total_delta = 0.0
    total_gamma = 0.0
    total_vega = 0.0
    total_theta = 0.0
    total_ivs =0.0
    
    # Parcourir toutes les options UNE SEULE FOIS
    for option in options:
        # ============ COÛT NET ============
        # Multiplier par la quantité pour tenir compte des multiples contrats
        quantity = option.quantity if option.quantity is not None else 1
        leg_cost: float = option.premium * quantity * (-1 if option.position == 'long' else 1)
        total_premium += leg_cost
                
        # ============ GREEKS ============
        sign = 1 if option.position == 'long' else -1
        
        # Multiplier par la quantité (déjà calculée pour le premium)
        delta = (option.delta or 0.0) * sign * quantity
        gamma = (option.gamma or 0.0) * sign * quantity
        vega = (option.vega or 0.0) * sign * quantity
        theta = (option.theta or 0.0) * sign * quantity
        
        
        # ============ SURFACES (stockées dans chaque option) ============
        # Accumuler les surfaces de profit et de perte
        if option.position == 'long':
            total_profit_surface += option.profit_surface
            total_loss_surface += option.loss_surface
            total_average_pnl += option.average_pnl
            total_ivs += option.implied_volatility
            
            #Greeks
            total_delta += delta
            total_gamma += gamma
            total_vega += vega
            total_theta += theta
            
            # Initialiser ou additionner le pnl_array (vérifier que ce n'est pas None)
            if option.pnl_array is not None:
                if total_pnl_array is None:
                    total_pnl_array = option.pnl_array.copy()
                else:
                    total_pnl_array += option.pnl_array
            
            total_sigma_pnl += (option.sigma_pnl ** 2)

        if option.position == 'short':
            total_profit_surface -= option.loss_surface
            total_loss_surface -= option.profit_surface
            total_average_pnl -= option.average_pnl
            total_ivs -= option.implied_volatility

            #Greeks
            total_delta -= delta
            total_gamma -= gamma
            total_vega -= vega
            total_theta -= theta

            
            # Initialiser ou soustraire le pnl_array (vérifier que ce n'est pas None)
            if option.pnl_array is not None:
                if total_pnl_array is None:
                    total_pnl_array = -option.pnl_array.copy()
                else:
                    total_pnl_array -= option.pnl_array
            
            total_sigma_pnl += (option.sigma_pnl ** 2)
    
    total_sigma_pnl = np.sqrt(total_sigma_pnl)
    prices = options[0].prices
    
    if total_pnl_array is None:
        total_pnl_array = np.zeros_like(prices)


    
    # ============ PRÉPARER LE DICTIONNAIRE DE RÉSULTATS ============
    result = {
        # Coût
        'premium': total_premium,

        # MÉTRIQUES DE SURFACE (accumulées depuis les options)
        'loss_surface': total_loss_surface,
        'profit_surface': total_profit_surface,
        
        # MÉTRIQUES PONDÉRÉES PAR MIXTURE (si disponibles)
        'average_pnl': total_average_pnl,
        'sigma_pnl': total_sigma_pnl,

        # Greeks - Total
        'delta_total': total_delta ,
        'gamma_total': total_gamma,
        'vega_total': total_vega,
        'theta_total': total_vega,
        
        # Volatilité
        'avg_implied_volatility': total_ivs,
        'pnl_array': total_pnl_array,
        'prices': prices
    }

    return result
