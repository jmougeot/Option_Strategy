"""
Email Generator Page
====================
Compose a structured trade recommendation email.
All fields are pre-filled from the current session (params, filter, scenarios, top strategies).
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from myproject.app.data_types import FutureData
from myproject.app.widget_payoff import create_payoff_diagram
from myproject.share_result.email_utils import build_email_template_data, create_email_with_images
from myproject.share_result.generate_pdf import create_pdf_report
from myproject.strategy.strategy_class import StrategyComparison

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

MONTH_NAMES = {
    "F": "January", "G": "February", "H": "March", "K": "April",
    "M": "June",    "N": "July",     "Q": "August", "U": "September",
    "V": "October", "X": "November", "Z": "December",
}


def _expiry_code(params) -> str:
    if params is None:
        return ""
    m = params.months[0] if params.months else ""
    y = params.years[0]  if params.years  else ""
    return f"{params.underlying}{m}{y}"


def _expiry_label(params) -> str:
    if params is None:
        return ""
    m = params.months[0] if params.months else ""
    y = params.years[0]  if params.years  else ""
    year_str = f"20{y}" if isinstance(y, int) and y < 100 else str(y)
    return f"{MONTH_NAMES.get(m, m)} {year_str}"


def _bp(val: float) -> int:
    return int(round(val * 10_000))


def _strat_summary_line(s: StrategyComparison, ref: str) -> str:
    sign = "BUY" if (s.premium or 0) >= 0 else "SELL"
    prem = abs(s.premium or 0)
    delta = getattr(s, "total_delta", 0.0)
    return f"{sign} {s.strategy_name}, mkt is {prem:.4f}, reference {ref}, delta: {delta:+.3f}"


# ──────────────────────────────────────────────────────────────────────────────
# Strategy block (one per recommended trade)
# ──────────────────────────────────────────────────────────────────────────────

def _strategy_block(idx: int, s: StrategyComparison,
                    ref: str, nb_screened: int, nb_kept: int) -> dict:
    st.markdown(f"---\n### Strategy {idx}")

    summary  = _strat_summary_line(s, ref)
    prem     = abs(s.premium or 0)
    avg_pnl  = getattr(s, "average_pnl",    0.0) or 0.0
    max_pft  = getattr(s, "max_profit",      0.0) or 0.0
    delta    = getattr(s, "total_delta",     0.0)  
    lvg      = getattr(s, "avg_pnl_levrage", 0.0) or 0.0
    bp_pts   = getattr(s, "breakeven_points", []) or []
    max_pft_at = ref

    try:
        if s.pnl_array is not None and s.prices is not None and len(s.pnl_array) > 0:
            max_pft_at = f"{float(s.prices[int(np.argmax(s.pnl_array))]):.4f}"
    except Exception:
        pass

    breakeven_str = " / ".join(f"{b:.4f}" for b in bp_pts)

    col1, col2 = st.columns([4, 1])
    with col1:
        line = st.text_input(f"Summary line #{idx}", value=summary, key=f"email_line_{idx}")
    with col2:
        st.text_input("Direction", value="BUY" if prem >= 0 else "SELL",
                      key=f"email_dir_{idx}", disabled=True)

    commentary = st.text_area(
        f"Why this strategy? #{idx}",
        value="",
        height=80,
        key=f"email_comment_{idx}",
        placeholder="The model, and we, chose this strategy because ..."
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        e_prem  = st.number_input("Premium",      value=float(prem),    format="%.4f", key=f"ep_{idx}")
        e_avg   = st.number_input("Avg P&L",      value=float(avg_pnl), format="%.4f", key=f"ea_{idx}")
    with c2:
        e_mpft  = st.number_input("Max Profit",   value=float(max_pft), format="%.4f", key=f"em_{idx}")
        e_mpftat = st.text_input("At price",      value=max_pft_at,                     key=f"ema_{idx}")
    with c3:
        e_lvg   = st.number_input("Leverage",     value=float(lvg),     format="%.2f", key=f"el_{idx}")
        e_be    = st.text_input("Breakeven(s)",   value=breakeven_str,                  key=f"eb_{idx}")

    return {
        "idx": idx, "line": line, "commentary": commentary,
        "premium": e_prem, "avg_pnl": e_avg,
        "max_profit": e_mpft, "max_profit_at": e_mpftat,
        "leverage": e_lvg, "breakeven": e_be,
        "nb_screened": nb_screened, "nb_kept": nb_kept,
    }

# ──────────────────────────────────────────────────────────────────────────────
# Main page
# ──────────────────────────────────────────────────────────────────────────────

def run_email():
    st.header("Generate Email")

    # ── Pull session state ───────────────────────────────────────────────────
    params      = st.session_state.get("_params_widget")
    scenarios   = st.session_state.get("_scenarios_widget")
    flt         = st.session_state.get("_filter_widget")
    comparisons: Optional[List[StrategyComparison]] = st.session_state.get("comparisons")
    future_data: FutureData = st.session_state.get("future_data", FutureData())
    stats: dict = st.session_state.get("stats", {})

    nb_screened = stats.get("nb_strategies_possibles", 0)
    nb_kept     = stats.get("nb_strategies_classees",  0)

    ref_price   = f"{future_data.underlying_price:.4f}" \
                  if (future_data and future_data.underlying_price) else ""
    expiry_code = _expiry_code(params)
    expiry_lbl  = _expiry_label(params)

    target_price = uncert_left = uncert_right = ""
    if scenarios and scenarios.centers:
        target_price = f"{scenarios.centers[0]:.4f}"
        uncert_left  = str(_bp(scenarios.std_devs[0]))   if scenarios.std_devs   else ""
        uncert_right = str(_bp(scenarios.std_devs_r[0])) if scenarios.std_devs_r else ""

    tail_left   = f"{abs(flt.max_loss_left):.4f}"  if flt else ""
    tail_right  = f"{abs(flt.max_loss_right):.4f}" if flt else ""
    limit_left  = f"{flt.limit_left:.4f}"          if flt else ""
    limit_right = f"{flt.limit_right:.4f}"         if flt else ""
    open_risk   = "allowed" if (flt and flt.ouvert_gauche > 0) else "not allowed"

    # ── Header ───────────────────────────────────────────────────────────────
    st.subheader("Header")
    c1, c2 = st.columns(2)
    with c1:
        client_name = st.text_input("Client name",  value="",        key="email_client",
                                    placeholder="John Smith")
    with c2:
        signature   = st.text_input("Your signature", value="",      key="email_sig",
                                    placeholder="Your name / BGC")

    c1, c2, c3 = st.columns(3)
    with c1:
        f_expiry   = st.text_input("Expiry code",   value=expiry_code,  key="email_expiry")
    with c2:
        f_target   = st.text_input("Target price",  value=target_price, key="email_target")
    with c3:
        f_tdate    = st.text_input("Target date",   value=expiry_lbl,   key="email_tdate")

    # ── Risk Criteria ────────────────────────────────────────────────────────
    st.subheader("Risk Criteria")
    c1, c2, c3 = st.columns(3)
    with c1:
        f_und_price   = st.text_input("Underlying price",          value=ref_price,    key="email_uprice")
        f_uncert_l    = st.text_input("Uncertainty left (bp)",     value=uncert_left,  key="email_uncl")
        f_uncert_r    = st.text_input("Uncertainty right (bp)",    value=uncert_right, key="email_uncr")
    with c2:
        f_tail_l      = st.text_input("Tail risk downside (ticks)", value=tail_left,   key="email_taill")
        f_tail_r      = st.text_input("Tail risk upside (ticks)",   value=tail_right,  key="email_tailr")
        f_lim_l       = st.text_input("Starting from (left)",       value=limit_left,  key="email_liml")
        f_lim_r       = st.text_input("Starting from (right)",      value=limit_right, key="email_limr")
    with c3:
        f_open        = st.selectbox("1x2 open risk", ["allowed", "not allowed"],
                                     index=0 if open_risk == "allowed" else 1,
                                     key="email_open")
        f_max_legs    = st.text_input("Max legs",      value=str(params.max_legs) if params else "",
                                      key="email_legs")
        f_min_short   = st.text_input("Min short premium",
                                      value=f"{flt.min_premium_sell:.4f}" if flt else "",
                                      key="email_minshort")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        f_pmin  = st.text_input("Price min",  value=f"{params.price_min:.4f}"  if params else "", key="email_pmin")
    with c2:
        f_pmax  = st.text_input("Price max",  value=f"{params.price_max:.4f}"  if params else "", key="email_pmax")
    with c3:
        f_pstep = st.text_input("Tick size",  value=f"{params.price_step}"     if params else "", key="email_pstep")
    with c4:
        f_dmin  = st.text_input("Delta min",  value=f"{flt.delta_min}"         if flt    else "", key="email_dmin")
    with c5:
        f_dmax  = st.text_input("Delta max",  value=f"{flt.delta_max}"         if flt    else "", key="email_dmax")

    # ── Strategies ───────────────────────────────────────────────────────────
    st.subheader("Strategies")

    if not comparisons:
        st.warning("No strategies in session — run the strategy screener first.")
        strat_data = []
        selected_comparisons_for_payoff = []
        n_strats   = 0
    else:
        # Build human-readable labels for every available strategy
        strat_labels = [
            f"#{i + 1} — {s.strategy_name}  (prem: {abs(s.premium or 0):.4f})"
            for i, s in enumerate(comparisons)
        ]

        n_strats = int(st.number_input(
            "Number of strategies to include", min_value=1,
            max_value=min(10, len(comparisons)),
            value=min(3, len(comparisons)), step=1, key="email_nstrats"
        ))

        # One selectbox per slot — default to i-th strategy but fully overridable
        # Keys used inside _strategy_block(idx) that need resetting on change
        _BLOCK_KEYS = ["email_line_{}", "email_dir_{}", "email_comment_{}",
                       "ep_{}", "ea_{}", "em_{}", "ema_{}", "el_{}", "eb_{}"]

        selected_indices: list[int] = []
        cols = st.columns(min(n_strats, 3))
        for slot in range(n_strats):
            default_idx = min(slot, len(comparisons) - 1)
            with cols[slot % len(cols)]:
                chosen_label = st.selectbox(
                    f"Strategy {slot + 1}",
                    options=strat_labels,
                    index=default_idx,
                    key=f"email_strat_sel_{slot}",
                )
            chosen_idx = strat_labels.index(chosen_label)

            # If the user picked a different strategy for this slot, wipe the
            # stale cached widget values so they re-initialise from the new strategy.
            prev_key = f"_email_prev_sel_{slot}"
            if st.session_state.get(prev_key) != chosen_idx:
                idx = slot + 1
                for tmpl in _BLOCK_KEYS:
                    st.session_state.pop(tmpl.format(idx), None)
                st.session_state[prev_key] = chosen_idx

            selected_indices.append(chosen_idx)

        strat_data = [
            _strategy_block(slot + 1, comparisons[selected_indices[slot]],
                            ref_price or f_und_price, nb_screened, nb_kept)
            for slot in range(n_strats)
        ]
        selected_comparisons_for_payoff = [
            comparisons[selected_indices[slot]] for slot in range(n_strats)
        ]

    # ── Auto email body (always computed from current form values) ────────────
    def _ss(key, fallback=""):
        return st.session_state.get(key, fallback) or fallback

    fields = {
        "client_name":      _ss("email_client", "XXX"),
        "expiry_code":      _ss("email_expiry", expiry_code),
        "target":           _ss("email_target", target_price),
        "target_date":      _ss("email_tdate",  expiry_lbl),
        "underlying_price": _ss("email_uprice", ref_price),
        "uncert_left":      _ss("email_uncl",   uncert_left),
        "uncert_right":     _ss("email_uncr",   uncert_right),
        "tail_left":        _ss("email_taill",  tail_left),
        "tail_right":       _ss("email_tailr",  tail_right),
        "limit_left":       _ss("email_liml",   limit_left),
        "limit_right":      _ss("email_limr",   limit_right),
        "open_risk":        _ss("email_open",   open_risk),
        "max_legs":         _ss("email_legs"),
        "price_min":        _ss("email_pmin"),
        "price_max":        _ss("email_pmax"),
        "price_step":       _ss("email_pstep"),
        "min_short":        _ss("email_minshort"),
        "delta_min":        _ss("email_dmin"),
        "delta_max":        _ss("email_dmax"),
        "signature":        _ss("email_sig", "XXX"),
    }


    c1, c2 = st.columns(2)
    with c1:
        if st.button("Send Email (Outlook)"):
            _params  = st.session_state.get("_params_widget")
            _filter  = st.session_state.get("_filter_widget")
            _weights = st.session_state.get("_scoring_weights")
            _mixture = st.session_state.get("mixture")
            if _params and _filter and _weights and _mixture:
                template_data = build_email_template_data(_params, _filter, _weights)
                success = create_email_with_images(
                    template_data=template_data,
                    mixture=_mixture,
                    selected_comparisons=selected_comparisons_for_payoff or None,
                    fields=fields,
                    strat_data=strat_data,
                    params=_params,
                )
                if success:
                    st.success("Email opened in Outlook with images!")
                else:
                    st.error("Error opening Outlook.")
            else:
                st.warning("Params/filter not available in session.")
    with c2:
        if st.button("Generate PDF Report"):
            _params  = st.session_state.get("_params_widget")
            _filter  = st.session_state.get("_filter_widget")
            _weights = st.session_state.get("_scoring_weights")
            _mixture = st.session_state.get("mixture")
            if _params and _filter and _weights and selected_comparisons_for_payoff:
                template_data = build_email_template_data(_params, _filter, _weights)
                pdf_bytes = create_pdf_report(
                    template_data=template_data,
                    comparisons=selected_comparisons_for_payoff,
                    mixture=_mixture,
                )
                if pdf_bytes:
                    st.session_state["pdf_bytes"] = pdf_bytes
                    st.session_state["pdf_filename"] = (
                        f"Strategy_{fields['expiry_code']}"
                        f"_{datetime.now().strftime('%Y-%m-%d')}.pdf"
                    )
                    st.success("PDF generated!")
                    st.rerun()
                else:
                    st.error("Error generating PDF.")
            else:
                st.warning("Select strategies and ensure params are loaded.")

    if "pdf_bytes" in st.session_state and st.session_state["pdf_bytes"]:
        st.download_button(
            label="Download PDF",
            data=st.session_state["pdf_bytes"],
            file_name=st.session_state.get("pdf_filename", "report.pdf"),
            mime="application/pdf",
        )