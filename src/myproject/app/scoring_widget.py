import streamlit as st
from typing import List


# Definition of scoring categories based on comparor_v2.py
SCORING_CATEGORIES = {
    "Gaussian Mixture": {
        "fields": ["average_pnl", "roll", "roll_quarterly", "sigma_pnl"],
        "color": "📊",
        "description": "Probability weighted metrics",
    },
    "Greeks": {
        "fields": ["delta_neutral", "gamma_low", "vega_low", "theta_positive"],
        "color": "🔢",
        "description": "Market factor sensitivities",
    },
    "Volatility & Cost": {
        "fields": ["implied_vol_moderate"],
        "color": "🌊",
        "description": "Implied volatility and cost/credit",
    },
}

# Mapping of field names to readable names
FIELD_LABELS = {
    "delta_neutral": "Delta Neutral",
    "gamma_low": "Gamma Low",
    "vega_low": "Vega Low",
    "theta_positive": "Theta Positive",
    "average_pnl": "Average P&L",
    "roll": "Roll (Avg)",
    "roll_quarterly": "Roll (Q-1)",
    "sigma_pnl": "Sigma P&L",
    "implied_vol_moderate": "Moderate IV",
}


def get_available_scoring_fields() -> List[str]:
    """Retrieves all available scoring fields from StrategyComparison"""
    all_fields = []
    for category_info in SCORING_CATEGORIES.values():
        all_fields.extend(category_info["fields"])
    return all_fields


def scoring_weights_block() -> dict:
    st.subheader("Score Weighting")
    weights_manual = {}

    # Iterate mainly through each category and create sliders
    for category_name, category_info in SCORING_CATEGORIES.items():
        fields_in_category = category_info["fields"]
        num_cols = min(len(fields_in_category), 3)
        cols = st.columns(num_cols)

        for idx, field_name in enumerate(fields_in_category):
            col_idx = idx % num_cols
            with cols[col_idx]:
                label = FIELD_LABELS.get(field_name, field_name) or field_name
                # Default value: 100 for average_pnl, 0 for others
                default_value = 100 if field_name == "average_pnl" else 0
                weight = (
                    st.slider(
                        str(label),  # Ensure it is a str
                        min_value=0,
                        max_value=100,
                        value=default_value,
                        step=1,
                        key=f"weight_{field_name}",
                    )
                    / 100
                )
                weights_manual[field_name] = weight
    return weights_manual
        
