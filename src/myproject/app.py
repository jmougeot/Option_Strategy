"""
Streamlit Interface for Options Strategy Comparison
Description: Web user interface to compare options strategies
"""

import streamlit as st
from myproject.app.main import process_bloomberg_to_strategies
from myproject.app.styles import inject_css
from myproject.app.params_widget import sidebar_params
from myproject.app.scenarios_widget import scenario_params
from myproject.app.scoring_widget import scoring_weights_block
from myproject.app.tabs import display_overview_tab, display_payoff_tab
from myproject.app.processing import (
    process_comparison_results,
    save_to_session_state,
    display_success_stats,
)
from myproject.app.filter_widget import filter_params


# ============================================================================
# CONFIGURATION DE LA PAGE
# ============================================================================

st.set_page_config(
    page_title="Options Strategy Comparator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()

# ============================================================================
# INTERFACE PRINCIPALE
# ============================================================================

def main():
    # En-tête
    st.markdown(
        '<div class="main-header">📊 Comparateur de Stratégies Options</div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # ========================================================================
    # SIDEBAR - PARAMÈTRES
    # ========================================================================

    with st.sidebar:
        scenarios = scenario_params()
        st.markdown("---")
        params = sidebar_params()
        filter = filter_params()
        scoring_weights = scoring_weights_block()

    # ========================================================================
    # ZONE PRINCIPALE
    # ========================================================================

    compare_button = st.button(
        "🚀 Lancer la Comparaison", type="primary", use_container_width=True
    )

    # Déterminer quelle source de stratégies utiliser
    all_comparisons = None
    best_target_price = None
    # Utiliser les stratégies chargées si disponibles

    if compare_button:
        # ====================================================================
        # ÉTAPE 1 : Traitement complet via la fonction main
        # ====================================================================

        with st.spinner(
            f"🔄 Génération et comparaison des stratégies (max {params.max_legs} legs)..."
        ):
            # Appeler la fonction principale qui fait TOUT
            best_strategies, stats, mixture = process_bloomberg_to_strategies(
                brut_code=params.brut_code,
                underlying=params.underlying,
                months=params.months,
                years=params.years,
                strikes=params.strikes,
                price_min=params.price_min,
                price_max=params.price_max,
                max_legs=params.max_legs,
                top_n=500,
                scoring_weights=scoring_weights,
                scenarios=scenarios, #type: ignore
                filter=filter
            )

            # Vérifier les résultats
            if not best_strategies:
                st.error("❌ Aucune stratégie générée")
                return

            display_success_stats(stats)

        # Utiliser best_strategies pour l'affichage
        all_comparisons = best_strategies

        if not all_comparisons:
            st.error("❌ Aucune stratégie disponible")
            return

        # Sauvegarder dans session_state (incluant les scénarios)
        save_to_session_state(
            all_comparisons, params, best_strategies[0].target_price, scenarios
        )

    # Si on arrive ici sans stratégies, ne rien afficher
    if not all_comparisons:
        return

    # Traiter et filtrer les résultats
    comparisons, top_5_comparisons, best_target_price = process_comparison_results(
        all_comparisons
    )

    # ====================================================================
    # TABS POUR L'AFFICHAGE
    # ====================================================================

    tab1, tab2 = st.tabs(["Vue d'Ensemble", "Diagramme P&L"])

    # Afficher chaque tab avec son module dédié
    with tab1:
        display_overview_tab(comparisons)

    with tab2:
        display_payoff_tab(top_5_comparisons, best_target_price, mixture) #type: ignore

# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

if __name__ == "__main__":
    main()
