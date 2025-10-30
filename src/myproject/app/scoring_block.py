import streamlit as st 
from myproject.strategy.comparison_class import StrategyComparison
from typing import Dict, List
from dataclasses import fields


# Définition des catégories de métriques basées sur StrategyComparison
SCORING_CATEGORIES = {
    "Financier": {
        "fields": ["max_profit", "max_loss", "risk_reward_ratio", "profit_at_target"],
        "color": "💰",
        "description": "Métriques de profit et risque"
    },
    "Surfaces": {
        "fields": ["surface_profit", "surface_loss", "surface_profit_ponderate", "surface_loss_ponderate"],
        "color": "📐",
        "description": "Aires sous la courbe de P&L"
    },
    "Zone Profitable": {
        "fields": ["profit_zone_width", "breakeven_points"],
        "color": "🎯",
        "description": "Largeur et points d'équilibre"
    },
    "Greeks": {
        "fields": ["total_delta", "total_gamma", "total_vega", "total_theta"],
        "color": "🔢",
        "description": "Sensibilités aux facteurs de marché"
    },
    "Mixture Gaussienne": {
        "fields": ["average_pnl", "sigma_pnl"],
        "color": "📊",
        "description": "Métriques pondérées par probabilité"
    },
    "Volatilité": {
        "fields": ["avg_implied_volatility"],
        "color": "🌊",
        "description": "Volatilité implicite moyenne"
    }
}

# Mapping des noms de champs vers des noms lisibles
FIELD_LABELS = {
    "max_profit": "Max Profit",
    "max_loss": "Max Loss",
    "risk_reward_ratio": "Risk/Reward",
    "profit_at_target": "Profit @ Target",
    "surface_profit": "Surface Profit",
    "surface_loss": "Surface Loss",
    "surface_profit_ponderate": "Surface Profit Pond.",
    "surface_loss_ponderate": "Surface Loss Pond.",
    "profit_zone_width": "Largeur Zone",
    "breakeven_points": "Breakevens",
    "total_delta": "Delta Total",
    "total_gamma": "Gamma Total",
    "total_vega": "Vega Total",
    "total_theta": "Theta Total",
    "average_pnl": "Average P&L",
    "sigma_pnl": "Sigma P&L",
    "avg_implied_volatility": "IV Moyenne"
}


def get_available_scoring_fields() -> List[str]:
    """Récupère tous les champs disponibles pour le scoring depuis StrategyComparison"""
    all_fields = []
    for category_info in SCORING_CATEGORIES.values():
        all_fields.extend(category_info["fields"])
    return all_fields


