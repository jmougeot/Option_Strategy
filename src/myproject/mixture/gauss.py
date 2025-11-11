import numpy as np


def gaussian(x: np.ndarray, mu: float, sigma: float) -> np.ndarray:
    return (1 / (sigma * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mu) / sigma) ** 2)
