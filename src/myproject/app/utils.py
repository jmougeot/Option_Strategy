# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

import pandas as pd
from typing import Dict, List
from myproject.strategy.comparison_class import StrategyComparison
from myproject.option.option_class import Option


def prepare_options_data(options: List[Option]) -> Dict[str, List[Option]]:
    """Sépare les calls et puts."""
    calls = [opt for opt in options if opt.option_type == "call"]
    puts = [opt for opt in options if opt.option_type == "put"]

    return {"calls": calls, "puts": puts}


def format_currency(value: float) -> str:
    """Formats a value as currency."""
    if value == float("inf"):
        return "Unlimited"
    return f"{value:.2f}"


def format_percentage(value: float) -> str:
    """Formats a percentage."""
    return f"{value:.1f}%"


def format_expiration_date(month: str, year: int) -> str:
    """
    Formate la date d'expiration à partir du mois Bloomberg et de l'année.

    Args:
        month: Code du mois Bloomberg (F, G, H, K, M, N, Q, U, V, X, Z)
        year: Année (6 = 2026)

    Returns:
        Date formatée (ex: "Jun 2026")
    """
    month_names = {
        "F": "Jan",
        "G": "Feb",
        "H": "Mar",
        "K": "Apr",
        "M": "Jun",
        "N": "Jul",
        "Q": "Aug",
        "U": "Sep",
        "V": "Oct",
        "X": "Nov",
        "Z": "Dec",
    }

    month_name = month_names.get(month, month)
    full_year = 2020 + year

    return f"{month_name} {full_year}"

def strike_list(strike_min: float, strike_max: float, step: float) -> List[float]:
    """
    Génère une liste de strikes avec un step défini
    """
    # Calculer le nombre de steps nécessaires
    num_steps = int(round((strike_max - strike_min) / step)) + 1
    
    # Générer les strikes par multiplication pour éviter l'accumulation d'erreurs
    strike_list = [round(strike_min + i * step, 10) for i in range(num_steps)]
    
    return strike_list

def filter_same_strategies(comparisons: List[StrategyComparison], decimals: int = 4) -> List[StrategyComparison]:
    """
    Filtre les stratégies ayant le même profil P&L.
    
    Args:
        comparisons: Liste de StrategyComparison à filtrer
        decimals: Nombre de décimales pour l'arrondi (4 = tolérance 0.0001)
        
    Returns:
        Liste sans doublons (conserve la première occurrence)
    """
    import numpy as np
    
    vues = set()
    uniques = []
    
    for comp in comparisons:
        # Signature = tuple du pnl_array arrondi
        sig = tuple(np.round(comp.pnl_array, decimals))
        if sig not in vues:
            vues.add(sig)
            uniques.append(comp)
    
    n = len(comparisons) - len(uniques)
    if n > 0:
        print(f"  🔍 {n} doublons éliminés")
    
    return uniques



