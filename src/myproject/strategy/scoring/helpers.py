"""
Helpers pour extraction robuste des valeurs
"""

from typing import Optional
import numpy as np


def safe_value(value: Optional[float], default: float = 0.0) -> float:
    """Extrait une valeur en gérant None/NaN/Inf."""
    if value is None:
        return default
    if not np.isfinite(value):
        return default
    return float(value)


def safe_ratio(
    numerator: Optional[float], denominator: Optional[float], default: float = 0.0
) -> float:
    """Calcule un ratio en gérant None/0/Inf."""
    num = safe_value(numerator, 0.0)
    den = safe_value(denominator, 0.0)

    if den == 0.0 or not np.isfinite(den):
        return default

    ratio = num / den
    return ratio if np.isfinite(ratio) else default
