import numpy as np 
from scipy.stats import norm
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import pandas as pd
from typing import Literal

"""
Calcul des prix avec black and Sholes et bachelier 
"""

sigma=0.58

def black_sholes(sigma, S0, K, T, r, ) -> float:
    """
    Calcule du prix d'une optiona avec Black and Sholes.

    Args:
        sigma: volatilité implicité
        S0: prix spot de l'actif
        K: strike
        T: maturité (en année)
        r: taux sans risque (continu)
    """
    d1 =  (np.log(S0/K) + (r + 0.5*sigma**2)*T)/(sigma*np.sqrt(T))
    d2 = d1 - sigma*np.sqrt(T)
    C = S0*norm.cdf(d1) - K*np.exp(-r*T)*norm.cdf(d2)
    return C

def bachelier_call(S0, K, T, sigma_n) -> float:
    d = (S0 - K) / (sigma_n * np.sqrt(T))
    C = (S0 - K) * norm.cdf(d) + sigma_n * np.sqrt(T) * norm.pdf(d)
    return C

def bachelier_put(S0, K, T, sigma_n) -> float:
    d = (S0 - K) / (sigma_n * np.sqrt(T))
    P = (K - S0) * norm.cdf(-d) + sigma_n * np.sqrt(T) * norm.pdf(d)
    return P


def create_heatmap_option_prices(
    spot: float,
    strike: float,
    option_type: Literal["call", "put"] = "call",
    vol_range: tuple = (0.01, 0.80),
    vol_steps: int = 30,
    days_to_expiry_range: tuple = (1, 180),
    days_steps: int = 30,
) -> go.Figure:
    """
    Crée une heatmap du prix des options en fonction de la volatilité et l'expiration.
    Utilise le modèle de Bachelier (Normal model).
    
    Args:
        spot: Prix spot actuel du sous-jacent
        strike: Strike de l'option
        option_type: "call" ou "put"
        vol_range: Tuple (min_vol, max_vol) pour la plage de volatilité
        vol_steps: Nombre de steps de volatilité à tester
        
    Returns:
        Figure Plotly avec la heatmap interactive
    """
    
    # Créer les ranges
    volatilities = np.linspace(vol_range[0], vol_range[1], vol_steps)
    days_to_expiry = np.linspace(days_to_expiry_range[0], days_to_expiry_range[1], days_steps)
    
    # Matrice des prix
    prices = np.zeros((len(days_to_expiry), len(volatilities)))
    
    # Remplir la matrice
    for i, days in enumerate(days_to_expiry):
        T = days / 365  # Convertir en années
        for j, vol in enumerate(volatilities):
            if option_type.lower() == "call":
                prices[i, j] = bachelier_call(spot, strike, T, vol)
            else:
                prices[i, j] = bachelier_put(spot, strike, T, vol)
    
    # Créer la heatmap
    fig = go.Figure(data=go.Heatmap(
        z=prices,
        x=np.round(volatilities, 4),
        y=np.round(days_to_expiry, 0).astype(int),
        colorscale="RdYlGn",
        hovertemplate="<b>Volatilité:</b> %{x}<br><b>Jours à expiration:</b> %{y}<br><b>Prix:</b> %{z:.4f}<extra></extra>",
    ))
    
    # Mise en forme
    option_label = "CALL" if option_type.lower() == "call" else "PUT"
    fig.update_layout(
        title=f"Heatmap Prix {option_label} | Spot={spot} | Strike={strike}",
        xaxis_title="Volatilité Normale (σ)",
        yaxis_title="Jours à Expiration",
        height=600,
        width=1000,
        font=dict(size=12),
    )
    
    return fig


# Exemple d'utilisation
if __name__ == "__main__":
    # Test : CALL 96.5 avec spot=96.445
    fig = create_heatmap_option_prices(
        spot=96.445,
        strike=96.5,
        option_type="call",
        vol_range=(0.01, 0.80),
        vol_steps=40,
        days_to_expiry_range=(1, 180),
        days_steps=40,
    )
    fig.show()

    