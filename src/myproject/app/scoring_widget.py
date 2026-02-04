import streamlit as st
from typing import List


# All scoring fields with their labels
SCORING_FIELDS = {
    "average_pnl": ("Expected gain at expiry", 100),
    "roll_quarterly": ("Roll into next quarter", 0),
    "max_loss": ("Max Drawdown", 0),
    "premium": ("Premium", 0),
    "avg_pnl_levrage": ("Leverage of expected gain", 0),

}

ADVENCED_SCORING_FIELDS = {
    "sigma_pnl": ("Standard deviation", 0),
    "delta_neutral": ("Delta Neutral", 0),
    "gamma_low": ("Gamma Low", 0),
    "vega_low": ("Vega Low", 0),
    "theta_positive": ("Theta Positive", 0),
    "implied_vol_moderate": ("Moderate IV", 0),
    "delta_levrage": ("Leverage with delta", 0),
}

def scoring_weights_block() -> dict:
    st.subheader("Score Weighting")
    weights_manual = {}

    cols = st.columns(3)
    for idx, (field_name, (label, default_value)) in enumerate(SCORING_FIELDS.items()):
        with cols[idx % 3]:
            weight = st.number_input(
                label,
                min_value=0,
                max_value=100,
                value=default_value,
                step=1,
                key=f"weight_{field_name}",
            ) / 100
            weights_manual[field_name] = weight
    
    st.subheader("Advanced Score Weighting")
    cols = st.columns(3)
    for idx, (field_name, (label, default_value)) in enumerate(ADVENCED_SCORING_FIELDS.items()):
        with cols[idx % 3]:
            weight = st.number_input(
                label,
                min_value=0,
                max_value=100,
                value=default_value,
                step=1,
                key=f"weight_{field_name}",
            ) / 100
            weights_manual[field_name] = weight

    
    return weights_manual
        
