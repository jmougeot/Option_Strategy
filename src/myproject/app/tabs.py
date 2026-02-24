"""
Module pour gÃ©rer les diffÃ©rents tabs de l'application Streamlit
"""

import streamlit as st
from typing import List, Optional
from myproject.strategy.strategy_class import StrategyComparison
from myproject.app.utils import format_currency, format_expiration_date, format_price
from myproject.app.widget_comparison import create_comparison_table


def display_overview_tab(comparisons: List[StrategyComparison], roll_labels: Optional[List[str]] = None, unit: str = "100ème", tab_key: str = "default") -> List[StrategyComparison]:
    """
    Displays the Overview tab. Returns the active (non-deleted) comparisons.
    """
    if not comparisons:
        st.info("No strategies to display for this ranking.")
        return []

    editor_key = f"overview_table_{tab_key}"
    orig_key   = f"{editor_key}_orig"
    active_key = f"{editor_key}_active_comps"

    # Si orig_key a été effacé (nouveau run), on réinitialise aussi active_key
    if orig_key not in st.session_state:
        st.session_state.pop(active_key, None)

    # Initialiser la liste active une seule fois par run
    if active_key not in st.session_state:
        st.session_state[active_key] = list(comparisons)

    active_comparisons = st.session_state[active_key] or list(comparisons)

    winner = active_comparisons[0]
    expiry_str = format_expiration_date(winner.expiration_month, winner.expiration_year)

    col1, col2, col3, col4 = st.columns([6, 4, 4, 4])
    with col1:
        st.metric(
            f"🥇 Best Strategy ({expiry_str})", 
            winner.strategy_name, 
        )
    with col2:
        st.metric("Max Profit", format_price(winner.max_profit, unit), "")
    with col3:
        max_loss_str = (
            format_price(winner.max_loss, unit)
            if winner.max_loss != float("inf")
            else "Unlimited"
        )
        st.metric("Max Loss", max_loss_str, "")
    with col4:
        st.metric(
            "Expected gain at expiry",
            format_price(winner.average_pnl, unit),
            f"{winner.profit_at_target_pct:.1f}% of max",
        )

    st.markdown("---")

    # Comparison Table
    st.subheader("Top Strategies")
    df = create_comparison_table(comparisons, roll_labels=roll_labels, max_rows=30, unit=unit)

    if df.empty:
        st.warning("Aucune stratégie à afficher")
        return active_comparisons

    # Stocker le df original une seule fois (reseté par overview.py sur nouveau run)
    if orig_key not in st.session_state:
        st.session_state[orig_key] = df.copy()
    orig_df = st.session_state[orig_key]

    def color_rank(val):
        if val == 1:   return 'background-color: #FFD700; color: black; font-weight: bold'
        elif val == 2: return 'background-color: #C0C0C0; color: black; font-weight: bold'
        elif val == 3: return 'background-color: #CD7F32; color: white; font-weight: bold'
        return ''

    # Bouton reset
    col_reset, _ = st.columns([1, 5])
    with col_reset:
        if st.button("↺ Reset", key=f"{editor_key}_reset", help="Restore deleted rows"):
            st.session_state.pop(editor_key, None)
            st.session_state.pop(orig_key, None)
            st.session_state.pop(active_key, None)
            st.rerun()

    # data_editor retourne le df après suppression — on l'utilise directement
    editable_cols = ['Premium'] if 'Premium' in orig_df.columns else []
    disabled_cols = [c for c in orig_df.columns if c not in editable_cols]

    result_df = st.data_editor(
        orig_df,
        hide_index=True,
        num_rows="dynamic",
        height=350,
        width="stretch",
        key=editor_key,
        disabled=disabled_cols,
    )

    # Renumeroter les rangs si des lignes ont été supprimées
    if result_df is not None and len(result_df) < len(orig_df) and 'Rank' in result_df.columns:
        # Mettre à jour la liste active en utilisant les indices conservés
        kept_positions = list(result_df.index)
        current_active = st.session_state[active_key]
        st.session_state[active_key] = [
            current_active[i] for i in kept_positions if i < len(current_active)
        ]
        result_df = result_df.reset_index(drop=True).copy()
        result_df['Rank'] = range(1, len(result_df) + 1)
        st.session_state[orig_key] = result_df
        st.session_state.pop(editor_key, None)
        st.rerun()

    return active_comparisons
