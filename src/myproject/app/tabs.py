"""
Module pour gérer les différents tabs de l'application Streamlit
"""

import streamlit as st
import numpy as np
from typing import List, Tuple
from myproject.strategy.comparison_class import StrategyComparison
from myproject.app.utils import format_currency
from myproject.app.comparison_table import create_comparison_table
from myproject.app.payoff_diagram import create_payoff_diagram


def display_overview_tab(comparisons: List[StrategyComparison]):
    """
    Displays the Overview tab with metrics and the comparison table.

    Args:
        comparisons: List of strategies to display
    """
    st.header("Strategies Overview")

    # Winner card
    winner = comparisons[0]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "🥇 Best Strategy", winner.strategy_name, f"Score: {winner.score:.3f}"
        )
    with col2:
        st.metric("💰 Max Profit", format_currency(winner.max_profit), "")
    with col3:
        max_loss_str = (
            format_currency(winner.max_loss)
            if winner.max_loss != float("inf")
            else "Unlimited"
        )
        st.metric("⚠️ Max Loss", max_loss_str, "")
    with col4:
        st.metric(
            "🎯 P&L at Target Price",
            format_currency(winner.profit_at_target),
            f"{winner.profit_at_target_pct:.1f}% of max",
        )

    st.markdown("---")

    # Comparison Table
    st.subheader("Comparison Table")
    df = create_comparison_table(comparisons)

    st.dataframe(df.style, width="stretch", hide_index=True)


def display_payoff_tab(
    top_5_comparisons: List[StrategyComparison],
    best_target_price: float,
    mixture: Tuple[np.ndarray, np.ndarray],
):
    """
    Displays the P&L Diagram tab with integrated Gaussian mixture.

    Args:
        top_5_comparisons: Top 5 strategies for the diagram
        best_target_price: Target price
        mixture: Tuple (prices, probabilities) for the Gaussian mixture
    """
    st.header("Profit/Loss Diagram at Expiration (Top 5)")

    # Create diagram with only top 5 strategies
    fig_payoff = create_payoff_diagram(
        comparisons=top_5_comparisons, target_price=best_target_price, mixture=mixture
    )
    st.plotly_chart(fig_payoff, use_container_width=True)
