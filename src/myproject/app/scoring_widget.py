import streamlit as st
from typing import List


# Définition des catégories de métriques basées sur comparor_v2.py
SCORING_CATEGORIES = {
    "Mixture Gaussienne": {
        "fields": ["average_pnl", "sigma_pnl"],
        "color": "📊",
        "description": "Métriques pondérées par probabilité",
    },
    "Greeks": {
        "fields": ["delta_neutral", "gamma_low", "vega_low", "theta_positive"],
        "color": "🔢",
        "description": "Sensibilités aux facteurs de marché",
    },
    "Volatilité & Coût": {
        "fields": ["implied_vol_moderate"],
        "color": "🌊",
        "description": "Volatilité implicite et coût/crédit",
    },
}

# Mapping des noms de champs vers des noms lisibles
FIELD_LABELS = {
    "delta_neutral": "Delta Neutral",
    "gamma_low": "Gamma Low",
    "vega_low": "Vega Low",
    "theta_positive": "Theta Positive",
    "average_pnl": "Average P&L",
    "sigma_pnl": "Sigma P&L",
    "implied_vol_moderate": "IV Modérée",
}


def get_available_scoring_fields() -> List[str]:
    """Récupère tous les champs disponibles pour le scoring depuis StrategyComparison"""
    all_fields = []
    for category_info in SCORING_CATEGORIES.values():
        all_fields.extend(category_info["fields"])
    return all_fields


def scoring_weights_block() -> dict:
    st.subheader("Pondération du Score")
    weights_manual = {}

    # Parcourir chaque catégorie et créer les sliders
    for category_name, category_info in SCORING_CATEGORIES.items():
        fields_in_category = category_info["fields"]
        num_cols = min(len(fields_in_category), 3)
        cols = st.columns(num_cols)

        for idx, field_name in enumerate(fields_in_category):
            col_idx = idx % num_cols
            with cols[col_idx]:
                label = FIELD_LABELS.get(field_name, field_name) or field_name
                # Valeur par défaut : 100 pour average_pnl, 0 pour les autres
                default_value = 100 if field_name == "average_pnl" else 0
                weight = (
                    st.slider(
                        str(label),  # Garantir que c'est un str
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
        
