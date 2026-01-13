
from myproject.app.utils import format_currency, format_expiration_date, format_currency
from myproject.strategy.comparison_class import StrategyComparison
from typing import List
import pandas as pd 


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
