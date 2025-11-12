import streamlit as st
from typing import List


# Définition des catégories de métriques basées sur comparor_v2.py
SCORING_CATEGORIES = {
    "Financier": {
        "fields": ["max_profit", "risk_over_reward", "profit_zone_width", "profit_at_target"],
        "color": "💰",
        "description": "Métriques de profit et risque",
    },
    "Surfaces": {
        "fields": [
            "surface_profit",
            "surface_loss",
            "surface_profit_ponderated",
            "surface_loss_ponderated",
            "reward_over_risk",
        ],
        "color": "📐",
        "description": "Aires sous la courbe de P&L",
    },
    "Greeks": {
        "fields": ["delta_neutral", "gamma_low", "vega_low", "theta_positive"],
        "color": "🔢",
        "description": "Sensibilités aux facteurs de marché",
    },
    "Mixture Gaussienne": {
        "fields": ["average_pnl", "sigma_pnl"],
        "color": "📊",
        "description": "Métriques pondérées par probabilité",
    },
    "Volatilité & Coût": {
        "fields": ["implied_vol_moderate", "premium_credit"],
        "color": "🌊",
        "description": "Volatilité implicite et coût/crédit",
    },
}

# Mapping des noms de champs vers des noms lisibles
FIELD_LABELS = {
    "max_profit": "Max Profit",
    "risk_over_reward": "Risk/Reward",
    "profit_at_target": "Profit @ Target",
    "profit_zone_width": "Largeur Zone",
    "surface_profit": "Surface Profit",
    "surface_loss": "Surface Loss",
    "surface_profit_ponderated": "Surface Profit Pond.",
    "surface_loss_ponderated": "Surface Loss Pond.",
    "reward_over_risk": "Reward/Risk Ratio",
    "delta_neutral": "Delta Neutral",
    "gamma_low": "Gamma Low",
    "vega_low": "Vega Low",
    "theta_positive": "Theta Positive",
    "average_pnl": "Average P&L",
    "sigma_pnl": "Sigma P&L",
    "implied_vol_moderate": "IV Modérée",
    "premium_credit": "Premium (Crédit)",
}


def get_available_scoring_fields() -> List[str]:
    """Récupère tous les champs disponibles pour le scoring depuis StrategyComparison"""
    all_fields = []
    for category_info in SCORING_CATEGORIES.values():
        all_fields.extend(category_info["fields"])
    return all_fields


def scoring_weights_block() -> dict:
    st.subheader("Pondération du Score - COMPLET")

    # STRATÉGIES PRÉDÉFINIES - Basées sur comparor_v2.py
    preset_strategies = {
        "Balanced (Équilibré)": {
            # Financier (36%)
            "max_profit": 0.10,
            "risk_over_reward": 0.10,
            "profit_zone_width": 0.08,
            "profit_at_target": 0.08,
            # Surfaces (46%)
            "surface_profit": 0.12,
            "surface_loss": 0.08,
            "surface_profit_ponderated": 0.08,
            "surface_loss_ponderated": 0.08,
            "reward_over_risk": 0.10,
            # Greeks (18%)
            "delta_neutral": 0.06,
            "gamma_low": 0.04,
            "vega_low": 0.04,
            "theta_positive": 0.04,
            # Mixture (18%)
            "average_pnl": 0.15,
            "sigma_pnl": 0.03,
            # Volatilité & Coût (9%)
            "implied_vol_moderate": 0.04,
            "premium_credit": 0.05,
        },
        "Manuel (Personnalisé)": None,  # Sera configuré manuellement
    }

    strategy_choice = st.selectbox(
        "Choisir une stratégie:",
        list(preset_strategies.keys()),
        index=len(preset_strategies) - 1,  # Manuel par défaut (dernier élément)
        help="Sélectionnez une stratégie prédéfinie ou 'Manuel' pour personnaliser",
    )

    # Initialiser les poids avec la stratégie sélectionnée
    if strategy_choice != "Manuel (Personnalisé)":
        weights = preset_strategies[strategy_choice].copy()

        # Afficher les poids de la stratégie sélectionnée par catégorie
        with st.expander("📊 Voir les poids de cette stratégie", expanded=False):
            # Afficher par catégories définies dans SCORING_CATEGORIES
            for category_name, category_info in SCORING_CATEGORIES.items():
                st.markdown(f"**{category_info['color']} {category_name}**")
                cols = st.columns(min(len(category_info["fields"]), 4))

                for idx, field_name in enumerate(category_info["fields"]):
                    col_idx = idx % len(cols)
                    with cols[col_idx]:
                        label = FIELD_LABELS.get(field_name, field_name)
                        weight_value = weights.get(field_name, 0.0)
                        st.write(f"{label}: {weight_value*100:.1f}%")

            # Afficher le total
            total = sum(weights.values())
            if total < 0.95 or total > 1.05:
                st.warning(f"⚠️ Total: {total*100:.1f}%")
            else:
                st.success(f"✅ Total: {total*100:.1f}%")

        return weights

    # Mode MANUEL - Afficher tous les sliders organisés par catégories

    with st.expander("📊 Personnaliser TOUS les poids de scoring", expanded=True):
        st.markdown(
            "**Configuration basée sur comparor_v2.py. Total doit être ~100%**"
        )

        weights_manual = {}

        # Parcourir chaque catégorie et créer les sliders
        for category_name, category_info in SCORING_CATEGORIES.items():
            st.markdown(f"### {category_info['color']} {category_name}")
            st.caption(category_info["description"])

            # Créer des colonnes pour les sliders (max 3 par ligne)
            fields_in_category = category_info["fields"]
            num_cols = min(len(fields_in_category), 3)
            cols = st.columns(num_cols)

            for idx, field_name in enumerate(fields_in_category):
                col_idx = idx % num_cols
                with cols[col_idx]:
                    label = FIELD_LABELS.get(field_name, field_name) or field_name
                    # Valeur par défaut de 0%
                    default_value = 0
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

        # Calculer et afficher le total
        total = sum(weights_manual.values())

        st.markdown("---")
        if total < 0.95 or total > 1.05:
            st.warning(
                f"⚠️ Total des poids: {total*100:.1f}% (devrait être proche de 100%)"
            )
        else:
            st.success(f"✅ Total des poids: {total*100:.1f}%")

    return weights_manual
