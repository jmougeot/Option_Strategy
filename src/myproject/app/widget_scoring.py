import streamlit as st
from typing import Dict, List
import uuid


# ============================================================================
# Metric catalogue (keys used by C++ scorer)
# ============================================================================

SCORING_FIELDS: Dict[str, str] = {
    "avg_pnl_levrage":   "Leverage",
    "roll":             "Roll",
    "avg_intra_life_pnl":"Dynamic Life",
    "average_pnl":       "Expected Gain",
    "max_loss":          "Tail Risk",
    "premium":           "Premium",
}

ALL_FIELDS = {**SCORING_FIELDS}


# ============================================================================
# Predefined ranking presets  (R1–R7)
# ============================================================================

RANKING_PRESETS: Dict[str, Dict[str, float]] = {
    "R1 — Leverage":              {"avg_pnl_levrage": 1.0},
    "R2 — Roll":                  {"roll": 1.0},
    "R3 — Dynamic Life":          {"avg_intra_life_pnl": 1.0},
    "R4 — Balanced (L/R/D)":      {"avg_pnl_levrage": 0.33, "roll": 0.33, "avg_intra_life_pnl": 0.34},
    "R5 — Roll + Leverage":       {"roll": 0.50, "avg_pnl_levrage": 0.50},
    "R6 — Leverage + Dynamic":    {"avg_pnl_levrage": 0.50, "avg_intra_life_pnl": 0.50},
    "R7 — Dynamic + Leverage":    {"avg_intra_life_pnl": 0.50, "avg_pnl_levrage": 0.50},
}
fields_list = list(SCORING_FIELDS.items())
midpoint= len(fields_list)//2

# ============================================================================
# Helpers
# ============================================================================
def delete_weight(weight_id: str):
    """Delete custom weight set with given id from session state."""
    if len(st.session_state.custom_weight_sets) > 0:
        st.session_state.custom_weight_sets = [s for s in st.session_state.custom_weight_sets if s["id"] != weight_id]

def add_weight():
    """Add a new custom weight set with default values."""
    new_ws: Dict[str, object] = {"id": str(uuid.uuid4())}
    for k in ALL_FIELDS:
        new_ws[k] = 0.0
    st.session_state.custom_weight_sets.append(new_ws)

def _make_full_weights(sparse: Dict[str, float]) -> Dict[str, float]:
    """Expand a sparse preset dict into a full dict with 0.0 for missing keys."""
    full = {k: 0.0 for k in ALL_FIELDS}
    full.update(sparse)
    return full


def _weight_row_editor(weight_id: float, defaults: Dict[str, float]) -> Dict[str, float]:
    """Render editable number inputs for one custom weight set."""
    weights: Dict[str, float] = {}

    # First ligne 
    cols = st.columns(midpoint)
    for col_idx, (field_name, label) in enumerate(fields_list[:midpoint]):
        default_val = int(defaults.get(field_name, 0) * 100)
        with cols[col_idx]:
            val = st.number_input(
                label,
                min_value=0,
                max_value=100,
                value=default_val,
                step=1,
                key=f"custom_ws_{weight_id}_{field_name}",
            ) / 100
            weights[field_name] = val

    # Second ligne
    cols = st.columns(len(fields_list) - midpoint)
    for col_idx, (field_name, label) in enumerate(fields_list[midpoint:]):
        default_val = int(defaults.get(field_name, 0) * 100)
        with cols[col_idx]:
            val = st.number_input(
                label,
                min_value=0,
                max_value=100,
                value=default_val,
                step=1,
                key=f"custom_ws_{weight_id}_{field_name}",
            ) / 100
            weights[field_name] = val


    return weights


def _preset_summary(preset: Dict[str, float]) -> str:
    """One-line description of a preset's active weights."""
    parts = []
    for k, v in preset.items():
        if v > 0:
            label = SCORING_FIELDS.get(k)
            parts.append(f"{label} {v:.0%}")
    return ", ".join(parts) if parts else "—"


# ============================================================================
# Public API
# ============================================================================

def scoring_weights_block() -> List[Dict[str, float]]:
    """
    Renders the scoring panel in the Streamlit sidebar.
    """
    st.header("Ranking Presets")

    # ---- Bootstrap session strate ----
    if "preset_active" not in st.session_state:
        # Default: only R1 active
        st.session_state.preset_active = {name: (i == 0) for i, name in enumerate(RANKING_PRESETS)}
    if "custom_weight_sets" not in st.session_state:
        st.session_state.custom_weight_sets = []

    # Migration: add an id to existing weight sets that don't have one
    for ws in st.session_state.custom_weight_sets:
        if "id" not in ws:
            ws["id"] = str(uuid.uuid4())

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
    edited_custom: List[Dict[str, float]] = []

    for i, ws in enumerate(custom_sets):
        weight_id = ws["id"]
        cols_header = st.columns([6, 1])
        with cols_header[0]:
            st.markdown(f"**Custom {i + 1}**")
        with cols_header[1]:
            st.button("🗑️", key=f"delete_weight_{weight_id}", help="Delete this weight set", on_click=delete_weight, args=(weight_id,))
        edited = _weight_row_editor(weight_id, ws)
        edited["id"] = weight_id
        edited_custom.append(edited)
    st.button("➕ Add custom weight set", on_click=add_weight)

    # Persist edited values
    if edited_custom:
        st.session_state.custom_weight_sets = edited_custom

    # Add custom sets to result (exclude 'id' key for downstream use)
    for ws in st.session_state.custom_weight_sets:
        result.append({k: v for k, v in ws.items() if k != "id"})

    # Fallback: if nothing is selected, default to R1
    if not result:
        st.warning("Aucun ranking sélectionné — R1 (Leverage) activé par défaut.")
        result = [_make_full_weights(RANKING_PRESETS["R1 — Leverage"])]

    return result

