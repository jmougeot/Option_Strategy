"""
Utilitaires pour la manipulation des options
=============================================
Fonctions communes pour convertir et manipuler les options.
"""

from typing import Dict, List, Optional, Literal, Any, Tuple
import math
from myproject.option.option_class import Option

def get_expiration_key(day: int, month: str, year: int) -> str:
    """
    Crée une clé unique pour identifier une date d'expiration.
    
    Args:
        day: Jour d'expiration
        month: Mois d'expiration (format lettre: F, G, H, etc.)
        year: Année d'expiration
    
    Returns:
        Clé au format 'YYYY-MONTH-DD'
    """
    return f"{year}-{month}-{day:02d}"


def get_expiration_info(options: List[Option]) -> Dict[str, Any]:
    """
    Extrait les informations d'expiration communes d'une liste d'options.
    
    Args:
        options: Liste d'options
    
    Returns:
        Dict avec expiration_month, expiration_year, expiration_day, expiration_week
    """
    if not options:
        return {
            'expiration_month': 'F',
            'expiration_year': 6,
            'expiration_day': None,
            'expiration_week': None
        }
    
    first_option = options[0]
    return {
        'expiration_month': first_option.expiration_month,
        'expiration_year': first_option.expiration_year,
        'expiration_day': first_option.expiration_day,
        'expiration_week': first_option.expiration_week
    }

def dict_to_option(option_dict: Dict, position: Literal['long', 'short'] = 'long', quantity: int = 1) -> Option:
    """
    Convertit un dictionnaire d'option (format Bloomberg) en objet Option.
    
    Args:
        option_dict: Dictionnaire avec les données de l'option
        position: 'long' ou 'short'
        quantity: Quantité
    
    Returns:
        Objet Option ou None si données invalides
    """
    try:
        # Extraire la date d'expiration
        day = option_dict.get('day_of_expiration', 1)
        expiration_month = option_dict.get('month_of_expiration', 1)
        expiration_year = option_dict.get('year_of_expiration', 2025)
        
        return Option(
            # Obligatoires
            option_type=option_dict.get('option_type', 'call'),
            strike=float(option_dict.get('strike', 0.0)),
            premium=float(option_dict.get('premium', 0.0)),
            expiration_month= expiration_month,
            expiration_year=expiration_year,
            expiration_day= None,

            # Position
            quantity=quantity,
            position=position,
            
            # Identification
            ticker=option_dict.get('bloomberg_ticker'),
            underlying_symbol=option_dict.get('symbol'),
            
            # Prix
            bid=option_dict.get('bid'),
            ask=option_dict.get('ask'),
            last=option_dict.get('last'),
            mid=option_dict.get('mid'),
            
            # Greeks
            delta=option_dict.get('delta'),
            gamma=option_dict.get('gamma'),
            vega=option_dict.get('vega'),
            theta=option_dict.get('theta'),
            rho=option_dict.get('rho'),
            
            # Volatilité
            implied_volatility=option_dict.get('implied_volatility'),
            
            # Liquidité
            open_interest=option_dict.get('open_interest'),
            volume=option_dict.get('volume'),
            
            # Sous-jacent
            underlying_price=option_dict.get('underlying_price'),
            
            # Bloomberg
            bloomberg_ticker=option_dict.get('bloomberg_ticker'),
            timestamp=option_dict.get('timestamp')
        )
    except Exception as e:
        print(f"⚠️ Erreur conversion dict->Option: {e}")
        return Option.empyOption()


def calculate_greeks_from_options(options: List[Option]) -> Dict[str, float]:
    """
    Calcule les Greeks totaux à partir d'une liste d'objets Option.
    Prend en compte la position (long/short) et la quantité.
    
    Args:
        options: Liste d'objets Option
    
    Returns:
        Dict avec delta, gamma, vega, theta totaux
    """
    total_delta = 0.0
    total_gamma = 0.0
    total_vega = 0.0
    total_theta = 0.0
    
    for opt in options:
        # Multiplicateur selon la position
        multiplier =  (1 if opt.position == 'long' else -1)
        
        total_delta += (opt.delta or 0.0) * multiplier
        total_gamma += (opt.gamma or 0.0) * multiplier
        total_vega += (opt.vega or 0.0) * multiplier
        total_theta += (opt.theta or 0.0) * multiplier
    
    return {
        'delta': total_delta,
        'gamma': total_gamma,
        'vega': total_vega,
        'theta': total_theta
    }


def calculate_greeks_by_type(options: List[Option]) -> Dict[str, Dict[str, float]]:
    """
    Calcule les Greeks séparés par type (calls vs puts).
    
    Args:
        options: Liste d'objets Option
    
    Returns:
        Dict avec 'calls', 'puts', et 'total'
    """
    calls = [opt for opt in options if opt.option_type == 'call']
    puts = [opt for opt in options if opt.option_type == 'put']
    
    greeks_calls = calculate_greeks_from_options(calls)
    greeks_puts = calculate_greeks_from_options(puts)
    greeks_total = calculate_greeks_from_options(options)
    
    return {
        'calls': greeks_calls,
        'puts': greeks_puts,
        'total': greeks_total
    }


