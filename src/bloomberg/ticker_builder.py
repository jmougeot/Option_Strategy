"""
Bloomberg Ticker Builder
========================
Construction intelligente des tickers Bloomberg pour options.

Supporte:
- Options sur actions (equity): "AAPL 12/20/24 C150 Equity"
- Options sur indices: "SPX 12/20/24 P4500 Index"
- Options EURIBOR (taux): "ER H5 C97.50 Comdty"

Auteur: BGC Trading Desk
Date: 2025-10-16
"""

from datetime import date, datetime
from typing import Literal, Optional


# Codes mensuels Bloomberg (pour les futures et options de taux)
MONTH_CODES = {
    1: 'F',   # Janvier
    2: 'G',   # Février
    3: 'H',   # Mars
    4: 'J',   # Avril
    5: 'K',   # Mai
    6: 'M',   # Juin
    7: 'N',   # Juillet
    8: 'Q',   # Août
    9: 'U',   # Septembre
    10: 'V',  # Octobre
    11: 'X',  # Novembre
    12: 'Z'   # Décembre
}


def get_suffix(underlying: str) -> str:
    """
    Détermine le suffixe Bloomberg selon le type d'actif.
    
    Règles:
    - Si contient 'ER' (EURIBOR) → 'Comdty' (commodity/futures)
    - Si finit par 'X' ou contient plusieurs majuscules → 'Index' (indice)
    - Sinon → 'Equity' (action)
    
    Args:
        underlying: Symbole du sous-jacent (ex: "AAPL", "SPX", "ER")
    
    Returns:
        Suffixe Bloomberg: 'Equity', 'Index', ou 'Comdty'
    
    Exemples:
        >>> get_suffix("AAPL")
        'Equity'
        >>> get_suffix("SPX")
        'Index'
        >>> get_suffix("ER")
        'Comdty'
    """
    underlying = underlying.upper()
    
    # Cas EURIBOR et futures de taux
    if underlying in ['ER', 'EURIBOR'] or underlying.startswith('ER'):
        return 'Comdty'
    
    # Cas indices (finissent souvent par X: SPX, NDX, VIX, etc.)
    # Liste explicite des indices courants
    indices = ['SPX', 'NDX', 'RUT', 'VIX', 'DJX', 'OEX', 'XSP']
    if underlying in indices or underlying.endswith('X'):
        return 'Index'
    
    # Cas par défaut: actions (AAPL, MSFT, GOOGL, etc.)
    return 'Equity'


def build_equity_option_ticker(
    underlying: str,
    expiry: date,
    option_type: Literal['C', 'P', 'CALL', 'PUT'],
    strike: float,
    suffix: Optional[str] = None
) -> str:
    """
    Construit un ticker d'option sur action ou indice.
    
    Format Bloomberg: "{UNDERLYING} {MM/DD/YY} {C/P} {STRIKE} {Suffix}"
    
    Args:
        underlying: Symbole (ex: "AAPL", "SPX")
        expiry: Date d'expiration
        option_type: 'C'/'CALL' pour call, 'P'/'PUT' pour put
        strike: Prix d'exercice (ex: 150.0)
        suffix: Suffixe Bloomberg (auto-détecté si None)
    
    Returns:
        Ticker complet (ex: "AAPL 12/20/24 C150 Equity")
    
    Exemples:
        >>> build_equity_option_ticker("AAPL", date(2024, 12, 20), "C", 150.0)
        'AAPL 12/20/24 C150 Equity'
        
        >>> build_equity_option_ticker("SPX", date(2024, 12, 20), "PUT", 4500.0)
        'SPX 12/20/24 P4500 Index'
    """
    # Normaliser le type d'option
    opt_type = option_type[0].upper()  # 'C' ou 'P'
    
    # Formater la date MM/DD/YY
    expiry_str = expiry.strftime("%m/%d/%y")
    
    # Formater le strike (entier si possible, sinon 2 décimales)
    if strike == int(strike):
        strike_str = f"{int(strike)}"
    else:
        strike_str = f"{strike:.2f}"
    
    # Déterminer le suffixe si non fourni
    if suffix is None:
        suffix = get_suffix(underlying)
    
    # Construire le ticker
    ticker = f"{underlying.upper()} {expiry_str} {opt_type}{strike_str} {suffix}"
    return ticker


