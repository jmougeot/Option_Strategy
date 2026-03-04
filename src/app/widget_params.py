"""
Parameter definitions for the option strategy application.
Pure Python — no Streamlit dependency.
"""
import re
from dataclasses import dataclass
from typing import Optional, List, Tuple

# Type alias
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
