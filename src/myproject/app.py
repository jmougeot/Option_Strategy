"""
Streamlit Interface for Options Strategy Comparison
Description: Web user interface to compare options strategies
"""

import streamlit as st
from datetime import datetime
from myproject.app.styles import inject_css
from myproject.app.widget_params import sidebar_params
from myproject.app.widget_scenario import scenario_params
from myproject.app.widget_scoring import scoring_weights_block
from myproject.app.widget_filter import filter_params
from myproject.share_result.email_utils import build_email_template_data, create_email_with_images
from myproject.share_result.generate_pdf import create_pdf_report
from myproject.app.pages.overview import run as overview_run
from myproject.app.pages.history import run as history_run
from myproject.app.pages.email import run_email
from myproject.app.pages.help import run as help_run
from myproject.app.pages.volatility import run as volatility_run
from myproject.app.pages.history import init_history, apply_pending_restore
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
        if params.unit == "64ème":
            filter.max_premium = filter.max_premium / 64
            filter.max_loss_right = filter.max_loss_right / 64
            filter.max_loss_left = filter.max_loss_left / 64
            filter.min_premium_sell = filter.min_premium_sell / 64

        # Store widget outputs in session_state for the pages
        st.session_state["_params_widget"] = params
        st.session_state["_scenarios_widget"] = scenarios
        st.session_state["_filter_widget"] = filter
        st.session_state["_scoring_weights"] = scoring_weights

        st.markdown("---")

    # ========================================================================
    # PAGE NAVIGATION  (replaces st.tabs)
    # ========================================================================

    overview_page = st.Page(overview_run, title="Overview", icon="📊", default=True, url_path="overview")

    pages = st.navigation(
        [
            overview_page,
            st.Page(volatility_run, title="Volatility", icon="📈", url_path="volatility"),
            st.Page(history_run, title="History", icon="📜", url_path="history"),
            st.Page(run_email, title= "Email", icon= "📊", url_path="email"),
            st.Page(help_run, title="Help", icon="📚", url_path="help"),
        ],
        position="top"
    )

    # Redirection automatique vers Overview après "Rerun pipeline" depuis Volatility
    # Flag séparé pour éviter la boucle : _redirect_to_overview est supprimé immédiatement
    if st.session_state.pop("_redirect_to_overview", False):
        st.switch_page(overview_page)

    # Render navigation selector in main area
    pages.run()


# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
