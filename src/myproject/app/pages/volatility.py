"""
Volatility Page — Visualisation du smile de volatilité, skew et surface.
Affiche les IV des options importées, le slope Bachelier et les corrections warning.
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Optional

from myproject.option.option_class import Option
from myproject.strategy.strategy_class import StrategyComparison


# ============================================================================
# HELPERS
# ============================================================================

def _collect_options_from_session() -> List[Option]:
    """
    Récupère toutes les options importées depuis la session.
    Priorité: all_imported_options (complet) > extraction depuis les stratégies (partiel).
    """
    # 1. Source principale: toutes les options importées
    all_opts: Optional[List[Option]] = st.session_state.get("all_imported_options")
    if all_opts:
        options = sorted(all_opts, key=lambda o: o.strike)
        return options

    # 2. Fallback: extraire depuis les stratégies (partiel)
    comparisons: Optional[List[StrategyComparison]] = st.session_state.get("comparisons")
    if not comparisons:
        return []

    seen = set()
    options: List[Option] = []
    for comp in comparisons:
        for opt in comp.all_options:
            key = (opt.strike, opt.option_type, opt.expiration_month, opt.expiration_year)
            if key not in seen:
                seen.add(key)
                options.append(opt)

    options.sort(key=lambda o: o.strike)
    return options


def _split_calls_puts(options: List[Option]):
    """Sépare les calls et puts."""
    calls = [o for o in options if o.is_call()]
    puts = [o for o in options if o.is_put()]
    return calls, puts


# ============================================================================
# GRAPHIQUES
# ============================================================================
def _plot_skew(calls: List[Option], puts: List[Option], underlying_price: Optional[float]):
    """Skew de volatilité: différence put IV - call IV au même strike."""

    # Trouver les strikes communs
    call_dict = {o.strike: o.implied_volatility for o in calls if o.implied_volatility > 0}
    put_dict = {o.strike: o.implied_volatility for o in puts if o.implied_volatility > 0}

    common_strikes = sorted(set(call_dict.keys()) & set(put_dict.keys()))
    if not common_strikes:
        st.info("Pas assez de données pour le skew (besoin de calls + puts aux mêmes strikes).")
        return

    skew = [put_dict[k] - call_dict[k] for k in common_strikes]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=common_strikes,
        y=skew,
        marker_color=["#F44336" if s > 0 else "#2196F3" for s in skew],
        name="Skew (Put IV − Call IV)",
    ))

    if underlying_price and underlying_price > 0:
        fig.add_vline(x=underlying_price, line_dash="dash", line_color="gray")

    fig.update_layout(
        title="Volatility Skew — Put IV − Call IV",
        xaxis_title="Strike",
        yaxis_title="Skew (pp)",
        template="plotly_dark",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)


def _plot_premium_vs_strike(calls: List[Option], puts: List[Option], underlying_price: Optional[float]):
    """Premium (mid) vs Strike."""

    fig = go.Figure()

    for opts, name, color, symbol in [
        (calls, "Calls", "#2196F3", "circle"),
        (puts, "Puts", "#F44336", "diamond"),
    ]:
        good = [o for o in opts if o.status and o.premium > 0]
        warn = [o for o in opts if not o.status and o.premium > 0]

        if good:
            fig.add_trace(go.Scatter(
                x=[o.strike for o in good],
                y=[o.premium for o in good],
                mode="markers+lines",
                name=name,
                marker=dict(color=color, size=7, symbol=symbol),
                line=dict(color=color, width=1, dash="dot"),
            ))
        if warn:
            fig.add_trace(go.Scatter(
                x=[o.strike for o in warn],
                y=[o.premium for o in warn],
                mode="markers",
                name=f"{name} (corrigés)",
                marker=dict(color=color, size=9, symbol="x", line=dict(width=2, color="#FF9800")),
            ))

    if underlying_price and underlying_price > 0:
        fig.add_vline(x=underlying_price, line_dash="dash", line_color="gray")

    fig.update_layout(
        title="Premium vs Strike",
        xaxis_title="Strike",
        yaxis_title="Premium",
        template="plotly_dark",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)


def _plot_greeks(options: List[Option], underlying_price: Optional[float]):
    """Delta et Gamma vs Strike."""

    if not options:
        return

    fig = make_subplots(rows=1, cols=2, subplot_titles=("Delta vs Strike", "Gamma vs Strike"))

    calls = [o for o in options if o.is_call() and abs(o.delta) > 0]
    puts = [o for o in options if o.is_put() and abs(o.delta) > 0]

    for opts, name, color in [(calls, "Calls", "#2196F3"), (puts, "Puts", "#F44336")]:
        if opts:
            fig.add_trace(go.Scatter(
                x=[o.strike for o in opts],
                y=[o.delta for o in opts],
                mode="markers+lines",
                name=f"{name} Δ",
                marker=dict(color=color, size=6),
                line=dict(color=color, width=1),
            ), row=1, col=1)

            fig.add_trace(go.Scatter(
                x=[o.strike for o in opts],
                y=[o.gamma for o in opts],
                mode="markers+lines",
                name=f"{name} Γ",
                marker=dict(color=color, size=6),
                line=dict(color=color, width=1, dash="dash"),
                showlegend=False,
            ), row=1, col=2)

    fig.update_layout(
        template="plotly_dark",
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.08, xanchor="right", x=1),
    )
    fig.update_xaxes(title_text="Strike", row=1, col=1)
    fig.update_xaxes(title_text="Strike", row=1, col=2)
    fig.update_yaxes(title_text="Delta", row=1, col=1)
    fig.update_yaxes(title_text="Gamma", row=1, col=2)

    st.plotly_chart(fig, use_container_width=True)


def _options_table(options: List[Option]):
    """Tableau récapitulatif des options avec leurs IV et status."""
    import pandas as pd

    rows = []
    for o in options:
        rows.append({
            "Type": "Call" if o.is_call() else "Put",
            "Strike": o.strike,
            "Premium": round(o.premium, 6) if o.premium else 0.0,
            "Bid": round(o.bid, 6) if o.bid else 0.0,
            "Ask": round(o.ask, 6) if o.ask else 0.0,
            "IV (%)": round(o.implied_volatility, 2) if o.implied_volatility else 0.0,
            "Delta": round(o.delta, 4) if o.delta else 0.0,
            "Gamma": round(o.gamma, 6) if o.gamma else 0.0,
            "Vega": round(o.vega, 4) if o.vega else 0.0,
            "Theta": round(o.theta, 4) if o.theta else 0.0,
            "Status": "✅" if o.status else "⚠️ Corrigé",
            "Expiry": f"{o.expiration_month}{o.expiration_year}",
        })

    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "IV (%)": st.column_config.NumberColumn(format="%.2f"),
            "Premium": st.column_config.NumberColumn(format="%.6f"),
            "Delta": st.column_config.NumberColumn(format="%.4f"),
        },
    )


# ============================================================================
# PAGE PRINCIPALE
# ============================================================================

def run():
    """Volatility page content."""

    st.header("Volatility Analysis")

    options = _collect_options_from_session()

    if not options:
        st.info("Aucune donnée de volatilité disponible. Lancez une comparaison dans **Overview** d'abord.")
        return

    # Underlying price
    future_data = st.session_state.get("future_data")
    underlying_price = future_data.underlying_price if future_data and future_data.underlying_price else None

    calls, puts = _split_calls_puts(options)

    # Stats rapides
    n_warned = sum(1 for o in options if not o.status)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Options totales", len(options))
    with col2:
        st.metric("Calls", len(calls))
    with col3:
        st.metric("Puts", len(puts))
    with col4:
        st.metric("Corrigées (warning)", n_warned)

    # Sélecteur d'expiration si multiples
    expiries = sorted(set(f"{o.expiration_month}{o.expiration_year}" for o in options))
    if len(expiries) > 1:
        selected_expiry = st.selectbox("Expiration", expiries, index=0)
        options = [o for o in options if f"{o.expiration_month}{o.expiration_year}" == selected_expiry]
        calls, puts = _split_calls_puts(options)

    # Onglets
    tab_smile, tab_skew, tab_premium, tab_greeks, tab_table = st.tabs(
        ["Smile", "Premium", "Greeks", "Table"]
    )

    with tab_skew:
        _plot_skew(calls, puts, underlying_price)

    with tab_premium:
        _plot_premium_vs_strike(calls, puts, underlying_price)

    with tab_greeks:
        _plot_greeks(options, underlying_price)

    with tab_table:
        _options_table(options)
