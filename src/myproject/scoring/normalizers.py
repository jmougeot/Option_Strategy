"""
Fonctions de normalisation pour les métriques de scoring
"""

from typing import List, Tuple
import numpy as np


def normalize_max(values: List[float]) -> Tuple[float, float]:
    """
    Normalisation simple avec maximum.
    Garde les 0 (valeur informative), filtre uniquement None/NaN/Inf.
    """
    valid_values = [v for v in values if np.isfinite(v)]
    if not valid_values:
        return 0.0, 1.0
    max_val = max(valid_values)
    return 0.0, max_val if max_val != 0.0 else 1.0


def normalize_min_max(values: List[float]) -> Tuple[float, float]:
    """
    Normalisation min-max.
    Garde les 0 (valeur informative), filtre uniquement None/NaN/Inf.
    """
    valid_values = [v for v in values if np.isfinite(v)]
    if not valid_values:
        return 0.0, 1.0
    min_val = min(valid_values)
    max_val = max(valid_values)
    if max_val == min_val:
        return min_val, min_val + 1.0  # Éviter division par zéro
    return min_val, max_val


def normalize_count(values: List[float]) -> Tuple[float, float]:
    """
    Normalise une métrique de compte (ex: nombre de puts).
    Garde les 0, filtre None/NaN/Inf; retourne (min, max) pour compatibilité.
    """
    valid_values = [v for v in values if np.isfinite(v)]
    if not valid_values:
        return 0.0, 1.0
    min_val = min(valid_values)
    max_val = max(valid_values)
    if max_val == min_val:
        return min_val, min_val + 1.0  # éviter division par zéro
    return min_val, max_val