def calculate_avg_implied_volatility(options: List[Option]) -> float:
    """
    Calcule la volatilité implicite moyenne pondérée par les primes.
    
    Args:
        options: Liste d'objets Option
    
    Returns:
        IV moyenne pondérée
    """
    total_premium = 0.0
    weighted_iv = 0.0
    
    for opt in options:
        if opt.implied_volatility is not None and opt.premium > 0:
            weight = abs(opt.premium)
            weighted_iv += opt.implied_volatility * weight
            total_premium += weight
    
    if total_premium > 0:
        return weighted_iv / total_premium
    
    # Fallback: moyenne simple
    ivs = [opt.implied_volatility for opt in options if opt.implied_volatility is not None]
    return sum(ivs) / len(ivs) if ivs else 0.0


def calculate_strategy_pnl(options: List[Option], price: float) -> float:
    """
    Calcule le P&L d'une stratégie d'options à un prix donné à l'expiration.
    
    Args:
        options: Liste d'options constituant la stratégie
        price: Prix du sous-jacent
    
    Returns:
        P&L total de la stratégie
    """
    total_pnl = 0.0
    
    for opt in options:
        # Coût initial (négatif si long, positif si short)
        cost = opt.premium * (-1 if opt.position == 'long' else 1)
        
        # Valeur intrinsèque à l'expiration
        if opt.option_type == 'call':
            intrinsic_value = max(0, price - opt.strike)
        else:  # put
            intrinsic_value = max(0, opt.strike - price)
        
        # P&L pour cette option (long: on reçoit la valeur, short: on la paye)
        if opt.position == 'long':
            option_pnl = intrinsic_value + cost
        else:  # short
            option_pnl = cost - intrinsic_value
        
        total_pnl += option_pnl
    
    return total_pnl


def calculate_profit_surface(options: List[Option], 
                         price_min: float, 
                         price_max: float, 
                         num_points: int = 1000) -> float:
    """
    Calcule l'aire sous la courbe de P&L positive (zone de profit) entre prix_min et prix_max.
    Utilise la méthode des trapèzes pour l'intégration numérique.
    
    Args:
        options: Liste d'options constituant la stratégie
        price_min: Prix minimum du sous-jacent
        price_max: Prix maximum du sous-jacent
        num_points: Nombre de points pour l'intégration (plus = plus précis)
    
    Returns:
        Aire de profit (surface positive sous la courbe P&L)
    """
    if price_min >= price_max:
        return 0.0
    
    # Générer les points de prix
    step = (price_max - price_min) / (num_points - 1)
    profit_surface = 0.0
    
    for i in range(num_points - 1):
        price1 = price_min + i * step
        price2 = price_min + (i + 1) * step
        
        # Calculer P&L aux deux points
        pnl1 = calculate_strategy_pnl(options, price1)
        pnl2 = calculate_strategy_pnl(options, price2)
        
        # Ne compter que les parties positives (profit)
        pnl1_positive = max(0, pnl1)
        pnl2_positive = max(0, pnl2)
        
        # Aire du trapèze pour ce segment
        trapezoid_area = (pnl1_positive + pnl2_positive) * step / 2
        profit_surface += trapezoid_area
    
    return profit_surface


def calculate_loss_surface(options: List[Option], 
                       price_min: float, 
                       price_max: float, 
                       num_points: int = 100) -> float:
    """
    Calcule l'aire sous la courbe de P&L négative (zone de perte) entre prix_min et prix_max.
    Utilise la méthode des trapèzes pour l'intégration numérique.

    Returns:
        Aire de perte (valeur absolue de la surface négative sous la courbe P&L)
    """
    if price_min >= price_max:
        return 0.0
    
    # Générer les points de prix
    step = (price_max - price_min) / (num_points - 1)
    loss_surface = 0.0
    
    for i in range(num_points - 1):
        price1 = price_min + i * step
        price2 = price_min + (i + 1) * step
        
        # Calculer P&L aux deux points
        pnl1 = calculate_strategy_pnl(options, price1)
        pnl2 = calculate_strategy_pnl(options, price2)
        
        # Ne compter que les parties négatives (perte), en valeur absolue
        pnl1_negative = abs(min(0, pnl1))
        pnl2_negative = abs(min(0, pnl2))
        
        # Aire du trapèze pour ce segment
        trapezoid_area = (pnl1_negative + pnl2_negative) * step / 2
        loss_surface += trapezoid_area
    
    return loss_surface


def calculate_pnl_areas(options: List[Option],
                       price_min: float,
                       price_max: float,
                       num_points: int = 1000) -> Dict[str, float]:
    """
    Calcule à la fois l'aire de profit et l'aire de perte d'une stratégie.
    
    Returns:
        Dict avec 'profit_surface', 'loss_surface', et 'net_area'
    """
    profit_surface = calculate_profit_surface(options, price_min, price_max, num_points)
    loss_surface = calculate_loss_surface(options, price_min, price_max, num_points)
    
    return {
        'profit_surface': profit_surface,
        'loss_surface': loss_surface,
        'net_area': profit_surface - loss_surface,
        'profit_loss_ratio': profit_surface / loss_surface if loss_surface > 0 else float('inf')
    }


