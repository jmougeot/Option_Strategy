"""
Streamlit Interface for Options Strategy Comparison
Description: Web user interface to compare options strategies
"""

import streamlit as st
from datetime import datetime
from typing import Dict, List

from myproject.app.styles import inject_css
from myproject.app.params_widget import sidebar_params
from myproject.app.scenarios_widget import scenario_params
from myproject.app.scoring_widget import scoring_weights_block
from myproject.app.filter_widget import filter_params
from myproject.app.history_tab import init_history, apply_pending_restore
from myproject.share_result.email_utils import build_email_template_data, StrategyEmailData, create_email_with_images
from myproject.share_result.generate_pdf import create_pdf_report
from myproject.app.pages.overview import run as overview_run
from myproject.app.pages.history import run as history_run
from myproject.app.pages.help import run as help_run


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="M2O",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()


# ============================================================================
# MAIN
# ============================================================================

def main():
    init_history()
    apply_pending_restore()

    # Header
    # col_left, col_center, col_right = st.columns([2, 2, 1])
    # with col_center:
    #     st.image("./assets/m2o_logo.png", width=400)

    # ========================================================================
    # SIDEBAR - Parameters + Navigation
    # ========================================================================

    with st.sidebar:
        scenarios = scenario_params()
        st.markdown("---")
        params = sidebar_params()
        filter = filter_params()
        scoring_weights = scoring_weights_block()

        # Store widget outputs in session_state for the pages
        st.session_state["_params_widget"] = params
        st.session_state["_scenarios_widget"] = scenarios
        st.session_state["_filter_widget"] = filter
        st.session_state["_scoring_weights"] = scoring_weights

        st.markdown("---")

        if st.button("📧 Send Email with Images (Outlook)"):
            comparisons_for_email = st.session_state.get("comparisons", None)
            mixture_for_email = st.session_state.get("mixture", None)
            template_data = build_email_template_data(params, filter, scoring_weights)
            success = create_email_with_images(
                template_data=template_data,
                comparisons=comparisons_for_email,
                mixture=mixture_for_email,
            )
            if success:
                st.success("✅ Email opened in Outlook with images!")
            else:
                st.error("❌ Error opening Outlook. See console for details.")

        if st.button("Generate PDF Report"):
            comparisons_for_pdf = st.session_state.get("comparisons", None)
            mixture_for_pdf = st.session_state.get("mixture", None)
            if comparisons_for_pdf:
                template_data = build_email_template_data(params, filter, scoring_weights)
                pdf_bytes = create_pdf_report(
                    template_data=template_data,
                    comparisons=comparisons_for_pdf,
                    mixture=mixture_for_pdf,
                )
                if pdf_bytes:
                    st.session_state["pdf_bytes"] = pdf_bytes
                    st.session_state["pdf_filename"] = (
                        f"Strategy_{params.underlying if params.underlying else 'Options'}"
                        f"_{datetime.now().strftime('%Y-%m-%d')}.pdf"
                    )
                    st.success("PDF generated successfully!")
                    st.rerun()
                else:
                    st.error("Error generating PDF. See console for details.")
            else:
                st.warning("No strategies to generate PDF. Run comparison first.")

        if "pdf_bytes" in st.session_state and st.session_state["pdf_bytes"]:
            st.download_button(
                label="Download PDF",
                data=st.session_state["pdf_bytes"],
                file_name=st.session_state.get("pdf_filename", "report.pdf"),
                mime="application/pdf",
            )

    # ========================================================================
    # PAGE NAVIGATION  (replaces st.tabs)
    # ========================================================================

    pages = st.navigation(
        [
            st.Page(overview_run, title="Overview", icon="📊", default=True, url_path="overview"),
            st.Page(history_run, title="History", icon="📜", url_path="history"),
            st.Page(help_run, title="Help", icon="📚", url_path="help"),
        ],
        position="top"
    )

    # Render navigation selector in main area
    pages.run()


# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
