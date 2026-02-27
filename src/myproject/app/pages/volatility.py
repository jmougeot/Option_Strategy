"""
Volatility Page — Visualisation du smile de volatilité, skew et surface.
Affiche les IV des options importées, le slope Bachelier et les corrections warning.
"""

import streamlit as st
import plotly.graph_objects as go
from typing import List, Optional
from myproject.option.option_class import Option
from myproject.app.utils import split_calls_puts, collect_options_from_session

# ============================================================================
# GRAPHIQUES
# ============================================================================

def _plot_smile(calls: List[Option], puts: List[Option], underlying_price: Optional[float]):
    """
    Smile de volatilité unifié : une seule courbe par strike.
    - Si call ET put disponibles au même strike → moyenne des deux IV.
    - Si un seul disponible → on garde cette IV.
    - Les points corrigés (status=False) sont marqués d'un symbole différent.
    - Les anomalies SABR (sabr_is_anomaly=True) sont surlignées en rouge.
    """
    from collections import defaultdict

    # Index des calls et puts par strike
    calls_by_strike: dict = {o.strike: o for o in calls if o.implied_volatility > 0}
    puts_by_strike:  dict = {o.strike: o for o in puts  if o.implied_volatility > 0}

    all_strikes = sorted(set(calls_by_strike) | set(puts_by_strike))
    if not all_strikes:
        st.info("Aucune volatilité implicite disponible.")
        return

    # Construire le smile fusionné
    smile_x, smile_y = [], []
    sabr_x, sabr_y, sabr_model_y, sabr_labels = [], [], [], []
    warn_x, warn_y = [], []

    for K in all_strikes:
        c = calls_by_strike.get(K)
        p = puts_by_strike.get(K)

        ivs   = [o.implied_volatility for o in (c, p) if o is not None]
        iv_avg = float(sum(ivs) / len(ivs))

        # Point corrigé si au moins un des deux a status=False
        is_corrected = any(not o.status for o in (c, p) if o is not None)

        # Anomalie SABR : si l'un ou l'autre est flagué
        is_anomaly = any(getattr(o, "sabr_is_anomaly", False) for o in (c, p) if o is not None)

        if is_corrected:
            warn_x.append(K)
            warn_y.append(iv_avg)
        elif is_anomaly:
            sabr_x.append(K)
            sabr_y.append(iv_avg)
            # Récupérer la vol SABR modèle pour l'annotation
            sabr_vol_model = next(
                (getattr(o, "sabr_volatility", 0.0) for o in (c, p) if o is not None and getattr(o, "sabr_volatility", 0.0) > 0),
                0.0,
            )
            res_bp = (iv_avg - sabr_vol_model) * 10_000
            sabr_model_y.append(sabr_vol_model)
            sabr_labels.append(f"K={K:.3f}<br>mkt={iv_avg*1e4:.1f}bp<br>SABR={sabr_vol_model*1e4:.1f}bp<br>Δ={res_bp:+.1f}bp")
        else:
            smile_x.append(K)
            smile_y.append(iv_avg)

    fig = go.Figure()

    # ── Smile normal ──────────────────────────────────────────────────────────
    all_x = sorted(smile_x + warn_x + sabr_x)
    all_y_dict = dict(zip(smile_x, smile_y))
    all_y_dict.update(dict(zip(warn_x, warn_y)))
    all_y_dict.update(dict(zip(sabr_x, sabr_y)))
    line_y = [all_y_dict[k] for k in all_x]

    fig.add_trace(go.Scatter(
        x=all_x,
        y=line_y,
        mode="lines",
        name="Smile",
        line=dict(color="#2196F3", width=2),
        showlegend=True,
    ))

    if smile_x:
        fig.add_trace(go.Scatter(
            x=smile_x,
            y=smile_y,
            mode="markers",
            name="IV marché",
            marker=dict(color="#2196F3", size=8, symbol="circle"),
            showlegend=True,
        ))

    # ── Points corrigés (extrapolés) ─────────────────────────────────────────
    if warn_x:
        fig.add_trace(go.Scatter(
            x=warn_x,
            y=warn_y,
            mode="markers",
            name="Corrigé / extrapolé",
            marker=dict(color="#FF9800", size=10, symbol="x", line=dict(width=2)),
            showlegend=True,
        ))

    # ── Anomalies SABR ────────────────────────────────────────────────────────
    if sabr_x:
        fig.add_trace(go.Scatter(
            x=sabr_x,
            y=sabr_y,
            mode="markers+text",
            name="Anomalie SABR",
            marker=dict(color="#F44336", size=12, symbol="diamond",
                        line=dict(color="white", width=1)),
            text=[f"Δ={lbl.split('Δ=')[1].split('bp')[0]}bp" for lbl in sabr_labels],
            textposition="top center",
            textfont=dict(color="#F44336", size=9),
            customdata=sabr_labels,
            hovertemplate="%{customdata}<extra></extra>",
            showlegend=True,
        ))
        # Trait vertical reliant mkt au modèle SABR
        for K, iv_mkt, iv_model in zip(sabr_x, sabr_y, sabr_model_y):
            fig.add_trace(go.Scatter(
                x=[K, K], y=[iv_mkt, iv_model],
                mode="lines",
                line=dict(color="#F44336", width=1, dash="dot"),
                showlegend=False,
                hoverinfo="skip",
            ))
        # Carré SABR modèle
        fig.add_trace(go.Scatter(
            x=sabr_x,
            y=sabr_model_y,
            mode="markers",
            name="SABR (modèle)",
            marker=dict(color="#F44336", size=8, symbol="square-open",
                        line=dict(color="#F44336", width=2)),
            showlegend=True,
        ))

    # ── Forward ATM ───────────────────────────────────────────────────────────
    if underlying_price and underlying_price > 0:
        fig.add_vline(
            x=underlying_price, line_dash="dash", line_color="gray",
            annotation_text=f"Forward {underlying_price:.3f}",
            annotation_position="top right",
        )

    fig.update_layout(
        title="Volatility Smile — IV vs Strike (smile unifié Call+Put)",
        xaxis_title="Strike",
        yaxis_title="Implied Volatility",
        template="plotly_dark",
        height=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    st.plotly_chart(fig, width='stretch')


def _options_table(options: List[Option]):
    """Tableau récapitulatif des options — IV et Premium éditables, propagés aux objets Option."""
    import pandas as pd

    rows = []
    for o in options:
        rows.append({
            "Type":    "Call" if o.is_call() else "Put",
            "Expiry":  f"{o.expiration_month}{o.expiration_year}",
            "Strike":  o.strike,
            "Premium": round(o.premium, 6) if o.premium else 0.0,
            "Bid":     round(o.bid, 6) if o.bid else 0.0,
            "Ask":     round(o.ask, 6) if o.ask else 0.0,
            "IV (%)":  round(o.implied_volatility, 4) if o.implied_volatility else 0.0,
            "Delta":   round(o.delta, 4) if o.delta else 0.0,
            "Gamma":   round(o.gamma, 6) if o.gamma else 0.0,
            "Theta":   round(o.theta, 6) if o.theta else 0.0,
            "Status":  "Ok" if o.status else "⚠️ Corrigé",
        })

    df = pd.DataFrame(rows)

    # Colonnes éditables : IV et Premium uniquement
    editable = {"IV (%)", "Premium"}
    disabled_cols = [c for c in df.columns if c not in editable]
    edited = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        disabled=disabled_cols,
        column_config={
            "IV (%)":   st.column_config.NumberColumn("IV (%)", format="%.4f", min_value=0.0),
            "Premium":  st.column_config.NumberColumn("Premium", format="%.6f", min_value=0.0),
            "Delta":    st.column_config.NumberColumn(format="%.4f"),
            "Gamma":    st.column_config.NumberColumn(format="%.4f"),
            "Theta":    st.column_config.NumberColumn(format="%.4f"),
        },
        key="volatility_table_editor",
    )

    # Propager les modifications aux objets Option en session
    if edited is not None:
        changed = False
        for idx, row in edited.iterrows():
            o = options[idx]
            new_iv  = float(row["IV (%)"])
            new_prem = float(row["Premium"])
            if abs(new_iv - (o.implied_volatility or 0.0)) > 1e-8:
                o.implied_volatility = new_iv
                changed = True
            if abs(new_prem - (o.premium or 0.0)) > 1e-8:
                o.premium = new_prem
                changed = True
        if changed:
            # Forcer Streamlit à re-lire les options depuis session (smile se redessine)
            st.session_state["all_imported_options"] = st.session_state.get("all_imported_options", options)


# ============================================================================
# PAGE PRINCIPALE
# ============================================================================

def run():
    """Volatility page content."""

    st.header("Volatility Analysis")

    options = collect_options_from_session()

    if not options:
        st.info("Aucune donnée de volatilité disponible. Lancez une comparaison dans **Overview** d'abord.")
        return

    # Underlying price
    future_data = st.session_state.get("future_data")
    underlying_price = future_data.underlying_price if future_data and future_data.underlying_price else None

    calls, puts = split_calls_puts(options)

    # Onglets
    tab_smile, tab_table = st.tabs(
        ["Smile", "Table"]
    )

    with tab_smile:
        _plot_smile(calls, puts, underlying_price)

    with tab_table:
        _options_table(options)

        rerun_btn = st.button(
            "Rerun pipeline",
            type="primary",
            use_container_width=True,
        )

        if rerun_btn:
            # Snapshot des options actuelles (déjà mutées par l'éditeur)
            current_opts = st.session_state.get("all_imported_options", options)
            st.session_state["_prefilled_options"] = list(current_opts)
            st.session_state["_trigger_rerun_with_prefilled"] = True
            st.session_state["_redirect_to_overview"] = True
            st.rerun()
