# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

from typing import List, Optional
from option.option_class import Option
from strategy.strategy_class import StrategyComparison
import pandas as pd

def split_calls_puts(options: List[Option]):
    """Sépare les calls et puts."""
    calls = [o for o in options if o.is_call()]
    puts = [o for o in options if o.is_put()]
    return calls, puts


def format_currency(value: float) -> str:
    """Formats a value as currency."""
    if value == float("inf"):
        return "Unlimited"
    return f"{value:.2f}"


def format_price(value: float, unit: str = "100ème") -> str:
    """Formats a price value, converting to 64ths if needed"""
    if value is None:
        return "-"
    if value == float("inf") or value == float("-inf"):
        return "Unlimited"
    if unit == "64ème":
        ticks_64 = value * 64 / 100
        return f"{ticks_64:.2f}"
    return f"{value:.3f}"


def format_percentage(value: float) -> str:
    """Formats a percentage."""
    return f"{value:.1f}%"


def format_expiration_date(month: str, year: int) -> str:
    """
    Formate la date d'expiration à partir du mois Bloomberg et de l'année.
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
    Génére une liste de strike entre le point strike min et strike max
    """
    num_steps = int(round((strike_max - strike_min) / step)) + 1
    strike_list = [round(strike_min + i * step, 10) for i in range(num_steps)]
    return strike_list


# ============================================================================
# Comparison table builder  (ex widget_comparison.py)
# ============================================================================

def create_comparison_table(comparisons: List[StrategyComparison], roll_labels: Optional[List[str]] = None, max_rows: int = 15, unit: str = "100ème") -> pd.DataFrame:
    """
    Creates a DataFrame for displaying comparisons with ALL scoring criteria.
    """
    data = []
    for idx, comp in enumerate(comparisons[:max_rows], 1):
        row = {
            "Rank": idx,
            "Score": comp.score,
            "Strategy": comp.strategy_name,
            "Premium": format_price(comp.premium, unit),
            "Max Profit": format_price(comp.max_profit, unit),
            "Avg P&L": format_price(comp.average_pnl, unit) if comp.average_pnl is not None else "-",
            "Delta %": f"{comp.total_delta * 100:.2f}%",
            "Lvg P&L" : format_price(comp.avg_pnl_levrage, unit) if comp.avg_pnl_levrage is not None else "-",
            "Gamma" : f"{comp.total_gamma * 100:.2f}",
            "Theta" : f"{comp.total_theta * 100:.2f}",
        }
        
        if roll_labels:
            for label in roll_labels[:4]:
                roll_value = comp.rolls_detail.get(label)
                row[f"Roll {label}"] = format_price(roll_value, unit) if roll_value is not None else "-"
        data.append(row)
    
    return pd.DataFrame(data)
