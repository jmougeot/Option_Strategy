"""
Data types, parameters, and scoring constants for the option strategy application.
Pure Python — no UI dependency.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# ============================================================================
# Core data types
# ============================================================================

@dataclass
class ScenarioData:
    """Data structure for scenario parameters"""
    centers: List[float]
    std_devs: List[float]  # std ou std_l si asymétrique
    std_devs_r: List[float]  # std_r si asymétrique, sinon égal à std_devs
    weights: List[float]

@dataclass
class FutureData:
    """Data on the future (underlying price and last tradeable date)"""
    underlying_price: Optional[float] = None
    last_tradable_date: Optional[str] = None
    number_strategies: Optional[int] = None


@dataclass
class StrategyType:
    """Strategy type filter"""
    put_condor: bool 
    call_condor: bool
    put_ladder: bool
    call_ladder: bool
    put_fly: bool
    call_fly: bool


@dataclass
class FilterData:
    """Data structure for filter parameters"""
    max_loss_left: float
    max_loss_right: float
    max_premium: float
    ouvert_gauche: int
    ouvert_droite: int
    min_premium_sell: float
    filter_type: bool
    strategies_include: Optional[StrategyType]
    delta_min: float
    delta_max: float
    limit_left: float
    limit_right: float
    premium_only: bool 
    premium_only_right: bool 
    premium_only_left: bool


# Patterns de signes par type de stratégie (triés par strike croissant)
STRATEGYTYPE = {
    "put_condor": {"option_type": "put", "signs": [1, -1, -1, 1]},
    "call_condor": {"option_type": "call", "signs": [1, -1, -1, 1]},
    "put_ladder": {"option_type": "put", "signs": [-1, -1, 1]},
    "call_ladder": {"option_type": "call", "signs": [1, -1, -1]},
    "put_fly": {"option_type": "put", "signs": [1, -1, -1, 1]},
    "call_fly": {"option_type": "call", "signs": [1, -1, -1, 1]},
}


# ============================================================================
# UI Parameters  (ex widget_params.py)
# ============================================================================

RollExpiry = Tuple[str, int]


def parse_roll_input(roll_input: str) -> Optional[List[RollExpiry]]:
    """Parse roll expiries: "H6, Z5" -> [(H,6),(Z,5)]."""
    if not roll_input:
        return None
    roll_expiries: List[RollExpiry] = []
    parts = re.split(r'[,\s]+', roll_input.strip())
    for part in parts:
        part = part.strip().upper()
        if len(part) >= 2:
            month = part[0]
            year_str = part[1:]
            if month.isalpha() and year_str.isdigit():
                roll_expiries.append((month, int(year_str)))
    return roll_expiries if roll_expiries else None


UNDERLYING_PARAMS = {
    'ER' : {'Short': 0.0025, 'Step': 0.0625, 'Min_price': 97,  'Max_price': 99,  'max_premium': 0.1},
    'SFR': {'Short': 0.0025, 'Step': 0.0625, 'Min_price': 96,  'Max_price': 99,  'max_premium': 0.1},
    'SFI': {'Short': 0.0025, 'Step': 0.0500, 'Min_price': 96,  'Max_price': 99,  'max_premium': 0.1},
    'RX' : {'Short': 0.0200, 'Step': 0.5000, 'Min_price': 126, 'Max_price': 132, 'max_premium': 0.5},
    'DU' : {'Short': 0.0100, 'Step': 0.1000, 'Min_price': 106, 'Max_price': 108, 'max_premium': 0.2},
    'OE' : {'Short': 0.0200, 'Step': 0.2500, 'Min_price': 115, 'Max_price': 119, 'max_premium': 0.2},
    'UB' : {'Short': 0.0500, 'Step': 1.0000, 'Min_price': 105, 'Max_price': 115, 'max_premium': 0.5},
    '0R' : {'Short': 0.0500, 'Step': 0.0625, 'Min_price': 97,  'Max_price': 99,  'max_premium': 0.1},
    '0N' : {'Short': 0.0500, 'Step': 0.100,  'Min_price': 96,  'Max_price': 99,  'max_premium': 0.1},
    '0Q' : {'Short': 0.0500, 'Step': 0.0625, 'Min_price': 96,  'Max_price': 99,  'max_premium': 0.1},
    'Other': {}
}


@dataclass
class UIParams:
    underlying: str
    months: List[str]
    years: List[int]
    price_min: float
    price_max: float
    price_step: float
    max_legs: int
    strikes: List[float]
    unit: str
    brut_code: Optional[List[str]] = None
    roll_expiries: Optional[List[RollExpiry]] = None
    operation_penalisation: float = 0.0
    use_bachelier: bool = True
    use_sabr: bool = True


# ============================================================================
# Scoring catalogue & presets  (ex widget_scoring.py)
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

RANKING_PRESETS: Dict[str, Dict[str, float]] = {
    "R1 — Leverage":              {"avg_pnl_levrage": 1.0},
    "R2 — Roll":                  {"roll": 1.0},
    "R3 — Balanced (L/R)":       {"avg_pnl_levrage": 0.50, "roll": 0.50},
    "R4 — Roll + Leverage":       {"roll": 0.50, "avg_pnl_levrage": 0.50},
}


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
