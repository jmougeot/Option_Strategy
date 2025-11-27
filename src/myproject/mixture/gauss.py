from git import Optional
import numpy as np


def gaussian(x: np.ndarray, mu: float=1, sigma: float=1) -> np.ndarray:
    return (1 / (sigma * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mu) / sigma) ** 2)

def asymetric_gaussian(x: np.ndarray, mu: float, sigma_l: float, sigma_r: float) -> np.ndarray:
    result = np.zeros_like(x, dtype=float)
    
    # Partie gauche (x < mu)
    mask_left = x < mu
    result[mask_left] = (2 / ((sigma_l +sigma_r)* np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x[mask_left] - mu) / sigma_l) ** 2)
    
    # Partie droite (x >= mu)
    mask_right = x >= mu
    result[mask_right] = (2 / ((sigma_r + sigma_l)* np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x[mask_right] - mu) / sigma_r) ** 2)
    
    return result
