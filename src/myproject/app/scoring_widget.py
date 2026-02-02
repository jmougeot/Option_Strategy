import streamlit as st
from typing import List


# Definition of scoring categories based on comparor_v2.py
SCORING_CATEGORIES = {
    "Gaussian Mixture": {
        "fields": ["average_pnl", "roll_quarterly", "sigma_pnl", "avg_pnl_levrage"],
    },
    "Greeks": {
        "fields": ["premium", "delta_neutral", "gamma_low", "vega_low", "theta_positive"],
    },
    "Volatility & Cost": {
        "fields": ["implied_vol_moderate"],
    },
    "Levarge" : {
        "fields" : ["delta_levrage"]
    }
}

# Mapping of field names to readable names
FIELD_LABELS = {
    "delta_neutral": "Delta Neutral",
    "gamma_low": "Gamma Low",
    "vega_low": "Vega Low",
    "theta_positive": "Theta Positive",
    "average_pnl": "Expected gain at expiry",
    "roll_quarterly": "Roll into next quarter",
    "sigma_pnl": "Standart deviation",
    "implied_vol_moderate": "Moderate IV",
    "delta_levrage": "Levrage with delta",
    "avg_pnl_levrage": "Levrage of expectied gain",
    "premium" : "premium"
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
                # Default values: 100 for average_pnl, 50 for premium, 0 for others
                if field_name == "average_pnl":
                    default_value = 100
                elif field_name == "premium":
                    default_value = 50  # Premium proche de 0 = meilleur
                else:
                    default_value = 0
                weight = (
                    st.slider(
                        str(label),
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
        
