import streamlit as st
from dataclasses import dataclass
from myproject.app.utils import strike_list

@dataclass
class UIParams:
    underlying: str
    months: list[str]
    years: list[int]
    strike: float
    price_min: float
    price_max: float
    price_step: float
    max_legs: int
    top_n: int
    strikes: list[float]

def sidebar_params() -> UIParams:
    st.header("⚙️ Paramètres")

    c1, c2 = st.columns(2)
    with c1:
        underlying = st.text_input("Sous-jacent:", value="ER", help="Code Bloomberg (ER = EURIBOR)")
    with c2:
        years_input = st.text_input("Années:", value="6", help="6=2026, 7=2027 (séparées par virgule)")

    c1, c2 = st.columns(2)
    with c1:
        months_input = st.text_input("Mois d'expiration:", value="F,G,H,K,M,N",
                                     help="F=Jan, G=Feb, H=Mar, K=Apr, M=Jun, N=Jul, Q=Aug, U=Sep, V=Oct, X=Nov, Z=Dec")
    with c2:
        strike = st.number_input("Strike :", value=98.0, format="%.4f", help="Target Price")

    c1, c2 = st.columns(2)
    with c1:
        price_min = st.number_input("Prix Min ($)", value=97.750, step=0.0001, format="%.4f")
    with c2:
        price_max = st.number_input("Prix Max ($)", value=98.250, step=0.0001, format="%.4f")

    price_step = st.number_input("Pas de Prix ($)", value=0.0625, step=0.0001, format="%.4f")
    strikes = strike_list(price_min, price_max, price_step)

    with st.expander("Paramètres de génération", expanded=True):
        max_legs = st.slider("Nombre maximum de legs par stratégie:", 1, 4, 4)
        top_n = st.number_input("Nombre de meilleures structures à afficher:", value=10, min_value=1, max_value=100)

    years = [int(y.strip()) for y in years_input.split(",") if y.strip()]
    months = [m.strip() for m in months_input.split(",") if m.strip()]

    return UIParams(underlying, months, years, strike, price_min, price_max, price_step, max_legs, top_n, strikes)

def scoring_weights_block() -> dict:
    st.subheader("⚖️ Pondération du Score - COMPLET")
    
    with st.expander("📊 Personnaliser TOUS les poids de scoring", expanded=False):
        st.markdown("**Tous les attributs participent au scoring. Total doit être ~100%**")
        
        # MÉTRIQUES FINANCIÈRES
        st.markdown("### 💰 Métriques Financières (40%)")
        col1, col2 = st.columns(2)
        with col1:
            w_max_profit = st.slider("Max Profit", 0, 100, 10, 1) / 100
            w_rr = st.slider("Risque/Rendement", 0, 100, 10, 1) / 100
        with col2:
            w_zone = st.slider("Zone Profitable", 0, 100, 8, 1) / 100
            w_target = st.slider("Performance Cible", 0, 100, 8, 1) / 100
        
        # SURFACES
        st.markdown("### 📐 Surfaces (32%)")
        col1, col2, col3 = st.columns(3)
        with col1:
            w_surf_profit = st.slider("Surface Profit", 0, 100, 12, 1) / 100
        with col2:
            w_surf_loss = st.slider("Surface Loss (inversé)", 0, 100, 8, 1) / 100
        with col3:
            w_pl_ratio = st.slider("Ratio Profit/Loss", 0, 100, 12, 1) / 100
        
        # GREEKS
        st.markdown("### 🔢 Greeks (18%)")
        col1, col2 = st.columns(2)
        with col1:
            w_delta = st.slider("Delta Neutralité", 0, 100, 6, 1) / 100
            w_gamma = st.slider("Gamma Exposure", 0, 100, 4, 1) / 100
        with col2:
            w_vega = st.slider("Vega Exposure", 0, 100, 4, 1) / 100
            w_theta = st.slider("Theta Positif", 0, 100, 4, 1) / 100
        
        # VOLATILITÉ
        st.markdown("### 📊 Volatilité (4%)")
        w_vol = st.slider("Volatilité Implicite", 0, 100, 4, 1) / 100
        
        # BREAKEVENS
        st.markdown("### 🎯 Breakevens (6%)")
        col1, col2 = st.columns(2)
        with col1:
            w_be_count = st.slider("Nombre de Breakevens", 0, 100, 3, 1) / 100
        with col2:
            w_be_spread = st.slider("Écart des Breakevens", 0, 100, 3, 1) / 100
        
        # Calculer et afficher le total
        total = (w_max_profit + w_rr + w_zone + w_target + 
                w_surf_profit + w_surf_loss + w_pl_ratio +
                w_delta + w_gamma + w_vega + w_theta + 
                w_vol + w_be_count + w_be_spread)
        
        if total < 0.95 or total > 1.05:
            st.warning(f"⚠️ Total des poids: {total*100:.1f}% (devrait être proche de 100%)")
        else:
            st.success(f"✅ Total des poids: {total*100:.1f}%")
    
    return {
        # Métriques financières
        "max_profit": w_max_profit,
        "risk_reward": w_rr,
        "profit_zone": w_zone,
        "target_performance": w_target,
        # Surfaces
        "surface_profit": w_surf_profit,
        "surface_loss": w_surf_loss,
        "profit_loss_ratio": w_pl_ratio,
        # Greeks
        "delta_neutral": w_delta,
        "gamma_exposure": w_gamma,
        "vega_exposure": w_vega,
        "theta_positive": w_theta,
        # Volatilité
        "implied_vol": w_vol,
        # Breakevens
        "breakeven_count": w_be_count,
        "breakeven_spread": w_be_spread,
    }