def build_euribor_option_ticker(
    expiry: date,
    option_type: Literal['C', 'P', 'CALL', 'PUT'],
    strike: float
) -> str:
    """
    Construit un ticker d'option EURIBOR (futures de taux).
    
    Format Bloomberg: "ER{MonthCode}{Year} {C/P}{Strike} Comdty"
    
    Détails:
    - ER = symbole EURIBOR 3 mois sur Eurex
    - MonthCode = lettre pour le mois (H=Mars, M=Juin, U=Sept, Z=Déc)
    - Year = dernière chiffre de l'année (5 pour 2025, 6 pour 2026)
    - Strike = prix du future (ex: 97.50 = taux implicite 2.50%)
    
    Format final: ERH6 C97.50 Comdty (SANS espace entre ER et H6)
    
    Args:
        expiry: Date d'expiration du future
        option_type: 'C'/'CALL' pour call, 'P'/'PUT' pour put
        strike: Strike en points de future (ex: 97.50)
    
    Returns:
        Ticker EURIBOR complet (ex: "ERH5 C97.50 Comdty")
    
    Exemples:
        >>> build_euribor_option_ticker(date(2025, 3, 15), "C", 97.50)
        'ERH5 C97.50 Comdty'
        
        >>> build_euribor_option_ticker(date(2025, 6, 15), "PUT", 98.00)
        'ERM5 P98.00 Comdty'
    """
    # Normaliser le type
    opt_type = option_type[0].upper()
    
    # Récupérer le code du mois
    month_code = MONTH_CODES[expiry.month]
    
    # Dernière chiffre de l'année
    year_code = str(expiry.year)[-1]
    
    # Formater le strike (2 décimales)
    strike_str = f"{strike:.2f}"
    
    # Construire le ticker (SANS espace entre ER et le code)
    # Format correct: ERH6 C97.50 Comdty (pas ER H6 C97.50 Comdty)
    ticker = f"ER{month_code}{year_code}{opt_type} {strike_str} Comdty"
    return ticker


def build_option_ticker(
    underlying: str,
    expiry: date,
    option_type: Literal['C', 'P', 'CALL', 'PUT'],
    strike: float,
    is_euribor: bool = False
) -> str:
    """
    Fonction générique qui route vers le bon builder selon le type d'actif.
    
    Args:
        underlying: Symbole du sous-jacent (ex: "AAPL", "SPX", "ER")
        expiry: Date d'expiration
        option_type: 'C'/'CALL' ou 'P'/'PUT'
        strike: Prix d'exercice
        is_euribor: Forcer le format EURIBOR (auto-détecté si False)
    
    Returns:
        Ticker Bloomberg complet
    
    Exemples:
        >>> build_option_ticker("AAPL", date(2024, 12, 20), "C", 150.0)
        'AAPL 12/20/24 C150 Equity'
        
        >>> build_option_ticker("ER", date(2025, 3, 15), "C", 97.50)
        'ER H5 C97.50 Comdty'
    """
    # Auto-détection EURIBOR
    if not is_euribor:
        is_euribor = underlying.upper() in ['ER', 'EURIBOR']
    
    if is_euribor:
        return build_euribor_option_ticker(expiry, option_type, strike)
    else:
        return build_equity_option_ticker(underlying, expiry, option_type, strike)


def parse_euribor_expiry_code(code: str) -> date:
    """
    Convertit un code d'expiry EURIBOR en date.
    
    Format: "{MonthCode}{Year}" (ex: "H5" = Mars 2025)
    
    Args:
        code: Code d'expiry (ex: "H5", "M5", "U5", "Z5")
    
    Returns:
        Date d'expiration (15ème jour du mois par convention)
    
    Exemples:
        >>> parse_euribor_expiry_code("H5")
        datetime.date(2025, 3, 15)
        
        >>> parse_euribor_expiry_code("Z5")
        datetime.date(2025, 12, 15)
    """
    month_code = code[0].upper()
    year_digit = int(code[1])
    
    # Trouver le mois correspondant
    month = None
    for m, mc in MONTH_CODES.items():
        if mc == month_code:
            month = m
            break
    
    if month is None:
        raise ValueError(f"Code de mois invalide: {month_code}")
    
    # Construire l'année (supposer 2020-2029 pour les années 0-9)
    year = 2020 + year_digit
    
    # Convention: 15ème jour du mois (date typique d'expiration)
    return date(year, month, 15)


if __name__ == "__main__":
    # Tests de construction de tickers
    print("=== Test Equity Options ===")
    print(build_option_ticker("AAPL", date(2024, 12, 20), "C", 150.0))
    print(build_option_ticker("MSFT", date(2024, 12, 20), "P", 300.0))
    
    print("\n=== Test Index Options ===")
    print(build_option_ticker("SPX", date(2024, 12, 20), "C", 4500.0))
    print(build_option_ticker("NDX", date(2024, 12, 20), "P", 15000.0))
    
    print("\n=== Test EURIBOR Options ===")
    print(build_option_ticker("ER", date(2025, 3, 15), "C", 97.50))
    print(build_option_ticker("ER", date(2025, 6, 15), "P", 98.00))
    print(build_option_ticker("ER", date(2025, 9, 15), "C", 97.75))
    print(build_option_ticker("ER", date(2025, 12, 15), "P", 98.25))
