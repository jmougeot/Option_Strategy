import numpy as np

def gaussian_array(price_min: float,
                   price_max: float,
                   center_price: float,
                   num_points: int = 500) -> tuple[np.ndarray, np.ndarray]:
    """
    Génère une gaussienne discrète sur un intervalle donné.

    Returns:
        (prices, gauss) : 
            - prices : np.ndarray des prix (shape [num_points])
            - gauss  : np.ndarray des valeurs de la densité (shape [num_points])
    """
    std_dev = max( abs(center_price - price_min), abs(center_price - price_max))

    if price_min >= price_max:
        raise ValueError("price_min doit être strictement inférieur à price_max.")
    if std_dev <= 0:
        raise ValueError("std_dev doit être strictement positif.")

    # Discrétisation de l'intervalle
    prices = np.linspace(price_min, price_max, num_points, dtype=float)

    # Formule de la densité normale
    # gauss(x) = (1 / (σ√(2π))) * exp(-(x - μ)^2 / (2σ^2))
    gauss = (1.0 / (std_dev * np.sqrt(2 * np.pi))) * np.exp(
        -0.5 * ((prices - center_price) / std_dev) ** 2
    )

    # Normalisation optionnelle pour que l'aire sous la courbe = 1
    gauss /= np.trapz(gauss, prices)

    return prices, gauss
