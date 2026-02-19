"""
Bloomberg Data Importer OFFLINE (Mode Simulation)
==================================================

Simule les donnees Bloomberg pour tester l'application sans connexion.
Genere des options avec des donnees realistes basees sur Black-Scholes.

Activation: 
    - Variable d'environnement OFFLINE_MODE=true
    - Ou modifier le fichier .env a la racine du projet
"""

import os
from pathlib import Path
import numpy as np
from typing import List, Literal, Optional, Tuple
import math

from myproject.option.option_class import Option


# =============================================================================
# FONCTIONS MATHEMATIQUES (remplace scipy.stats.norm)
# =============================================================================

def _norm_cdf(x: float) -> float:
    """Fonction de repartition de la loi normale standard."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _norm_pdf(x: float) -> float:
    """Densite de probabilite de la loi normale standard."""
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


# =============================================================================
# CONFIGURATION
# =============================================================================

def _load_env_file():
    """Charge le fichier .env s'il existe."""
    # Chercher le fichier .env dans les parents
    current = Path(__file__).resolve()
    for parent in [current.parent] + list(current.parents):
        env_file = parent / ".env"
        if env_file.exists():
            with open(env_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ.setdefault(key.strip(), value.strip())
            break

# Charger le .env au chargement du module
_load_env_file()


def is_offline_mode() -> bool:
    """Verifie si le mode offline est active."""
    return os.environ.get("OFFLINE_MODE", "false").lower() == "true"


# =============================================================================
# SIMULATION BLACK-SCHOLES
# =============================================================================

def _black_scholes_price(
    S: float,          # Prix du sous-jacent
    K: float,          # Strike
    T: float,          # Temps jusqu'a expiration (annees)
    r: float,          # Taux sans risque
    sigma: float,      # Volatilite implicite
    option_type: str   # "call" ou "put"
) -> float:
    """Calcule le prix Black-Scholes d'une option."""
    if T <= 0:
        # Option expiree
        if option_type == "call":
            return max(S - K, 0)
        else:
            return max(K - S, 0)
    
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    
    if option_type == "call":
        price = S * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)
    else:  # put
        price = K * math.exp(-r * T) * _norm_cdf(-d2) - S * _norm_cdf(-d1)
    
    return max(price, 0.001)  # Prix minimum


def _black_scholes_greeks(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str
) -> dict:
    """Calcule les Greeks Black-Scholes."""
    if T <= 0:
        return {"delta": 0, "gamma": 0, "vega": 0, "theta": 0, "rho": 0}
    
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    
    # Delta
    if option_type == "call":
        delta = _norm_cdf(d1)
    else:
        delta = _norm_cdf(d1) - 1
    
    # Gamma (meme pour call et put)
    gamma = _norm_pdf(d1) / (S * sigma * math.sqrt(T))
    
    # Vega (meme pour call et put)
    vega = S * _norm_pdf(d1) * math.sqrt(T) / 100  # Divise par 100 pour convention
    
    # Theta
    term1 = -S * _norm_pdf(d1) * sigma / (2 * math.sqrt(T))
    if option_type == "call":
        term2 = -r * K * math.exp(-r * T) * _norm_cdf(d2)
    else:
        term2 = r * K * math.exp(-r * T) * _norm_cdf(-d2)
    theta = (term1 + term2) / 365  # Par jour
    
    # Rho
    if option_type == "call":
        rho = K * T * np.exp(-r * T) * _norm_cdf(d2) / 100
    else:
        rho = -K * T * np.exp(-r * T) * _norm_cdf(-d2) / 100
    
    return {
        "delta": round(delta, 4),
        "gamma": round(gamma, 6),
        "vega": round(vega, 4),
        "theta": round(theta, 4),
        "rho": round(rho, 4)
    }


# =============================================================================
# GÉNÉRATEUR D'OPTIONS SIMULÉES
# =============================================================================

