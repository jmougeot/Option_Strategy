"""
Utilitaires pour la manipulation des options
=============================================
Fonctions communes pour convertir et manipuler les options.
"""

from typing import Dict, List, Optional, Literal, Any
from datetime import datetime
from myproject.option.option_class import Option


def dict_to_option(option_dict: Dict, position: Literal['long', 'short'] = 'long', quantity: int = 1) -> Optional[Option]:
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
        month = option_dict.get('month_of_expiration', 1)
        year = option_dict.get('year_of_expiration', 2025)
        
        return Option(
            # Obligatoires
            option_type=option_dict.get('option_type', 'call'),
            strike=float(option_dict.get('strike', 0.0)),
            premium=float(option_dict.get('premium', 0.0)),
            day_of_expirition=day,
            month_of_expiration=month,
            year_of_expiration=year,
            
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
        return None


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
        multiplier = opt.quantity * (1 if opt.position == 'long' else -1)
        
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
            weight = abs(opt.premium * opt.quantity)
            weighted_iv += opt.implied_volatility * weight
            total_premium += weight
    
    if total_premium > 0:
        return weighted_iv / total_premium
    
    # Fallback: moyenne simple
    ivs = [opt.implied_volatility for opt in options if opt.implied_volatility is not None]
    return sum(ivs) / len(ivs) if ivs else 0.0


def get_expiration_info(options: List[Option]) -> Dict[str, Any]:
    """
    Extrait les informations d'expiration commune.
    
    Args:
        options: Liste d'objets Option
    
    Returns:
        Dict avec expiration_date, month, year
    """
    if not options:
        return {'expiration_date': None, 'month': None, 'year': None}
    
    # Prendre la première option
    opt = options[0]
    
    try:
        # Mapping des codes Bloomberg de mois en nombres
        month_map = {
            'F': 1, 'G': 2, 'H': 3, 'K': 5,
            'M': 6, 'N': 7, 'Q': 8, 'U': 9,
            'V': 10, 'X': 11, 'Z': 12
        }
        
        month_num = month_map.get(opt.month_of_expiration, 1)
        day_num = int(opt.day_of_expirition) if isinstance(opt.day_of_expirition, str) else opt.day_of_expirition
        
        # Construire la date
        expiry = datetime(
            year=opt.year_of_expiration,
            month=month_num,
            day=day_num
        )
        
        return {
            'expiration_date': expiry,
            'month': expiry.strftime('%B'),  # Nom complet du mois
            'year': expiry.year
        }
    except (AttributeError, ValueError, KeyError):
        return {'expiration_date': None, 'month': None, 'year': None}
