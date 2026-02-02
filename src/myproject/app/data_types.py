"""
Data types for the option strategy application.
These are pure Python dataclasses that don't depend on Streamlit.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ScenarioData:
    """Data structure for scenario parameters"""
    centers: List[float]
    std_devs: List[float]  # std ou std_l si asymétrique
    std_devs_r: List[float]  # std_r si asymétrique, sinon égal à std_devs
    weights: List[float]
    asymmetric: bool = False


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
    confidence_senario: float


# Patterns de signes par type de stratégie (triés par strike croissant)
STRATEGYTYPE = {
    "put_condor": {"option_type": "put", "signs": [1, -1, -1, 1]},
    "call_condor": {"option_type": "call", "signs": [1, -1, -1, 1]},
    "put_ladder": {"option_type": "put", "signs": [-1, -1, 1]},
    "call_ladder": {"option_type": "call", "signs": [1, -1, -1]},
    "put_fly": {"option_type": "put", "signs": [1, -1, -1, 1]},
    "call_fly": {"option_type": "call", "signs": [1, -1, -1, 1]},
}