def scoring_weights_block() -> dict:
    st.subheader("⚖️ Pondération du Score - COMPLET")
    
    # STRATÉGIES PRÉDÉFINIES - Basées sur les champs de StrategyComparison
    preset_strategies = {
        "Balanced (Équilibré)": {
            # Financier (30%)
            'max_profit': 0.10,
            'max_loss': 0.05,
            'risk_reward_ratio': 0.10,
            'profit_at_target': 0.05,
            # Surfaces (25%)
            'surface_profit': 0.10,
            'surface_loss': 0.05,
            'surface_profit_ponderate': 0.06,
            'surface_loss_ponderate': 0.04,
            # Zone Profitable (15%)
            'profit_zone_width': 0.10,
            'breakeven_points': 0.05,
            # Greeks (20%)
            'total_delta': 0.06,
            'total_gamma': 0.04,
            'total_vega': 0.05,
            'total_theta': 0.05,
            # Mixture (8%)
            'average_pnl': 0.05,
            'sigma_pnl': 0.03,
            # Volatilité (2%)
            'avg_implied_volatility': 0.02
        },
        
        "Short Vol (Vente de Volatilité)": {
            # Favorise theta, surfaces pondérées, zone large
            'max_profit': 0.05,
            'max_loss': 0.05,
            'risk_reward_ratio': 0.08,
            'profit_at_target': 0.07,
            'surface_profit': 0.05,
            'surface_loss': 0.03,
            'surface_profit_ponderate': 0.15,
            'surface_loss_ponderate': 0.10,
            'profit_zone_width': 0.15,
            'breakeven_points': 0.05,
            'total_delta': 0.05,
            'total_gamma': 0.03,
            'total_vega': 0.02,
            'total_theta': 0.15,
            'average_pnl': 0.05,
            'sigma_pnl': 0.02,
            'avg_implied_volatility': 0.00
        },
        
        "Directional (Directionnel)": {
            # Favorise max profit, risk/reward, average_pnl
            'max_profit': 0.20,
            'max_loss': 0.03,
            'risk_reward_ratio': 0.15,
            'profit_at_target': 0.15,
            'surface_profit': 0.12,
            'surface_loss': 0.02,
            'surface_profit_ponderate': 0.08,
            'surface_loss_ponderate': 0.02,
            'profit_zone_width': 0.05,
            'breakeven_points': 0.02,
            'total_delta': 0.03,
            'total_gamma': 0.03,
            'total_vega': 0.02,
            'total_theta': 0.02,
            'average_pnl': 0.08,
            'sigma_pnl': 0.02,
            'avg_implied_volatility': 0.01
        },
        
        "Income (Génération de Revenus)": {
            # Favorise theta, zone profitable, surfaces pondérées
            'max_profit': 0.10,
            'max_loss': 0.05,
            'risk_reward_ratio': 0.08,
            'profit_at_target': 0.10,
            'surface_profit': 0.05,
            'surface_loss': 0.03,
            'surface_profit_ponderate': 0.12,
            'surface_loss_ponderate': 0.08,
            'profit_zone_width': 0.12,
            'breakeven_points': 0.05,
            'total_delta': 0.04,
            'total_gamma': 0.03,
            'total_vega': 0.03,
            'total_theta': 0.18,
            'average_pnl': 0.06,
            'sigma_pnl': 0.03,
            'avg_implied_volatility': 0.02
        },
        
        "Delta Neutral (Market Neutral)": {
            # Favorise neutralité delta, surfaces pondérées équilibrées
            'max_profit': 0.08,
            'max_loss': 0.05,
            'risk_reward_ratio': 0.10,
            'profit_at_target': 0.07,
            'surface_profit': 0.08,
            'surface_loss': 0.05,
            'surface_profit_ponderate': 0.10,
            'surface_loss_ponderate': 0.08,
            'profit_zone_width': 0.10,
            'breakeven_points': 0.05,
            'total_delta': 0.20,  # Important !
            'total_gamma': 0.06,
            'total_vega': 0.08,
            'total_theta': 0.05,
            'average_pnl': 0.05,
            'sigma_pnl': 0.03,
            'avg_implied_volatility': 0.02
        },
        
        "Manuel (Personnalisé)": None  # Sera configuré manuellement
    }
    


    strategy_choice = st.selectbox(
        "Choisir une stratégie:",
        list(preset_strategies.keys()),
        index=0,
        help="Sélectionnez une stratégie prédéfinie ou 'Manuel' pour personnaliser"
    )
    
    # Initialiser les poids avec la stratégie sélectionnée
    if strategy_choice != "Manuel (Personnalisé)":
        weights = preset_strategies[strategy_choice].copy()
        
        # Afficher les poids de la stratégie sélectionnée par catégorie
        if 'force_manual' not in st.session_state or not st.session_state['force_manual']:
            with st.expander("📊 Voir les poids de cette stratégie", expanded=False):
                # Afficher par catégories définies dans SCORING_CATEGORIES
                for category_name, category_info in SCORING_CATEGORIES.items():
                    st.markdown(f"**{category_info['color']} {category_name}**")
                    cols = st.columns(min(len(category_info['fields']), 4))
                    
                    for idx, field_name in enumerate(category_info['fields']):
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
    if 'force_manual' in st.session_state:
        del st.session_state['force_manual']
    
    with st.expander("📊 Personnaliser TOUS les poids de scoring", expanded=True):
        st.markdown("**Configuration basée sur les champs de StrategyComparison. Total doit être ~100%**")
        
        weights_manual = {}
        
        # Parcourir chaque catégorie et créer les sliders
        for category_name, category_info in SCORING_CATEGORIES.items():
            st.markdown(f"### {category_info['color']} {category_name}")
            st.caption(category_info['description'])
            
            # Créer des colonnes pour les sliders (max 3 par ligne)
            fields_in_category = category_info['fields']
            num_cols = min(len(fields_in_category), 3)
            cols = st.columns(num_cols)
            
            for idx, field_name in enumerate(fields_in_category):
                col_idx = idx % num_cols
                with cols[col_idx]:
                    label = FIELD_LABELS.get(field_name, field_name) or field_name
                    # Valeur par défaut de 5%
                    default_value = 5
                    weight = st.slider(
                        str(label),  # Garantir que c'est un str
                        min_value=0,
                        max_value=100,
                        value=default_value,
                        step=1,
                        key=f"weight_{field_name}"
                    ) / 100
                    weights_manual[field_name] = weight
        
        # Calculer et afficher le total
        total = sum(weights_manual.values())
        
        st.markdown("---")
        if total < 0.95 or total > 1.05:
            st.warning(f"⚠️ Total des poids: {total*100:.1f}% (devrait être proche de 100%)")
        else:
            st.success(f"✅ Total des poids: {total*100:.1f}%")
    
    return weights_manual
