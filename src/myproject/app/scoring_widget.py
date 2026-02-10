"""
Scoring Widget — Multi-weight ranking presets (R1–R7) + custom sets
====================================================================

Architecture:
  • RANKING_PRESETS  — 7 predefined weight configurations exposed as checkboxes.
    At least one must be active. Selecting several triggers multi-scoring in C++.
  • Custom sets      — unlimited user-defined weight sets (optional expander).
  • Return value     — ``List[Dict[str, float]]`` containing all *active* weight
    dicts (presets checked + custom sets).
"""

import streamlit as st
from typing import Dict, List


# ============================================================================
# Metric catalogue (keys used by C++ scorer)
# ============================================================================

SCORING_FIELDS: Dict[str, str] = {
    "avg_pnl_levrage":   "Leverage",
    "roll_quarterly":    "Roll",
    "avg_intra_life_pnl":"Dynamic Life",
    "average_pnl":       "Expected Gain",
    "max_loss":          "Tail Risk",
    "premium":           "Premium",
}

ADVANCED_SCORING_FIELDS: Dict[str, str] = {
    "sigma_pnl":            "Std Dev",
    "delta_neutral":        "Delta Neutral",
    "gamma_low":            "Gamma Low",
    "vega_low":             "Vega Low",
    "theta_positive":       "Theta Positive",
    "implied_vol_moderate": "Moderate IV",
    "delta_levrage":        "Leverage (delta)",
}

ALL_FIELDS = {**SCORING_FIELDS, **ADVANCED_SCORING_FIELDS}


# ============================================================================
# Predefined ranking presets  (R1–R7)
# Values are raw percentages — they'll be normalised by the C++ scorer.
# ============================================================================

RANKING_PRESETS: Dict[str, Dict[str, float]] = {
    "R1 — Leverage":              {"avg_pnl_levrage": 1.0},
    "R2 — Roll":                  {"roll_quarterly": 1.0},
    "R3 — Dynamic Life":          {"avg_intra_life_pnl": 1.0},
    "R4 — Balanced (L/R/D)":      {"avg_pnl_levrage": 0.33, "roll_quarterly": 0.33, "avg_intra_life_pnl": 0.34},
    "R5 — Roll + Leverage":       {"roll_quarterly": 0.50, "avg_pnl_levrage": 0.50},
    "R6 — Leverage + Dynamic":    {"avg_pnl_levrage": 0.50, "avg_intra_life_pnl": 0.50},
    "R7 — Dynamic + Leverage":    {"avg_intra_life_pnl": 0.50, "avg_pnl_levrage": 0.50},
}


# ============================================================================
# Helpers
# ============================================================================

def _make_full_weights(sparse: Dict[str, float]) -> Dict[str, float]:
    """Expand a sparse preset dict into a full dict with 0.0 for missing keys."""
    full = {k: 0.0 for k in ALL_FIELDS}
    full.update(sparse)
    return full


def _weight_row_editor(index: int, defaults: Dict[str, float]) -> Dict[str, float]:
    """Render editable number inputs for one custom weight set."""
    weights: Dict[str, float] = {}
    cols = st.columns(len(SCORING_FIELDS))
    for col_idx, (field_name, label) in enumerate(SCORING_FIELDS.items()):
        default_val = int(defaults.get(field_name, 0) * 100)
        with cols[col_idx]:
            val = st.number_input(
                label,
                min_value=0,
                max_value=100,
                value=default_val,
                step=1,
                key=f"custom_ws_{index}_{field_name}",
            ) / 100
            weights[field_name] = val

    # Advanced fields — keep existing value or 0
    for field_name in ADVANCED_SCORING_FIELDS:
        weights[field_name] = defaults.get(field_name, 0.0)

    return weights


def _preset_summary(preset: Dict[str, float]) -> str:
    """One-line description of a preset's active weights."""
    parts = []
    for k, v in preset.items():
        if v > 0:
            label = SCORING_FIELDS.get(k) or ADVANCED_SCORING_FIELDS.get(k, k)
            parts.append(f"{label} {v:.0%}")
    return ", ".join(parts) if parts else "—"


# ============================================================================
# Public API
# ============================================================================

def scoring_weights_block() -> List[Dict[str, float]]:
    """
    Renders the scoring panel in the Streamlit sidebar.

    Layout:
      1. Checkboxes for R1-R7 predefined rankings (at least one active).
      2. Optional expander for unlimited custom weight sets.

    Returns:
        List of active weight dicts (presets + custom sets).
    """
    st.subheader("Ranking Presets")

    # ---- Bootstrap session state ----
    if "preset_active" not in st.session_state:
        # Default: only R1 active
        st.session_state.preset_active = {name: (i == 0) for i, name in enumerate(RANKING_PRESETS)}
    if "custom_weight_sets" not in st.session_state:
        st.session_state.custom_weight_sets: List[Dict[str, float]] = []

    # ---- Render preset checkboxes ----
    active: Dict[str, bool] = {}
    for name, weights in RANKING_PRESETS.items():
        default = st.session_state.preset_active.get(name, False)
        checked = st.checkbox(
            f"**{name}**  ·  {_preset_summary(weights)}",
            value=default,
            key=f"preset_cb_{name}",
        )
        active[name] = checked

    st.session_state.preset_active = active

    # ---- Collect active preset weight dicts ----
    result: List[Dict[str, float]] = []
    for name, is_active in active.items():
        if is_active:
            result.append(_make_full_weights(RANKING_PRESETS[name]))

    # ---- Custom weight sets (optional) ----
    custom_sets: List[Dict[str, float]] = st.session_state.custom_weight_sets

    with st.expander(f"🔧 Custom weight sets ({len(custom_sets)})", expanded=False):
        edited_custom: List[Dict[str, float]] = []
        indices_to_remove: List[int] = []

        for i, ws in enumerate(custom_sets):
            st.markdown(f"**Custom #{i + 1}**")
            edited = _weight_row_editor(i, ws)
            edited_custom.append(edited)

            if st.button(f"🗑 Remove #{i + 1}", key=f"rm_custom_{i}"):
                indices_to_remove.append(i)

        # Handle removals
        if indices_to_remove:
            for idx in sorted(indices_to_remove, reverse=True):
                custom_sets.pop(idx)
            st.session_state.custom_weight_sets = custom_sets
            st.rerun()

        # Add button
        if st.button("➕ Add custom weight set"):
            base = _make_full_weights({"average_pnl": 1.0})
            custom_sets.append(base)
            st.session_state.custom_weight_sets = custom_sets
            st.rerun()

        # Persist edited values
        if edited_custom:
            st.session_state.custom_weight_sets = edited_custom

    # Add custom sets to result
    result.extend(st.session_state.custom_weight_sets)

    # Fallback: if nothing is selected, default to R1
    if not result:
        st.warning("⚠️ Aucun ranking sélectionné — R1 (Leverage) activé par défaut.")
        result = [_make_full_weights(RANKING_PRESETS["R1 — Leverage"])]

    return result

