import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from typing import Dict, List
from myproject.strategy.comparison_class import StrategyComparison
from myproject.option.option_class import Option


def create_comparison_table(comparisons: List[StrategyComparison]) -> pd.DataFrame:
    """Crée un DataFrame pour l'affichage des comparaisons avec TOUS les critères de scoring."""
    
    data = []
    for idx, comp in enumerate(comparisons, 1):
        data.append({
            'Rang': idx,
            'Stratégie': comp.strategy_name,
            'Expiration': format_expiration_date(comp.expiration_month, comp.expiration_year),
            'Premium': format_currency(comp.premium),
            'Max Profit': format_currency(comp.max_profit),
            'Max Loss': format_currency(comp.max_loss) if comp.max_loss != float('inf') else 'Illimité',
            'R/R': f"{comp.risk_reward_ratio:.2f}" if comp.risk_reward_ratio != float('inf') else '∞',
            'Zone ±': format_currency(comp.profit_zone_width),
            'P&L@Target': format_currency(comp.profit_at_target),
            'Target %': f"{comp.profit_at_target_pct:.1f}%",
            'Surf. Profit': f"{comp.surface_profit:.2f}",
            'Surf. Loss': f"{comp.surface_loss:.2f}",
            'P/L Ratio': f"{(comp.surface_profit/comp.surface_loss):.2f}" if comp.surface_loss > 0 else '∞',
            'Avg P&L': format_currency(comp.average_pnl) if comp.average_pnl is not None else '-',
            'σ P&L': format_currency(comp.sigma_pnl) if comp.sigma_pnl is not None else '-',
            'Delta': f"{comp.total_delta:.3f}",
            'Gamma': f"{comp.total_gamma:.3f}",
            'Vega': f"{comp.total_vega:.3f}",
            'Theta': f"{comp.total_theta:.3f}",
            'IV': f"{comp.avg_implied_volatility:.2%}",
        })
    
    return pd.DataFrame(data)