def _generate_simulated_option(
    underlying: str,
    strike: float,
    option_type: str,
    month: str,
    year: int,
    underlying_price: float,
    mixture: Tuple[np.ndarray, np.ndarray, float],
    position: Literal["long", "short"] = "long",
    base_iv: float = 0.20,
    risk_free_rate: float = 0.03,
    days_to_expiry: int = 30,
) -> Option:
    """
    Génère une option simulée avec des données réalistes.
    """
    # Temps jusqu'à expiration en années
    T = days_to_expiry / 365
    
    # Volatilité implicite avec smile (plus élevée loin de la monnaie)
    moneyness = strike / underlying_price
    iv_smile = base_iv * (1 + 0.1 * abs(moneyness - 1))
    
    # Calcul du prix Black-Scholes
    premium = _black_scholes_price(
        S=underlying_price,
        K=strike,
        T=T,
        r=risk_free_rate,
        sigma=iv_smile,
        option_type=option_type
    )
    
    # Calcul des Greeks
    greeks = _black_scholes_greeks(
        S=underlying_price,
        K=strike,
        T=T,
        r=risk_free_rate,
        sigma=iv_smile,
        option_type=option_type
    )
    
    # Créer le ticker
    opt_char = "C" if option_type == "call" else "P"
    ticker = f"{underlying}{month}{year} {opt_char}{strike}"
    
    # Créer l'option
    option = Option(
        option_type=option_type,
        strike=strike,
        premium=round(premium, 4),
        expiration_month=month,  # type: ignore
        expiration_year=year,
        position=position,
        ticker=ticker,
        underlying_symbol=underlying,
        bloomberg_ticker=ticker,
        bid=round(premium * 0.98, 4),
        ask=round(premium * 1.02, 4),
        delta=greeks["delta"],
        gamma=greeks["gamma"],
        vega=greeks["vega"],
        theta=greeks["theta"],
        rho=greeks["rho"],
        implied_volatility=round(iv_smile * 100, 2),  # En pourcentage
        underlying_price=underlying_price,
    )
    
    # Initialiser la mixture et calculer les surfaces
    if mixture is not None:
        option.prices, option.mixture, average_mix = mixture
        option._calcul_all_surface()
        option.average_mix = average_mix
        # Note: intra_life sera calculé après avoir créé toutes les options
    
    return option


# =============================================================================
# FONCTION PRINCIPALE D'IMPORT OFFLINE
# =============================================================================

def import_options_offline(
    mixture: Tuple[np.ndarray, np.ndarray, float],
    underlying: str,
    months: List[str],
    years: List[int],
    strikes: List[float],
    default_position: Literal["long", "short"] = "long",
) -> Tuple[List[Option], float]:

    print("\n🔧 MODE OFFLINE - Simulation des données Bloomberg")
    
    # Prix du sous-jacent simulé (centre de la grille de prix)
    prices_array = mixture[0]
    underlying_price = float(np.median(prices_array))
    
    print(f"  • Sous-jacent: {underlying}")
    print(f"  • Prix simulé: {underlying_price:.2f}")
    print(f"  • Strikes: {len(strikes)} ({min(strikes):.1f} - {max(strikes):.1f})")
    print(f"  • Expirations: {months} x {years}")
    
    options: List[Option] = []
    
    # Jours jusqu'à expiration par mois (approximatif)
    month_to_days = {
        "F": 30, "G": 60, "H": 90, "K": 120,
        "M": 150, "N": 180, "Q": 210, "U": 240,
        "V": 270, "X": 300, "Z": 330
    }
    
    for year in years:
        for month in months:
            days = month_to_days.get(month, 30)
            
            for strike in strikes:
                for opt_type in ["call", "put"]:
                    option = _generate_simulated_option(
                        underlying=underlying,
                        strike=strike,
                        option_type=opt_type,
                        month=month,
                        year=year,
                        underlying_price=underlying_price,
                        mixture=mixture,
                        position=default_position,
                        days_to_expiry=days,
                    )
                    
                    # Filtrer les options avec premium trop faible
                    if option.premium > 0.01:
                        options.append(option)
                        sym = "C" if opt_type == "call" else "P"
                        print(f"  ✓ {sym} {strike}: Premium={option.premium:.4f}, "
                              f"Delta={option.delta:.4f}, IV={option.implied_volatility:.1f}%")
    
    print(f"\n✅ {len(options)} options simulées générées")
    
    # Calculer les prix intra-vie pour toutes les options (avec les strikes comme prix du sous-jacent)
    if options:
        time_to_expiry = month_to_days.get(months[0], 30) / 365 if months else 0.25
        for option in options:
            option.calculate_all_intra_life(all_options=options, time_to_expiry=time_to_expiry)
        print(f"  • Prix intra-vie calculés pour {len(options)} options")
    
    return options, underlying_price
