from myproject.app.utils import format_currency, format_expiration_date, format_price
from myproject.strategy.strategy_class import StrategyComparison
from typing import List, Optional
import pandas as pd 


def create_comparison_table(comparisons: List[StrategyComparison], roll_labels: Optional[List[str]] = None, max_rows: int = 5, unit: str = "100ème") -> pd.DataFrame:
    """Creates a DataFrame for displaying comparisons with ALL scoring criteria.
    
    Args:
        comparisons: List of strategy comparisons
        roll_labels: List of roll expiry labels (ex: ["H6", "M6", "U6"]) to display as columns.
                    If None or empty, no roll columns are shown.
        max_rows: Maximum number of rows to display (default: 5)
        unit: "64ème" to display prices in 64ths, otherwise decimal
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
            "Avg Intra P&L": format_price(comp.avg_intra_life_pnl, unit) if comp.avg_intra_life_pnl is not None else "-",
        }
        
        # Colonnes de roll dynamiques basées sur roll_labels (limité à 4 rolls max)
        if roll_labels:
            for label in roll_labels[:4]:
                roll_value = comp.rolls_detail.get(label)
                row[f"Roll {label}"] = format_price(roll_value, unit) if roll_value is not None else "-"
        data.append(row)
    
    return pd.DataFrame(data)