def gaussian_pdf(x: float, mean: float, std_dev: float) -> float:
    """
    Calcule la densité de probabilité d'une distribution gaussienne.
    
    Args:
        x: Point où évaluer la densité
        mean: Moyenne (centre) de la gaussienne
        std_dev: Écart-type de la gaussienne
    
    Returns:
        Densité de probabilité au point x
    """
    variance = std_dev ** 2
    coefficient = 1.0 / math.sqrt(2 * math.pi * variance)
    exponent = -((x - mean) ** 2) / (2 * variance)
    return coefficient * math.exp(exponent)


def calculate_gaussian_weighted_profit(options: List[Option],
                                       price_min: float,
                                       price_max: float,
                                       center_strike: float,
                                       num_points: int = 1000) -> float:
    """
    Calcule l'aire sous min(0, f(x), g(x)) où:
    - f(x) est la densité gaussienne centrée sur center_strike
    - g(x) est le P&L de la stratégie
    
    La gaussienne est calibrée pour que ses points à 0.1% se situent à price_min ou price_max
    (selon lequel est le plus éloigné du centre).
    
    Cette métrique représente l'espérance de profit pondérée par la probabilité que le
    prix du sous-jacent soit proche du strike central.
    
    Args:
        options: Liste d'options constituant la stratégie
        price_min: Prix minimum du sous-jacent
        price_max: Prix maximum du sous-jacent
        center_strike: Strike central (centre de la gaussienne)
        num_points: Nombre de points pour l'intégration
    
    Returns:
        Aire pondérée par la gaussienne (surface_gauss)
    """
    if price_min >= price_max:
        return 0.0
    
    # Déterminer la distance maximale du centre aux bornes
    dist_to_min = abs(center_strike - price_min)
    dist_to_max = abs(center_strike - price_max)
    max_distance = max(dist_to_min, dist_to_max)
    
    # Calibrer l'écart-type pour que P(|X - center| > max_distance) = 0.001
    # Pour une gaussienne: P(|X - μ| > k*σ) = 0.001 => k ≈ 3.29 (percentile 99.9%)
    # Donc: max_distance = 3.29 * std_dev => std_dev = max_distance / 3.29
    std_dev = max_distance / 3.29
    
    # Calculer la hauteur maximale de la gaussienne (au centre)
    max_gaussian_height = gaussian_pdf(center_strike, center_strike, std_dev)
    
    # Intégration numérique avec méthode des trapèzes
    step = (price_max - price_min) / (num_points - 1)
    weighted_area = 0.0
    
    for i in range(num_points - 1):
        price1 = price_min + i * step
        price2 = price_min + (i + 1) * step
        
        # Calculer P&L aux deux points
        pnl1 = calculate_strategy_pnl(options, price1)
        pnl2 = calculate_strategy_pnl(options, price2)
        
        # Calculer densité gaussienne aux deux points
        gauss1 = gaussian_pdf(price1, center_strike, std_dev)
        gauss2 = gaussian_pdf(price2, center_strike, std_dev)
        
        # Calculer min(0, pnl, gauss) aux deux points
        # On prend seulement la partie positive du P&L, limitée par la gaussienne
        value1 = min(max(0, pnl1), gauss1) if pnl1 > 0 else 0
        value2 = min(max(0, pnl2), gauss2) if pnl2 > 0 else 0
        
        # Aire du trapèze pour ce segment
        trapezoid_area = (value1 + value2) * step / 2
        weighted_area += trapezoid_area
    
    return weighted_area


def calculate_all_surfaces(options: List[Option],
                          price_min: float,
                          price_max: float,
                          center_strike: float,
                          num_points: int = 1000) -> Dict[str, float]:
    """
    Calcule toutes les surfaces (profit, loss, et gaussienne) d'une stratégie.
    
    Args:
        options: Liste d'options constituant la stratégie
        price_min: Prix minimum du sous-jacent
        price_max: Prix maximum du sous-jacent
        center_strike: Strike central pour la gaussienne
        num_points: Nombre de points pour l'intégration
    
    Returns:
        Dict avec 'profit_surface', 'loss_surface', 'surface_gauss', et ratios
    """
    profit_surface = calculate_profit_surface(options, price_min, price_max, num_points)
    loss_surface = calculate_loss_surface(options, price_min, price_max, num_points)
    surface_gauss = calculate_gaussian_weighted_profit(options, price_min, price_max, center_strike, num_points)
    
    return {
        'profit_surface': profit_surface,
        'loss_surface': loss_surface,
        'surface_gauss': surface_gauss,
        'net_area': profit_surface - loss_surface,
        'profit_loss_ratio': profit_surface / loss_surface if loss_surface > 0 else float('inf'),
        'gauss_profit_ratio': surface_gauss / profit_surface if profit_surface > 0 else 0
    }

