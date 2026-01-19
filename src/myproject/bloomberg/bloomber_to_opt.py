from typing import Literal, Optional, cast, Tuple

from myproject.option.option_class import Option
import numpy as np

# Type pour les mois valides
MonthCode = Literal["F", "G", "H", "K", "M", "N", "Q", "U", "V", "X", "Z"]


def _safe_float(value, default: float = 0.0) -> float:
    """Convertit en float en gérant None/NaN."""
    if value is None:
        return default
    try:
        result = float(value)
        return result if np.isfinite(result) else default
    except (ValueError, TypeError):
        return default


def _safe_int(value, default: int = 0) -> int:
    """Convertit en int en gérant None."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


# Mapping des mois Bloomberg vers les noms complets
MONTH_NAMES = {
    "F": "January",
    "G": "February",
    "H": "March",
    "K": "April",
    "M": "June",
    "N": "July",
    "Q": "August",
    "U": "September",
    "V": "October",
    "X": "November",
    "Z": "December",
}

# Mapping des mois vers les dates d'expiration (3ème mercredi du mois)
MONTH_EXPIRY_DAY = {
    "F": 15,
    "G": 19,
    "H": 19,
    "K": 16,
    "M": 18,
    "N": 16,
    "Q": 20,
    "U": 17,
    "V": 15,
    "X": 19,
    "Z": 17,
}


def get_expiration_components(month: str, year: int) -> tuple[MonthCode, int, str]:
    """
    Calcule les composants d'expiration pour une option.

    Args:
        month: Code du mois Bloomberg (F, G, H, etc.)
        year: Année sur 1 chiffre (6 = 2026)

    Returns:
        (month_code, year, day_str)
    """
    day = MONTH_EXPIRY_DAY.get(month, 18)
    return cast(MonthCode, month), year, str(day)


def create_option_from_bloomberg(
    ticker: str,
    underlying: str,
    strike: float,
    month: str,
    year: int,
    option_type_str: str,
    bloomberg_data: dict,
    position: Literal["long", "short"] = "long",
    mixture: Optional[Tuple[np.ndarray, np.ndarray]] = None,
) -> Option:
    """
    Crée un objet Option directement depuis les données Bloomberg.

    Args:
        ticker: Ticker Bloomberg
        underlying: Symbole du sous-jacent
        strike: Prix d'exercice
        month: Code du mois d'expiration
        year: Année d'expiration (1 chiffre)
        option_type_str: "call" ou "put"
        bloomberg_data: Données brutes Bloomberg
        position: 'long' ou 'short'
        quantity: Quantité
        price_min: Prix min pour surfaces
        price_max: Prix max pour surfaces
        calculate_surfaces: Si True, calcule les surfaces
        num_points: Nombre de points pour les surfaces

    Returns:
        Objet Option
    """
    try:
        month_code, exp_year, exp_day = get_expiration_components(month, year)

        # Extraire les valeurs avec gestion des None
        premium = _safe_float(bloomberg_data.get("premium"))
        bid = _safe_float(bloomberg_data.get("bid"))
        ask = _safe_float(bloomberg_data.get("ask"))
        delta = _safe_float(bloomberg_data.get("delta"))
        gamma = _safe_float(bloomberg_data.get("gamma"))
        vega = _safe_float(bloomberg_data.get("vega"))
        theta = _safe_float(bloomberg_data.get("theta"))
        rho = _safe_float(bloomberg_data.get("rho"))
        iv = _safe_float(bloomberg_data.get("implied_volatility"))
        oi = _safe_int(bloomberg_data.get("open_interest"))
        vol = _safe_int(bloomberg_data.get("volume"))
        underlying_price = _safe_float(bloomberg_data.get("underlying_price"))

        # Vérifier que les données essentielles sont présentes
        if premium == 0.0 and bid == 0.0 and ask == 0.0:
            # Option sans prix valide, retourner une option vide
            return Option.empyOption()

        # Créer l'option directement
        option = Option(
            # Obligatoires
            option_type=option_type_str,
            strike=float(strike),
            premium=premium,
            expiration_month=month_code,
            expiration_year=exp_year,
            expiration_day=exp_day,
            # Position
            position=position,
            # Identification
            ticker=ticker,
            underlying_symbol=underlying,
            bloomberg_ticker=ticker,
            # Prix
            bid=bid,
            ask=ask,
            # Greeks
            delta=delta,
            gamma=gamma,
            vega=vega,
            theta=theta,
            rho=rho,
            # Volatilité
            implied_volatility=iv,
            # Liquidité
            open_interest=oi,
            volume=vol,
            # Sous-jacent
            underlying_price=underlying_price,
            # Timestamp
        )

        # Initialiser la mixture et calculer les surfaces si les paramètres sont fournis
        if mixture is not None:
            # 1. Stocker la mixture et la grille de prix
            option.prices, option.mixture = mixture

            # 2. Calculer toutes les surfaces et métriques
            option._calcul_all_surface()

        return option

    except Exception as e:
        print(f"⚠️ Erreur création Option: {e}")
        return Option.empyOption()
