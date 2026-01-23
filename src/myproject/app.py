"""
Streamlit Interface for Options Strategy Comparison
Description: Web user interface to compare options strategies
"""

import streamlit as st
from datetime import datetime
from myproject.app.main import process_bloomberg_to_strategies
from myproject.app.styles import inject_css
from myproject.app.params_widget import sidebar_params
from myproject.app.scenarios_widget import scenario_params
from myproject.app.scoring_widget import scoring_weights_block
from myproject.app.tabs import display_overview_tab, display_payoff_tab
from myproject.app.processing import (
    process_comparison_results,
    save_to_session_state,
)
from myproject.app.filter_widget import filter_params
from myproject.app.progress_tracker import ProgressTracker
from myproject.app.image_saver import save_all_diagrams
from myproject.app.email_utils import StrategyEmailData, create_email_with_images, create_pdf_report



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
        
        # Use session state scenarios which are list of dicts
        scenarios_list = st.session_state.get("scenarios", [])
        
        # Get best strategy info from session state if available
        best_strategy_data = None
        top_strategies_data = None
        diagram_path = st.session_state.get("diagram_path", None)
        top5_summary_path = st.session_state.get("top5_summary_path", None)
        
        if "comparisons" in st.session_state and st.session_state.comparisons:
            comparisons_list = st.session_state.comparisons
            
            # Build detailed strategy data for email
            def build_strategy_email_data(comp, diag_path=None, top5_path=None) -> StrategyEmailData:
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
                    legs_description=legs_desc,
                    diagram_path=diag_path,
                    top5_summary_path=top5_path
                )
            
            best_strategy_data = build_strategy_email_data(comparisons_list[0], diagram_path, top5_summary_path)
            top_strategies_data = [build_strategy_email_data(c, top5_path=top5_summary_path) for c in comparisons_list[:10]] 
            # First strategy (best) also gets the diagram path
            if top_strategies_data:
                top_strategies_data[0] = build_strategy_email_data(comparisons_list[0], diagram_path, top5_summary_path)
        
        # Bouton pour envoyer l'email avec images intégrées via Outlook
        if st.button("📧 Send Email with Images (Outlook)"):
            # Récupérer les comparisons pour générer les images
            comparisons_for_email = st.session_state.get("comparisons", None)
            mixture_for_email = st.session_state.get("mixture", None)
            
            success = create_email_with_images(
                ui_params=params, 
                scenarios=scenarios_list, 
                filters_data=filter, 
                scoring_weights=scoring_weights,
                best_strategy=best_strategy_data,
                top_strategies=top_strategies_data,
                comparisons=comparisons_for_email,
                mixture=mixture_for_email
            )
            if success:
                st.success("✅ Email ouvert dans Outlook avec les images!")
            else:
                st.error("❌ Erreur lors de l'ouverture d'Outlook. Voir la console pour les détails.")
        
        # Bouton pour générer le PDF simple
        comparisons_for_pdf = st.session_state.get("comparisons", None)
        mixture_for_pdf = st.session_state.get("mixture", None)
        
        if comparisons_for_pdf:
            pdf_bytes = create_pdf_report(
                ui_params=params,
                scenarios=scenarios_list,
                filters_data=filter,
                scoring_weights=scoring_weights,
                best_strategy=best_strategy_data,
                comparisons=comparisons_for_pdf,
                mixture=mixture_for_pdf
            )
            if pdf_bytes:
                underlying_name = params.underlying if params.underlying else "Options"
                date_str = datetime.now().strftime('%Y-%m-%d')
                filename = f"Strategy_{underlying_name}_{date_str}.pdf"
                st.download_button(
                    label="📄 Download PDF Report",
                    data=pdf_bytes,
                    file_name=filename,
                    mime="application/pdf"
                )
        
        # Show saved diagram paths if available
        if st.session_state.get("diagram_path") or st.session_state.get("top5_summary_path"):
            st.markdown("---")
            st.markdown("**📁 Saved Diagrams**")
            if st.session_state.get("diagram_path"):
                st.caption(f" {st.session_state['diagram_path']}")
            if st.session_state.get("top5_summary_path"):
                st.caption(f" {st.session_state['top5_summary_path']}")

    # ========================================================================
    # MAIN AREA
    # ========================================================================

    compare_button = st.button("Run Comparison", type="primary", width="stretch")
    all_comparisons = None

    if compare_button:

        # Créer le tracker de progression
        progress_tracker = ProgressTracker(max_legs=params.max_legs)
        
        try:
            # Call main function doing EVERYTHING with progress tracking
            best_strategies, stats, mixture = process_bloomberg_to_strategies(
                brut_code=params.brut_code,
                underlying=params.underlying,
                months=params.months,
                years=params.years,
                strikes=params.strikes,
                price_min=params.price_min,
                price_max=params.price_max,
                max_legs=params.max_legs,
                scoring_weights=scoring_weights,
                scenarios=scenarios,  # type: ignore
                filter=filter,
                roll_expiries=params.roll_expiries,
                progress_tracker=progress_tracker,
            )

            # Check results
            if not best_strategies:
                st.error(" No strategy generated")
                return

            progress_tracker.complete(stats)
            
        except Exception as e:
            progress_tracker.error(f"Erreur: {str(e)}")
            st.error(f" Error during processing: {str(e)}")
            return

        # Use best_strategies for display
        all_comparisons = best_strategies

        if not all_comparisons:
            st.error(" No strategy available")
            return

        # Save to session_state (including scenarios)
        save_to_session_state(all_comparisons, params, scenarios)

        # Also save mixture for diagram export
        st.session_state["mixture"] = mixture
                
        payoff_path = save_all_diagrams(all_comparisons[:5], mixture)
        if payoff_path:
            st.session_state["diagram_path"] = payoff_path.get("payoff")
            st.session_state["top5_summary_path"] = payoff_path.get("summary")
            st.success(f"📁 Diagrams auto-saved to assets/payoff_diagrams/")

    # Si on arrive ici sans stratégies, ne rien afficher
    if not all_comparisons:
        return

    # Traiter et filtrer les résultats
    comparisons, top_5_comparisons = process_comparison_results(
        all_comparisons
    )

    # ====================================================================
    # TABS FOR DISPLAY
    # ====================================================================

    tab1, tab2 = st.tabs(["Overview", "P&L Diagram"])

    # Display each tab with its dedicated module
    with tab1:
        # Générer les labels de roll dynamiquement (ex: ["H6", "M6", "U6"])
        roll_labels = [f"{m}{y}" for m, y in params.roll_expiries] if params.roll_expiries else None
        display_overview_tab(comparisons, roll_labels=roll_labels)

    with tab2:
        display_payoff_tab(top_5_comparisons, mixture) #type: ignore

# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

if __name__ == "__main__":
    main()
