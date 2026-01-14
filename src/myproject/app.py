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
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Options Strategy Comparator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()

# ============================================================================
# MAIN INTERFACE
# ============================================================================

def main():
    # Header
    st.markdown(
        '<div class="main-header">Options Strategy Comparator</div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # ========================================================================
    # SIDEBAR - PARAMETERS
    # ========================================================================

    with st.sidebar:
        scenarios = scenario_params()
        st.markdown("---")
        params = sidebar_params()
        filter = filter_params()
        scoring_weights = scoring_weights_block()

        st.markdown("---")
        from myproject.app.email_utils import generate_mailto_link, StrategyEmailData
        
        # Use session state scenarios which are list of dicts
        scenarios_list = st.session_state.get("scenarios", [])
        
        # Get best strategy info from session state if available
        best_strategy_data = None
        top_strategies_data = None
        
        if "comparisons" in st.session_state and st.session_state.comparisons:
            comparisons_list = st.session_state.comparisons
            
            # Build detailed strategy data for email
            def build_strategy_email_data(comp) -> StrategyEmailData:
                # Build legs description
                legs_desc = []
                for opt, sign in zip(comp.all_options, comp.signs):
                    position = "Long" if sign > 0 else "Short"
                    opt_type = opt.option_type.capitalize()
                    legs_desc.append(f"{position} {opt_type} {opt.strike:.4f}")
                
                return StrategyEmailData(
                    name=comp.strategy_name,
                    score=comp.score,
                    premium=comp.premium,
                    max_profit=comp.max_profit,
                    max_loss=comp.max_loss,
                    profit_at_target=comp.profit_at_target,
                    profit_at_target_pct=comp.profit_at_target_pct,
                    average_pnl=comp.average_pnl,
                    sigma_pnl=comp.sigma_pnl,
                    total_delta=comp.total_delta,
                    total_gamma=comp.total_gamma,
                    total_vega=comp.total_vega,
                    total_theta=comp.total_theta,
                    avg_implied_volatility=comp.avg_implied_volatility,
                    breakeven_points=comp.breakeven_points,
                    legs_description=legs_desc
                )
            
            best_strategy_data = build_strategy_email_data(comparisons_list[0])
            top_strategies_data = [build_strategy_email_data(c) for c in comparisons_list[:5]]
        
        email_link = generate_mailto_link(
            ui_params=params, 
            scenarios=scenarios_list, 
            filters_data=filter, 
            scoring_weights=scoring_weights,
            best_strategy=best_strategy_data,
            top_strategies=top_strategies_data
        )
        st.markdown(f'<a href="{email_link}" target="_blank" style="text-decoration:none;">📧 <b>Send Configuration by Email</b></a>', unsafe_allow_html=True)

    # ========================================================================
    # MAIN AREA
    # ========================================================================

    compare_button = st.button(
        "Run Comparison", type="primary", use_container_width=True
    )

    # Déterminer quelle source de stratégies utiliser
    all_comparisons = None
    best_target_price = None
    # Utiliser les stratégies chargées si disponibles

    if compare_button:
        # ====================================================================
        # STEP 1: Full processing via main function
        # ====================================================================

        with st.spinner(
            f"🔄 Generating and comparing strategies (max {params.max_legs} legs)..."
        ):
            # Call main function doing EVERYTHING
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

            # Check results
            if not best_strategies:
                st.error("❌ No strategy generated")
                return

            display_success_stats(stats)

        # Use best_strategies for display
        all_comparisons = best_strategies

        if not all_comparisons:
            st.error("❌ No strategy available")
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
    # TABS FOR DISPLAY
    # ====================================================================

    tab1, tab2 = st.tabs(["Overview", "P&L Diagram"])

    # Display each tab with its dedicated module
    with tab1:
        display_overview_tab(comparisons)

    with tab2:
        display_payoff_tab(top_5_comparisons, best_target_price, mixture) #type: ignore

# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

if __name__ == "__main__":
    main()
