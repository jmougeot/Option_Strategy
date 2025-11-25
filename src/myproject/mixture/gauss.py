from git import Optional
import numpy as np


def gaussian(x: np.ndarray, mu: float=1, sigma: float=1) -> np.ndarray:
    return (1 / (sigma * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mu) / sigma) ** 2)
