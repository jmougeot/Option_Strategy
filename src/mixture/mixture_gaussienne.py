import numpy as np
from typing import Callable, Optional, Sequence, Tuple


def mixture(
    price_min: float,
    price_max: float,
    num_points: int,
    proba: Sequence[float],
    mus: Sequence[float],
    sigmas: Sequence[float],
    f: Callable,
    sigmas_r: Optional[Sequence[float]] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Crée une mixture de distributions.
    
    Args:
        price_min, price_max: Bornes de la grille
        num_points: Nombre de points
        proba: Poids de chaque composante
        mus: Centres de chaque composante
        sigmas: Écarts-types (ou sigma_l si asymétrique)
        f: Fonction de distribution (gaussian ou asymetric_gaussian)
        sigmas_r: Écarts-types droits (pour asymétrique uniquement)
    
    Returns:
        (x, mix): Grille et mixture normalisée
    """
    x = np.linspace(price_min, price_max, num_points)
    step = (price_max - price_min) / num_points
    w = np.asarray(proba, dtype=float)

    if sigmas_r is None:
        # Mode symétrique: f(x, mu, sigma)
        mix = sum(
            (wi * f(x, mu, sigma) * step for wi, mu, sigma in zip(w, mus, sigmas)),
            np.zeros_like(x, dtype=float),
        )
    else:
        # Mode asymétrique: f(x, mu, sigma_l, sigma_r)
        mix = sum(
            (wi * f(x, mu, sigma_l, sigma_r) * step 
             for wi, mu, sigma_l, sigma_r in zip(w, mus, sigmas, sigmas_r)),
            np.zeros_like(x, dtype=float),
        )
    
    return (x, mix)
