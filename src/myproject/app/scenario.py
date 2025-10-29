from myproject.app.widget import ScenarioData
from myproject.mixture.mixture_gaussienne import mixture
from myproject.mixture.gauss import gaussian
import numpy as np
from typing import Callable, Tuple, Optional 


def create_mixture_from_scenarios(
    scenarios: Optional[ScenarioData],
    price_min: float,
    price_max: float,
    num_points: int = 50,
    target_price : float = 100,
    f = gaussian 
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Crée une mixture gaussienne à partir des scénarios définis par l'utilisateur.
    
    Utilise les fonctions du module mixture_gaussienne pour créer une distribution
    de probabilité à partir de plusieurs gaussiennes pondérées.
    
    Args:
        scenarios: ScenarioData avec centers, std_devs, weights
        price_min: Prix minimum de la grille
        price_max: Prix maximum de la grille
        num_points: Nombre de points dans la grille
        
    Returns:
        (prices, mixture_normalized): Grille de prix et mixture gaussienne normalisée
    """
    if not scenarios or not scenarios.centers:
        # Retourner une mixture uniforme par défaut
        sigma = (price_min-price_max)/4
        prices = np.linspace(price_min, price_max, num_points)
        step = len (prices)/num_points 
        uniform_mixture = f(prices, target_price, sigma)*step
        return prices, uniform_mixture
    
    # Extraire les paramètres des scénarios
    centers = scenarios.centers
    std_devs = scenarios.std_devs
    proba = scenarios.weights
    
    # Utiliser la fonction mixture du module mixture_gaussienne
    prices, mix = mixture(
        price_min=price_min,
        price_max=price_max,
        num_points=num_points,
        proba=proba,
        mus=centers,
        sigmas=std_devs,
        f=f  # Fonction gaussienne du module gauss
    )
    return prices, mix

