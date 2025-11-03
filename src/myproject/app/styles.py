import streamlit as st
# ============================================================================
# STYLES CSS PERSONNALISÉS
# ============================================================================
CSS = """
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #1f77b4;
    }
    .winner-card {
        background-color: #d4edda;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 6px solid #28a745;
        margin: 1rem 0;
    }
    .warning-card {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ffc107;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0 24px;
        background-color: transparent;
        border-radius: 4px 4px 0 0;
        border: 1px solid rgba(128,128,128,0.2);
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: rgba(128,128,128,0.1);
    }
    .stTabs [aria-selected="true"] {
        background-color: rgba(31,119,180,0.1);
        border-bottom: 2px solid #1f77b4;
    }
</style>"""

def inject_css():
    """Injecte le style CSS global dans Streamlit."""
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

