"""
Mixture utilities for scenario-based probability distributions.
This module doesn't depend on Streamlit.
"""

import numpy as np
from typing import Tuple
from myproject.mixture.mixture_gaussienne import mixture
from myproject.mixture.gauss import gaussian, asymetric_gaussian
from myproject.app.data_types import ScenarioData


def create_mixture_from_scenarios(
    scenarios: ScenarioData,
    price_min: float,
    price_max: float,
    num_points: int = 50,
) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    Crée une mixture gaussienne à partir des scénarios définis par l'utilisateur.
    Supporte les gaussiennes symétriques et asymétriques.

    Args:
        scenarios: ScenarioData avec centers, std_devs, std_devs_r, weights, asymmetric
        price_min: Prix minimum de la grille
        price_max: Prix maximum de la grille
        num_points: Nombre de points dans la grille

    Returns:
        (prices, mixture_normalized, average): Grille de prix, mixture gaussienne normalisée, et moyenne
    """
    # Extraire les paramètres des scénarios
    centers = scenarios.centers
    std_devs = scenarios.std_devs
    std_devs_r = scenarios.std_devs_r
    proba = scenarios.weights
    is_asymmetric = getattr(scenarios, 'asymmetric', False)

    if is_asymmetric:
        # Mode asymétrique: utiliser asymetric_gaussian
        prices, mix = mixture(
            price_min=price_min,
            price_max=price_max,
            num_points=num_points,
            proba=proba,
            mus=centers,
            sigmas=std_devs,
            f=asymetric_gaussian,
            sigmas_r=std_devs_r,
        )
    else:
        # Mode symétrique: utiliser gaussian standard
        prices, mix = mixture(
            price_min=price_min,
            price_max=price_max,
            num_points=num_points,
            proba=proba,
            mus=centers,
            sigmas=std_devs,
            f=gaussian,
        )
    average = float(np.average(prices, weights=mix))
    
    return prices, mix, average
