from typing import Dict, List


# ============================================================================
# Metric catalogue (keys used by C++ scorer)
# ============================================================================

SCORING_FIELDS: Dict[str, str] = {
    "avg_pnl_levrage":   "Leverage",
    "roll":             "Roll",
    "average_pnl":       "Expected Gain",
    "premium":           "Premium",
    "Theta_hight" : "Theta",
    "Gamma_hight" : "Gamma",
    "Delta_hight" : "Delta Height"
}

ALL_FIELDS = {**SCORING_FIELDS}

# ============================================================================
# Predefined ranking presets  (R1–R7)
# ============================================================================

RANKING_PRESETS: Dict[str, Dict[str, float]] = {
    "R1 — Leverage":              {"avg_pnl_levrage": 1.0},
    "R2 — Roll":                  {"roll": 1.0},
    "R3 — Balanced (L/R)":       {"avg_pnl_levrage": 0.50, "roll": 0.50},
    "R4 — Roll + Leverage":       {"roll": 0.50, "avg_pnl_levrage": 0.50},
}
fields_list = list(SCORING_FIELDS.items())
midpoint= len(fields_list)//2

# ============================================================================
# Helpers
# ============================================================================
def _make_full_weights(sparse: Dict[str, float]) -> Dict[str, float]:
    """Expand a sparse preset dict into a full dict with 0.0 for missing keys."""
    full = {k: 0.0 for k in ALL_FIELDS}
    full.update(sparse)
    return full


def _preset_summary(preset: Dict[str, float]) -> str:
    """One-line description of a preset's active weights."""
    parts = []
    for k, v in preset.items():
        if v > 0:
            label = SCORING_FIELDS.get(k)
            parts.append(f"{label} {v:.0%}")
    return ", ".join(parts) if parts else "—"


# (Streamlit sidebar rendering removed — use app/sidebar/scoring_panel.py instead)

if False:  # placeholder to prevent syntax error on empty section
    def scoring_weights_block() -> List[Dict[str, float]]:
        pass  # UI rendering done in app/sidebar/scoring_panel.py
