"""
Module pour gÃ©rer les diffÃ©rents tabs de l'application Streamlit
"""

import streamlit as st
import numpy as np
from typing import List, Optional, Tuple
from myproject.strategy.strategy_class import StrategyComparison
from myproject.app.utils import format_currency, format_expiration_date
from myproject.app.comparison_table import create_comparison_table
import pandas as pd


def display_overview_tab(comparisons: List[StrategyComparison], roll_labels: Optional[List[str]] = None):
    """
    Displays the Overview tab with metrics and the comparison table.

    Args:
        comparisons: List of strategies to display
        roll_labels: List of roll expiry labels (ex: ["H6", "M6"]) for dynamic columns.
                    If None, no roll columns are shown.
    """
    st.header("Strategies Overview")

    # Winner card avec expiry
    winner = comparisons[0]
    expiry_str = format_expiration_date(winner.expiration_month, winner.expiration_year)

    col1, col2, col3, col4 = st.columns([10, 4, 4, 4])
    with col1:
        st.metric(
            f"🥇 Best Strategy ({expiry_str})", 
            winner.strategy_name, 
            f"Score: {winner.score:.3f}"
        )
    with col2:
        st.metric("Max Profit", format_currency(winner.max_profit), "")
    with col3:
        max_loss_str = (
            format_currency(winner.max_loss)
            if winner.max_loss != float("inf")
            else "Unlimited"
        )
        st.metric("Max Loss", max_loss_str, "")
    with col4:
        st.metric(
            "Futures Reference",
            format_currency(winner.profit_at_target),
            f"{winner.profit_at_target_pct:.1f}% of max",
        )

    st.markdown("---")

    # Comparison Table avec style amélioré
    st.subheader("Top 5 Strategies")
    df = create_comparison_table(comparisons, roll_labels=roll_labels, max_rows=5)

    # Vérifier que le DataFrame n'est pas vide
    if df.empty:
        st.warning("Aucune stratégie à afficher")
        return
    
    # Style du tableau avec couleurs pour les rangs seulement
    def color_rank(val):
        if val == 1:
            return 'background-color: #FFD700; color: black; font-weight: bold'  # Or
        elif val == 2:
            return 'background-color: #C0C0C0; color: black; font-weight: bold'  # Argent
        elif val == 3:
            return 'background-color: #CD7F32; color: white; font-weight: bold'  # Bronze
        return ''
    
    # Appliquer les styles
    styled_df = df.style
    
    # Appliquer les couleurs pour les rangs
    if 'Rank' in df.columns:
        styled_df = styled_df.map(color_rank, subset=['Rank'])
    
    # Appliquer le style général avec police plus grande
    styled_df = styled_df.set_properties(**{
        'font-size': '16px',
        'padding': '10px'
    })
    
    # Afficher avec hauteur limitée pour permettre le scroll
    st.dataframe(
        styled_df,
        hide_index=True,
        height=400,
        use_container_width=True
    )
