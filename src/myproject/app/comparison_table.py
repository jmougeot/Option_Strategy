
from myproject.app.utils import format_currency, format_expiration_date
from myproject.strategy.strategy_class import StrategyComparison
from typing import List, Optional
import pandas as pd 


def create_comparison_table(comparisons: List[StrategyComparison], roll_labels: Optional[List[str]] = None, max_rows: int = 5) -> pd.DataFrame:
    """Creates a DataFrame for displaying comparisons with ALL scoring criteria.
    
    Args:
        comparisons: List of strategy comparisons
        roll_labels: List of roll expiry labels (ex: ["H6", "M6", "U6"]) to display as columns.
                    If None or empty, no roll columns are shown.
        max_rows: Maximum number of rows to display (default: 5)
    """
    data = []
    for idx, comp in enumerate(comparisons[:max_rows], 1):
        row = {
            "Rank": idx,
            "Score": comp.score,
            "Strategy": comp.strategy_name,
            "Premium": f"{comp.premium:.3f}",
            "Max Profit": format_currency(comp.max_profit),
            "Avg P&L": format_currency(comp.average_pnl) if comp.average_pnl is not None else "-",
            "Delta %": f"{comp.total_delta * 100:.2f}%",
            "Lvg P&L" : format_currency(comp.avg_pnl_levrage) if comp.avg_pnl_levrage is not None else "-",
            "Lvg Delta " : format_currency(comp.delta_levrage) if comp.delta_levrage is not None else "-",
        }
        
        # Colonnes de roll dynamiques basées sur roll_labels (limité à 2 rolls max)
        if roll_labels:
            for label in roll_labels[:2]:  # Limiter à 2 rolls max pour réduire les colonnes
                roll_value = comp.rolls_detail.get(label)
                row[f"Roll {label}"] = f"{roll_value:.4f}" if roll_value is not None else "-"
        data.append(row)
    
    return pd.DataFrame(data)

