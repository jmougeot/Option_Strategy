# ===============================================================
# Module qui encadre tout l'utilisation du modèle de bachelier
# ===============================================================


import numpy as np
from scipy.stats import norm
from typing import Optional


def bachelier_price(F: float, K: float, sigma: float, T: float, is_call: bool) -> float:
    """
    Calcule le prix d'une option avec le modèle de Bachelier (normal model).
    
    Formules:
    - Call: V = (F - K) * Phi(d) + sigma * sqrt(T) * phi(d)
    - Put:  V = (K - F) * Phi(-d) + sigma * sqrt(T) * phi(d)
    
    où d = (F - K) / (sigma * sqrt(T))
    
    Args:
        F: Prix forward du sous-jacent
        K: Strike de l'option
        sigma: Volatilité normale (en unités absolues, pas en %)
        T: Temps jusqu'à expiration (en années)
        is_call: True pour call, False pour put
        
    Returns:
        Prix de l'option
    """
    if T <= 0:
        # À expiration, valeur intrinsèque
        if is_call:
            return max(F - K, 0.0)
        else:
            return max(K - F, 0.0)
    
    if sigma <= 0:
        # Sans volatilité, valeur intrinsèque actualisée
        if is_call:
            return max(F - K, 0.0)
        else:
            return max(K - F, 0.0)
    
    sigma_sqrt_T = sigma * np.sqrt(T)
    d = (F - K) / sigma_sqrt_T
    
    if is_call:
        price = (F - K) * norm.cdf(d) + sigma_sqrt_T * norm.pdf(d)
    else:
        price = (K - F) * norm.cdf(-d) + sigma_sqrt_T * norm.pdf(d)
    
    return max(price, 0.0)



def bachelier_implied_vol(F: float, K: float, market_price: float, T: float, is_call: bool) -> float:
    """
    Calcule la volatilité normale implicite via le modèle de Bachelier.
    Résout: bachelier_price(F, K, sigma, T, is_call) = market_price
    
    Args:
        F: Prix forward du sous-jacent
        K: Strike de l'option
        market_price: Prix de marché de l'option
        T: Temps jusqu'à expiration (en années)
        is_call: True pour call, False pour put
        
    Returns:
        Volatilité normale implicite (sigma), ou 0.0 si échec
    """
    if T <= 0 or market_price <= 0:
        return 0.0
    
    intrinsic = max(F - K, 0.0) if is_call else max(K - F, 0.0)
    if market_price <= intrinsic + 1e-10:
        return 0.0
    
    from scipy.optimize import brentq
    
    def objective(sigma):
        return bachelier_price(F, K, sigma, T, is_call) - market_price
    
    try:
        max_vol = market_price * np.sqrt(2 * np.pi / T) * 10
        vol = brentq(objective, 1e-8, max(max_vol, 1000.0), xtol=1e-10, maxiter=200)
        return float(vol)  # type: ignore[arg-type]
    except Exception:
        return 0.0



def bachelier_price_vec(F: np.ndarray, K: float, sigma: float, T: float, is_call: bool) -> np.ndarray:
    """
    Version vectorisée de bachelier_price.
    F peut être un array numpy de prix forward.
    """
    if T <= 0 or sigma <= 0:
        if is_call:
            return np.maximum(F - K, 0.0)
        else:
            return np.maximum(K - F, 0.0)

    sigma_sqrt_T = sigma * np.sqrt(T)
    d = (F - K) / sigma_sqrt_T

    if is_call:
        prices = (F - K) * norm.cdf(d) + sigma_sqrt_T * norm.pdf(d)
    else:
        prices = (K - F) * norm.cdf(-d) + sigma_sqrt_T * norm.pdf(d)

    return np.maximum(prices, 0.0)


def breeden_litzenberger_density(
    strikes: np.ndarray,
    call_prices: np.ndarray,
    price_grid: np.ndarray,
    risk_free_rate: float = 0.0,
    time_to_expiry: float = 1.0
) -> Optional[np.ndarray]:
    """
    Extrait la densité risque-neutre q_T(K) via la formule de Breeden-Litzenberger.
    
    La formule est : q_T(K) = e^{rT} * ∂²C/∂K²(K)
    
    Args:
        strikes: Array des strikes triés (croissants)
        call_prices: Array des prix des calls correspondants
        price_grid: Grille de prix sur laquelle interpoler la densité
        risk_free_rate: Taux sans risque annuel
        time_to_expiry: Temps jusqu'à expiration (en années)
        
    Returns:
        Densité risque-neutre q_T(x) sur la grille price_grid, ou None si échec
    """
    if len(strikes) < 4:
        # Pas assez de strikes pour calculer une dérivée seconde fiable
        return None
    
    # Trier par strike
    sort_idx = np.argsort(strikes)
    K = strikes[sort_idx]
    C = call_prices[sort_idx]
    
    # Filtrer les prix valides (> 0)
    valid_mask = C > 0
    if np.sum(valid_mask) < 4:
        return None
    
    K = K[valid_mask]
    C = C[valid_mask]
    
    # Interpolation cubique des prix de calls
    try:
        from scipy.interpolate import CubicSpline as CS
        cs = CS(K, C)
        
        # Dérivée seconde = d²C/dK²
        # CubicSpline permet de calculer les dérivées directement
        d2C_dK2 = cs(price_grid, 2)  # dérivée seconde
        
        # Formule de Breeden-Litzenberger: q_T(K) = e^{rT} * d²C/dK²
        discount_factor = np.exp(risk_free_rate * time_to_expiry)
        q_T = discount_factor * d2C_dK2
        
        # La densité doit être positive
        q_T = np.maximum(q_T, 0.0)
        
        # Normaliser pour que l'intégrale = 1
        dx = float(np.mean(np.diff(price_grid))) if len(price_grid) > 1 else 1.0
        total_mass = np.sum(q_T) * dx
        if total_mass > 1e-10:
            q_T = q_T / total_mass
        else:
            return None
            
        return q_T
        
    except Exception as e:
        print(f"⚠️ Erreur Breeden-Litzenberger: {e}")
        return None
