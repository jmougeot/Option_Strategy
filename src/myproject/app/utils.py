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


def create_payoff_diagram(
    comparisons: List[StrategyComparison], target_price: float, mixture: tuple
):
    """
    Crée un diagramme P&L interactif pour toutes les stratégies avec mixture gaussienne optionnelle

    Args:
        comparisons: Liste des stratégies à afficher
        target_price: Prix cible pour la référence verticale
        mixture: Tuple (prices, probabilities) pour afficher la distribution gaussienne (optionnel)

    Returns:
        Figure Plotly avec les courbes P&L et optionnellement la mixture
    """
    # Import ici pour éviter circular import
    from myproject.app.payoff_diagram import create_payoff_diagram as create_payoff_full

    # Déléguer à la fonction complète dans payoff_diagram.py
    return create_payoff_full(comparisons, target_price, mixture)


def create_comparison_table(comparisons: List[StrategyComparison]) -> pd.DataFrame:
    """Crée un DataFrame pour l'affichage des comparaisons avec TOUS les critères de scoring."""

    data = []
    for idx, comp in enumerate(comparisons, 1):
        data.append(
            {
                "Rang": idx,
                "Stratégie": comp.strategy_name,
                "Expiration": format_expiration_date(
                    comp.expiration_month, comp.expiration_year
                ),
                "Premium": format_currency(comp.premium),
                "Max Profit": format_currency(comp.max_profit),
                "Max Loss": (
                    format_currency(comp.max_loss)
                    if comp.max_loss != float("inf")
                    else "Illimité"
                ),
                "R/R": (
                    f"{comp.risk_reward_ratio:.2f}"
                    if comp.risk_reward_ratio != float("inf")
                    else "∞"
                ),
                "Zone ±": format_currency(comp.profit_zone_width),
                "P&L@Target": format_currency(comp.profit_at_target),
                "Target %": f"{comp.profit_at_target_pct:.1f}%",
                "Surf. Profit": (
                    f"{comp.surface_profit:.2f}"
                    if comp.surface_profit is not None
                    else "-"
                ),
                "Surf. Loss": (
                    f"{comp.surface_loss:.2f}" if comp.surface_loss is not None else "-"
                ),
                "P/L Ratio": (
                    f"{(comp.surface_profit/comp.surface_loss):.2f}"
                    if (
                        comp.surface_profit is not None
                        and comp.surface_loss is not None
                        and comp.surface_loss > 0
                    )
                    else "∞"
                ),
                "Avg P&L": (
                    format_currency(comp.average_pnl)
                    if comp.average_pnl is not None
                    else "-"
                ),
                "σ P&L": (
                    format_currency(comp.sigma_pnl)
                    if comp.sigma_pnl is not None
                    else "-"
                ),
                "Delta": f"{comp.total_delta:.3f}",
                "Gamma": f"{comp.total_gamma:.3f}",
                "Vega": f"{comp.total_vega:.3f}",
                "Theta": f"{comp.total_theta:.3f}",
                "IV": f"{comp.avg_implied_volatility:.2%}",
            }
        )

    return pd.DataFrame(data)


def strike_list(strike_min: float, strike_max: float, step: float) -> List[float]:
    strike_list = []
    strike = strike_min
    while strike <= strike_max:
        strike_list.append(strike)
        strike += step
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
        if comp.pnl_array is None:
            uniques.append(comp)
            continue
        
        # Signature = tuple du pnl_array arrondi
        sig = tuple(np.round(comp.pnl_array, decimals))
        if sig not in vues:
            vues.add(sig)
            uniques.append(comp)
    
    n = len(comparisons) - len(uniques)
    if n > 0:
        print(f"  🔍 {n} doublons éliminés")
    
    return uniques
