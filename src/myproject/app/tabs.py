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
    Affiche le tab Vue d'Ensemble avec les métriques et le tableau comparatif.

    Args:
        comparisons: Liste des stratégies à afficher
    """
    st.header("Vue d'Ensemble des Stratégies")

    # Carte de la stratégie gagnante
    winner = comparisons[0]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "🥇 Meilleure Stratégie", winner.strategy_name, f"Score: {winner.score:.3f}"
        )
    with col2:
        st.metric("💰 Max Profit", format_currency(winner.max_profit), "")
    with col3:
        max_loss_str = (
            format_currency(winner.max_loss)
            if winner.max_loss != float("inf")
            else "Illimité"
        )
        st.metric("⚠️ Max Loss", max_loss_str, "")
    with col4:
        st.metric(
            "🎯 P&L au Prix Cible",
            format_currency(winner.profit_at_target),
            f"{winner.profit_at_target_pct:.1f}% du max",
        )

    st.markdown("---")

    # Tableau de comparaison
    st.subheader("Tableau Comparatif")
    df = create_comparison_table(comparisons)

    st.dataframe(df.style, width="stretch", hide_index=True)


def display_payoff_tab(
    top_5_comparisons: List[StrategyComparison],
    best_target_price: float,
    mixture: Tuple[np.ndarray, np.ndarray],
):
    """
    Affiche le tab Diagramme P&L avec la mixture gaussienne intégrée.

    Args:
        top_5_comparisons: Top 5 des stratégies pour le diagramme
        best_target_price: Prix cible
        mixture: Tuple (prices, probabilities) pour la mixture gaussienne
    """
    st.header("Diagramme de Profit/Perte à l'Expiration (Top 5)")

    # Créer le diagramme avec seulement les 5 meilleures stratégies
    fig_payoff = create_payoff_diagram(
        comparisons=top_5_comparisons, target_price=best_target_price, mixture=mixture
    )
    st.plotly_chart(fig_payoff, use_container_width=True)
