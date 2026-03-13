"""
Utilitaires de gestion des échéances Bloomberg
===============================================
Constantes pour manipuler les mois et années d'expiration.
"""

from typing import List, Tuple

# Liste ordonnée des mois Bloomberg
# F=Jan, G=Feb, H=Mar, J=Apr, K=May, M=Jun, N=Jul, Q=Aug, U=Sep, V=Oct, X=Nov, Z=Dec
MONTH_ORDER = ["F", "G", "H", "J", "K", "M", "N", "Q", "U", "V", "X", "Z"]

# Mois trimestriels pour le roll (H=Mar, M=Jun, U=Sep, Z=Dec)
QUARTERLY_MONTHS = ["H", "M", "U", "Z"]

# Mapping des mois Bloomberg vers les noms complets
MONTH_NAMES = {
    "F": "January",
    "G": "February",
    "H": "March",
    "J": "April",
    "K": "May",
    "M": "June",
    "N": "July",
    "Q": "August",
    "U": "September",
    "V": "October",
    "X": "November",
    "Z": "December",
}


def build_surface_months(
    month: str,
    year: int,
    n_quarterly: int = 4,
) -> List[Tuple[str, int]]:
    """
    Construit automatiquement les expirations trimestrielles pour la
    calibration de surface SVI.
    """
    qi = MONTH_ORDER.index(month) // 3          # quartile 0..3
    center = year * 4 + qi                       # position absolue
    n_before = (n_quarterly - 1) // 2

    result: List[Tuple[str, int]] = []
    for i in range(n_quarterly):
        abs_idx = center - n_before + i
        y, q = divmod(abs_idx, 4)
        if y >= 0:
            result.append((QUARTERLY_MONTHS[q], y))
    return result

