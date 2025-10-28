import numpy as np
from typing import Callable, Sequence, Tuple
from myproject.mixture.gauss import gaussian

# f doit être du type: f(x, mu, sigma) -> np.ndarray (même shape que x)
def mixture(
    price_min: float,
    price_max: float,
    num_points: int,
    proba: Sequence[float],
    mus: Sequence[float],
    sigmas: Sequence[float],
    f: Callable[[np.ndarray, float, float], np.ndarray],
) -> Tuple[np.ndarray, np.ndarray]:
    
    x = np.linspace(price_min, price_max, num_points)

    w = np.asarray(proba, dtype=float)

    mix = sum((wi * f(x, mu, sigma) for wi, mu, sigma in zip(w, mus, sigmas)), np.zeros_like(x, dtype=float))
    return (x, mix)

