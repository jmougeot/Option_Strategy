import streamlit as st
from typing import Dict, List


# All scoring fields with their labels
SCORING_FIELDS = {
    "avg_pnl_levrage": ("Leverage of expected gain", 0),
    "roll_quarterly": ("Roll into next quarter", 0),
    "max_loss": ("Tail Risk Penalty", 0),
    "average_pnl": ("Expected gain at expiry", 100),
    "avg_intra_life_pnl": ("Avg Intra-Life P&L", 0),
    "premium": ("Premium", 0),
}

ADVENCED_SCORING_FIELDS = {
    "sigma_pnl": ("Standard deviation", 0),
    "delta_neutral": ("Delta Neutral", 0),
    "gamma_low": ("Gamma Low", 0),
    "vega_low": ("Vega Low", 0),
    "theta_positive": ("Theta Positive", 0),
    "implied_vol_moderate": ("Moderate IV", 0),
    "delta_levrage": ("Leverage with delta", 0),
}

# Presets for quick-add weight sets
WEIGHT_PRESETS: Dict[str, Dict[str, float]] = {
    "Pure Gain": {"average_pnl": 1.0},
    "Gain + Tail Risk": {"average_pnl": 0.7, "max_loss": 0.3},
    "Gain + Intra-Life": {"average_pnl": 0.6, "avg_intra_life_pnl": 0.4},
    "Balanced": {"average_pnl": 0.5, "max_loss": 0.2, "avg_intra_life_pnl": 0.3},
    "Leverage": {"avg_pnl_levrage": 0.6, "average_pnl": 0.4},
    "Premium Income": {"premium": 0.5, "average_pnl": 0.3, "max_loss": 0.2},
    "Roll + Gain": {"roll_quarterly": 0.4, "average_pnl": 0.6},
    "Conservative": {"average_pnl": 0.4, "max_loss": 0.4, "sigma_pnl": 0.2},
}


# ============================================================================
# Single weight set editor (one row in the multi-weight table)
# ============================================================================

def _weight_row_editor(index: int, defaults: Dict[str, float]) -> Dict[str, float]:
    """Renders input fields for a single weight set and returns the dict."""
    weights: Dict[str, float] = {}
    cols = st.columns(len(SCORING_FIELDS))
    for col_idx, (field_name, (label, _)) in enumerate(SCORING_FIELDS.items()):
        default_val = int(defaults.get(field_name, 0) * 100)
        with cols[col_idx]:
            val = st.number_input(
                label,
                min_value=0,
                max_value=100,
                value=default_val,
                step=1,
                key=f"mw_{index}_{field_name}",
            ) / 100
            weights[field_name] = val

    # Advanced fields: keep defaults (0) unless overridden
    for field_name, (_, default_value) in ADVENCED_SCORING_FIELDS.items():
        weights[field_name] = defaults.get(field_name, default_value)

    return weights


# ============================================================================
# Public API
# ============================================================================

def scoring_weights_block() -> List[Dict[str, float]]:
    """
    Renders the multi-weight scoring UI in the Streamlit sidebar.

    Returns a **list** of weight dicts.  Each dict maps metric name → weight
    (0–1 scale).  The list always has at least one element.
    """
    st.subheader("Score Weighting")

    # ---- session state bootstrap ----
    if "weight_sets" not in st.session_state:
        # Start with one default set
        st.session_state.weight_sets = [
            {k: v / 100 for k, (_, v) in {**SCORING_FIELDS, **ADVENCED_SCORING_FIELDS}.items()}
        ]

    weight_sets: List[Dict[str, float]] = st.session_state.weight_sets

    # ---- Render each weight set ----
    result: List[Dict[str, float]] = []

    for i, ws in enumerate(weight_sets):
        active_desc = ", ".join(f"{k} {v:.0%}" for k, v in ws.items() if v > 0)
        with st.expander(f"Weight set #{i + 1}  —  {active_desc or 'empty'}", expanded=(i == 0)):
            edited = _weight_row_editor(i, ws)
            result.append(edited)

            # Remove button (only if more than 1 set)
            if len(weight_sets) > 1:
                if st.button(f"🗑 Remove set #{i + 1}", key=f"rm_ws_{i}"):
                    weight_sets.pop(i)
                    st.session_state.weight_sets = weight_sets
                    st.rerun()

    # ---- Add set controls ----
    col_add, col_preset = st.columns(2)
    with col_add:
        if st.button("➕ Add weight set"):
            # Copy the last set as starting point
            weight_sets.append(dict(result[-1]))
            st.session_state.weight_sets = weight_sets
            st.rerun()
    with col_preset:
        preset_name = st.selectbox(
            "Add from preset",
            options=[""] + list(WEIGHT_PRESETS.keys()),
            key="preset_selector",
        )
        if preset_name:
            base = {k: 0.0 for k in {**SCORING_FIELDS, **ADVENCED_SCORING_FIELDS}}
            base.update({k: v for k, v in WEIGHT_PRESETS[preset_name].items()})
            weight_sets.append(base)
            st.session_state.weight_sets = weight_sets
            st.rerun()

    # Persist
    st.session_state.weight_sets = [dict(r) for r in result]

    return result
