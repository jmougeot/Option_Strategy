import numpy as np
from myproject.option.option_class import Option 
from typing import List, Any, Dict

# ------- Helpers vectorisés -------

def _pack_legs(options: List[Option]):
    """Prépare des vecteurs numpy pour vectoriser le P&L."""
    if not options:
        # Placeholders vides
        return (np.array([]),)*6
    strikes  = np.array([o.strike for o in options], dtype=float)
    premiums = np.array([o.premium for o in options], dtype=float)
    qty      = np.array([float(o.quantity or 1) for o in options], dtype=float)
    signs    = np.array([-1.0 if o.position == "long" else 1.0 for o in options], dtype=float)
    is_call  = np.array([1.0 if o.option_type.lower() == "call" else 0.0 for o in options], dtype=float)
    csize    = np.array([float(o.contract_size or 1) for o in options], dtype=float)
    return strikes, premiums, qty, signs, is_call, csize

def _pnl_at_expiry_vec(options: List[Option], prices: np.ndarray) -> np.ndarray:
    """
    P&L total à l’expiration pour un array de prix 'prices' (shape [P]).
    Convention: long -> intrinsic - premium ; short -> premium - intrinsic.
    """
    if len(options) == 0:
        return np.zeros_like(prices, dtype=float)

    strikes, premiums, qty, signs, is_call, csize = _pack_legs(options)

    # Intrinsèques (broadcast [P, L])
    intrinsic_call = np.maximum(prices[:, None] - strikes[None, :], 0.0)
    intrinsic_put  = np.maximum(strikes[None, :] - prices[:, None], 0.0)
    intrinsic = is_call * intrinsic_call + (1.0 - is_call) * intrinsic_put

    # P&L par leg puis somme
    leg_pnl = signs * (premiums[None, :] - intrinsic) * qty * csize  # [P, L]
    return leg_pnl.sum(axis=1)  # [P]

def _piecewise_knots(options: List[Option], price_min: float, price_max: float) -> np.ndarray:
    """Nœuds où la pente peut changer (strikes + bornes)."""
    if not options:
        return np.array([price_min, price_max], dtype=float)
    strikes = {o.strike for o in options if price_min <= o.strike <= price_max}
    knots = [price_min, *sorted(strikes), price_max]
    # Déduplique au cas où min/max == strike
    return np.array(sorted(set(knots)), dtype=float)

# ------- Fonctions demandées (surfaces = aires) -------

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
