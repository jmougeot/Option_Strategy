import streamlit as st
import re
from dataclasses import dataclass
from myproject.app.utils import strike_list
from typing import Optional, List, Tuple


# Mois Bloomberg disponibles
MONTH_OPTIONS = ["H", "M", "U", "Z"]
MONTH_NAMES = {"H": "March", "M": "June", "U": "September", "Z": "December"}

# Type alias
RollExpiry = Tuple[str, int]


def parse_roll_input(roll_input: str) -> Optional[List[RollExpiry]]:
    """
    Parse une chaîne de roll expiries au format "H6, Z5" ou "H6,Z5".
    
    Retourne une liste de tuples (month, year) ou None si vide.
    """
    if not roll_input:
        return None
    
    roll_expiries: List[RollExpiry] = []
    # Split par virgule ou espace
    parts = re.split(r'[,\s]+', roll_input.strip())
    
    for part in parts:
        part = part.strip().upper()
        if len(part) >= 2:
            # Format: M + Y (ex: H6, Z5, H26)
            month = part[0]
            year_str = part[1:]
            if month.isalpha() and year_str.isdigit():
                roll_expiries.append((month, int(year_str)))
    
    return roll_expiries if roll_expiries else None


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
    brut_code: Optional[List[str]] = None
    roll_expiries: Optional[List[RollExpiry]] = None


def sidebar_params() -> UIParams:
    brut_code_check =st.checkbox(
        "Provide raw code",
        value=False,
        help="Provide full Bloomberg code"
    )
    
    # Defaults
    underlying = "ER"
    years_input = "6"
    months_input = "F"
    code_brut = None  # None by default, list if raw mode
    
    
    if brut_code_check is False : 
        c1, c2 = st.columns(2)
        with c1:
            underlying = st.text_input(
                "Underlying:", value="ER", help="Bloomberg Code (ER = EURIBOR)"
            )
        with c2:
            years_input = st.text_input(
                "Years:", value="6", help="6=2026, 7=2027 (comma separated)"
            )

        c1 , c2= st.columns(2)
        with c1:
            months_input = st.text_input(
                "Expiration Month:",
                value="F",
                help="H=Mar, M=Jun, U=Sep, Z=Dec",
            )
    
        with c2:
                price_step = st.number_input(
            "Price Step ($)", value=0.0625, step=0.0001, format="%.4f"
        )

    else:
        c1 , c2= st.columns(2)
        with c1:
            code_brut=st.text_input(
                "Full Bloomberg Code",
                value="RXWF26C2,RXWF26P2",
                help="Search for Bloomberg code and include put and call"
            )
        with c2:
            price_step = st.number_input(
            "Price Step ($)", value=0.0625, step=0.0001, format="%.4f"
        )

    c1, c2 = st.columns(2)
    with c1:
        price_min = st.number_input(
            "Min Price ($)", value=97.750, step=0.0001, format="%.4f"
        )
    with c2:
        price_max = st.number_input(
            "Max Price ($)", value=98.750, step=0.0001, format="%.4f"
            )
    
    roll_expiries: Optional[List[RollExpiry]] = None

    # Roll uniquement en mode standard (pas brut_code)
    if not brut_code_check:
        custom_roll = st.checkbox(
            "Custom roll",
            value=False,
            help="Check to specify roll expiries."
        )
        
        if custom_roll:
            roll_input = st.text_input(
                "Roll months",
                value="Z5",
                help="Format: M1Y1, M2Y2 (e.g. Z5 or H6, Z5)"
            )
            if roll_input:
                roll_expiries = parse_roll_input(roll_input)

    strikes = strike_list(price_min, price_max, price_step)

    max_legs = st.slider("Max legs per strategy:", 1, 6, 4)

    years = [int(y.strip()) for y in years_input.split(",") if y.strip()]
    months = [m.strip() for m in months_input.split(",") if m.strip()]
    
    # None if no raw code, else list of codes
    if code_brut:
        brut_code_result = [y.strip() for y in code_brut.split(",") if y.strip()] or None
    else:
        brut_code_result = None


    return UIParams(
        underlying=underlying,
        months=months,
        years=years,
        price_min=price_min,
        price_max=price_max,
        price_step=price_step,
        max_legs=max_legs,
        strikes=strikes,
        brut_code=brut_code_result,
        roll_expiries=roll_expiries,
    )
