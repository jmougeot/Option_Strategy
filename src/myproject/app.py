"""
Streamlit Interface for Options Strategy Comparison
Description: Web user interface to compare options strategies
"""

import streamlit as st
import uuid
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

from myproject.app.styles import inject_css
from myproject.app.params_widget import sidebar_params
from myproject.app.scenarios_widget import scenario_params
from myproject.app.scoring_widget import scoring_weights_block
from myproject.app.tabs import display_overview_tab
from myproject.app.payoff_diagram import create_payoff_diagram
from myproject.app.processing import (
    process_comparison_results,
    save_to_session_state,
)
from myproject.app.filter_widget import filter_params
from myproject.app.async_processing import (
    start_processing,
    check_processing_status,
    stop_processing,
)
from myproject.app.data_types import FutureData
from myproject.share_result.email_utils import StrategyEmailData, EmailTemplateData, create_email_with_images
from myproject.share_result.generate_pdf import create_pdf_report 


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
        
        
        if "comparisons" in st.session_state and st.session_state.comparisons:
            
            # Build detailed strategy data for email/PDF
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
                    legs_description=legs_desc,
                )
        
        
        # Build email template data from session state if available
        def build_email_template_data() -> EmailTemplateData:
            """Build EmailTemplateData from current UI parameters and comparisons."""
            underlying = params.underlying or "Options"
            
            # Find best strategies by different criteria
            comparisons_list = st.session_state.get("comparisons", [])
            best_strategies = []
            
            if comparisons_list and len(comparisons_list) > 0:
                # 1. Best overall (weighted score)
                best_overall = comparisons_list[0]
                delta_pct = int(best_overall.total_delta * 100) if best_overall.total_delta else 0
                delta_str = f"+{delta_pct}%" if delta_pct >= 0 else f"{delta_pct}%"
                best_strategies.append({
                    "label": "Best strategy overall with the weighted score",
                    "description": f"{best_overall.strategy_name} {best_overall.premium:.2f} Mid Price, {delta_str} delta"
                })
                
                # 2. Best for Roll (if roll data available - using first roll)
                roll_sorted = sorted([c for c in comparisons_list if hasattr(c, 'roll_pnl') and c.roll_pnl], 
                                    key=lambda x: x.roll_pnl[0] if x.roll_pnl else 0, reverse=True)
                if roll_sorted:
                    best_roll = roll_sorted[0]
                    delta_pct = int(best_roll.total_delta * 100) if best_roll.total_delta else 0
                    delta_str = f"+{delta_pct}%" if delta_pct >= 0 else f"{delta_pct}%"
                    best_strategies.append({
                        "label": "Best strategy for Roll",
                        "description": f"{best_roll.strategy_name} {best_roll.premium:.2f} Mid Price, {delta_str} delta"
                    })
                
                # 3. Best for cumulated roll (using sum of roll_pnl)
                cumul_sorted = sorted([c for c in comparisons_list if hasattr(c, 'roll_pnl') and c.roll_pnl],
                                     key=lambda x: sum(x.roll_pnl) if x.roll_pnl else 0, reverse=True)
                if cumul_sorted:
                    best_cumul = cumul_sorted[0]
                    delta_pct = int(best_cumul.total_delta * 100) if best_cumul.total_delta else 0
                    delta_str = f"+{delta_pct}%" if delta_pct >= 0 else f"{delta_pct}%"
                    best_strategies.append({
                        "label": "Best strategy for cumulated Roll",
                        "description": f"{best_cumul.strategy_name} {best_cumul.premium:.2f} Mid Price, {delta_str} delta"
                    })
                
                # 4. Best for net average P&L at expiry
                pnl_sorted = sorted([c for c in comparisons_list if c.average_pnl], 
                                   key=lambda x: x.average_pnl or 0, reverse=True)
                if pnl_sorted:
                    best_pnl = pnl_sorted[0]
                    delta_pct = int(best_pnl.total_delta * 100) if best_pnl.total_delta else 0
                    delta_str = f"+{delta_pct}%" if delta_pct >= 0 else f"{delta_pct}%"
                    best_strategies.append({
                        "label": "Best strategy regarding net average P&L gain at expiry",
                        "description": f"{best_pnl.strategy_name} {best_pnl.premium:.2f} Mid Price, {delta_str} delta"
                    })
            
            target_desc = f"Target defined by scenarios in the UI for {underlying}."
            tail_risk_desc = "Tail risk constraints as defined in filters."
            max_risk_desc = f"Open exposure left: {filter.ouvert_gauche}, right: {filter.ouvert_droite}"
            strikes_desc = f"Looking at all options between {params.price_min:.4f} and {params.price_max:.4f}. Step: {params.price_step:.4f}. Min premium to sell: {filter.min_premium_sell:.3f}."
            delta_desc = f"Limited from {filter.delta_min:.0f} to {filter.delta_max:.0f} delta"
            premium_desc = f"{filter.max_premium:.2f} max"
            max_loss_desc = f"{filter.max_loss_left:.2f} on downside / {filter.max_loss_right:.2f} on upside"
            weighting_desc = ", ".join([f"{k}: {v:.0%}" for k, v in scoring_weights.items() if v > 0])
            
            # Get reference price from session state (underlying price)
            future_data_email = st.session_state.get("future_data", FutureData(0, None))
            ref_price = future_data_email.underlying_price if future_data_email else "N/A"
            ref_price_str = f"{ref_price:.4f}" if isinstance(ref_price, (int, float)) else str(ref_price)
            
            return EmailTemplateData(
                underlying=underlying,
                reference_price=ref_price_str,
                target_description=target_desc,
                tail_risk_description=tail_risk_desc,
                max_risk_description=max_risk_desc,
                strikes_screened_description=strikes_desc,
                delta_description=delta_desc,
                premium_max_description=premium_desc,
                max_loss_description=max_loss_desc,
                weighting_description=weighting_desc,
                max_legs=params.max_legs,
                best_strategies=best_strategies
            )
        
        # Button to send email with embedded images via Outlook
        if st.button("📧 Send Email with Images (Outlook)"):
            comparisons_for_email = st.session_state.get("comparisons", None)
            mixture_for_email = st.session_state.get("mixture", None)
            
            # Build template data
            template_data = build_email_template_data()
            
            success = create_email_with_images(
                template_data=template_data,
                comparisons=comparisons_for_email,
                mixture=mixture_for_email
            )
            if success:
                st.success("✅ Email opened in Outlook with images!")
            else:
                st.error("❌ Error opening Outlook. See console for details.")
        
        # Button to generate PDF
        if st.button("📄 Generate PDF Report"):
            comparisons_for_pdf = st.session_state.get("comparisons", None)
            mixture_for_pdf = st.session_state.get("mixture", None)
            
            if comparisons_for_pdf:
                # Build template data
                template_data = build_email_template_data()
                
                pdf_bytes = create_pdf_report(
                    template_data=template_data,
                    comparisons=comparisons_for_pdf,
                    mixture=mixture_for_pdf
                )
                if pdf_bytes:
                    # Store PDF in session state
                    st.session_state["pdf_bytes"] = pdf_bytes
                    st.session_state["pdf_filename"] = f"Strategy_{params.underlying if params.underlying else 'Options'}_{datetime.now().strftime('%Y-%m-%d')}.pdf"
                    st.success("✅ PDF generated successfully!")
                    st.rerun()
                else:
                    st.error("❌ Error generating PDF. See console for details.")
            else:
                st.warning("⚠️ No strategies to generate PDF. Run comparison first.")
        
        # Show download button if PDF exists in session state
        if "pdf_bytes" in st.session_state and st.session_state["pdf_bytes"]:
            st.download_button(
                label="💾 Download PDF",
                data=st.session_state["pdf_bytes"],
                file_name=st.session_state.get("pdf_filename", "report.pdf"),
                mime="application/pdf"
            )

    # ========================================================================
    # MAIN AREA - Processing Controls
    # ========================================================================
    
    # Initialize session state
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())[:8]
    if "processing" not in st.session_state:
        st.session_state.processing = False
    if "process" not in st.session_state:
        st.session_state.process = None

    # Callback for stop button
    def on_stop_click():
        if st.session_state.process is not None:
            stop_processing(st.session_state.process)
            st.session_state.processing = False
            st.session_state.process = None

    compare_button_column, stop_button_column = st.columns(2)
    
    with compare_button_column:
        compare_button = st.button(
            "Run Comparison", 
            type="primary", 
            width="stretch",
            disabled=st.session_state.processing
        )
    with stop_button_column:
        st.button(
            "⛔ STOP", 
            type="secondary", 
            width="stretch",
            on_click=on_stop_click
        )
    
    all_comparisons = None
    mixture = None
    future_data: FutureData = FutureData(98.0, None)

    # Check if we have a running process
    if st.session_state.processing and st.session_state.process is not None:
        is_running, is_complete, result, error = check_processing_status(
            st.session_state.session_id, 
            st.session_state.process
        )
        
        if is_complete:
            st.session_state.processing = False
            st.session_state.process = None
            
            if error:
                if "terminated" in error.lower():
                    st.warning("⛔ Processing was terminated by user")
                else:
                    st.error(f"❌ Error: {error}")
                return
            
            if result:
                best_strategies, stats, mixture, future_data = result
                
                if not best_strategies:
                    st.error("❌ No strategy generated")
                    return
                
                all_comparisons = best_strategies
                save_to_session_state(all_comparisons, params, scenarios)
                st.session_state["mixture"] = mixture
                st.session_state["future_data"] = future_data
                st.success("✅ Processing complete!")
            else:
                st.warning("⛔ Processing was terminated")
                return
        else:
            # Still running
            st.info("⏳ Processing in progress... Click STOP to terminate immediately.")
            st_autorefresh(interval=1000, limit=None, key="processing_refresh")

    elif compare_button and not st.session_state.processing:
        st.session_state.processing = True
        
        # Prepare params dict for subprocess
        _params = {
            "brut_code": params.brut_code,
            "underlying": params.underlying,
            "months": params.months,
            "years": params.years,
            "strikes": params.strikes,
            "price_min": params.price_min,
            "price_max": params.price_max,
            "max_legs": params.max_legs,
            "scoring_weights": scoring_weights,
            "scenarios": scenarios,
            "filter": filter,
            "roll_expiries": params.roll_expiries,
        }
        
        # Start background process
        process = start_processing(st.session_state.session_id, _params)
        st.session_state.process = process
        
        st.info("⏳ Starting processing...")
        st.rerun()
        
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
        # Afficher les infos du future en haut
        future_data = st.session_state.get("future_data", FutureData(0, None))
        if future_data:
            col_price, col_date = st.columns(2)
            with col_price:
                st.metric("📊 Underlying Price", f"{future_data.underlying_price:.4f}")
            with col_date:
                date_str = future_data.last_tradable_date if future_data.last_tradable_date else "N/A"
                st.metric("📅 Last Tradeable Date", date_str)
            st.markdown("---")
        
        # Générer les labels de roll dynamiquement (ex: ["H6", "M6", "U6"])
        roll_labels = [f"{m}{y}" for m, y in params.roll_expiries] if params.roll_expiries else None
        display_overview_tab(comparisons, roll_labels=roll_labels)

    with tab2:
        future_data = st.session_state.get("future_data", FutureData(0, None))
        underlying_price = future_data.underlying_price if future_data else 0
        create_payoff_diagram(top_5_comparisons, mixture, underlying_price) #type:ignore

# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
