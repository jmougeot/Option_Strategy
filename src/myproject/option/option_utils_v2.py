import numpy as np
from myproject.option.option_class import Option 
from typing import List, Tuple, Dict

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
