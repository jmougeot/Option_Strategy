import numpy as np 
from myproject.mixture.gauss import gaussian
from scipy.stats import norm

"""
96.5
sigma = 16.31
96.445
P = 9.25
r=0.0404
SFRH6
"""

sigma=0.6474
spot = 129.12

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

def bachelier_call(S0, K, T, sigma_n):
    d = (S0 - K) / (sigma_n * np.sqrt(T))
    C = (S0 - K) * norm.cdf(d) + sigma_n * np.sqrt(T) * norm.pdf(d)
    return C

def bachelier_put(S0, K, T, sigma_n):
    d = (S0 - K) / (sigma_n * np.sqrt(T))
    P = (K - S0) * norm.cdf(-d) + sigma_n * np.sqrt(T) * norm.pdf(d)
    return P

C = black_sholes (sigma , spot, 126, 0.1616438, 2.70)

C_bachelier = bachelier_call(spot, 126, 0.1616438, sigma)

print(C, C_bachelier*100)