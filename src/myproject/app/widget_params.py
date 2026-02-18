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

UNDERLYING_PARAMS = {
    'ER' : {'Short': 0.0025, 'Step' : 0.0625, 'Min_price': 97, 'Max_price': 99, 'max_premium': 0.1},
    'SFR': {'Short': 0.0025, 'Step' : 0.0625, 'Min_price': 96, 'Max_price': 99, 'max_premium': 0.1},
    'SFI': {'Short': 0.0025, 'Step' : 0.0500, 'Min_price': 96, 'Max_price': 99, 'max_premium': 0.1},
    'RX' : {'Short': 0.0200, 'Step' : 0.5000, 'Min_price': 126, 'Max_price': 132, 'max_premium': 0.5},
    'DU' : {'Short': 0.0100, 'Step' : 0.1000, 'Min_price': 106, 'Max_price': 108, 'max_premium': 0.2},
    'OE' : {'Short': 0.0200, 'Step' : 0.2500, 'Min_price': 115, 'Max_price': 119, 'max_premium': 0.2},
    'UB' : {'Short': 0.0500, 'Step' : 1.0000, 'Min_price': 105, 'Max_price': 115, 'max_premium': 0.5},
    '0R' : {'Short': 0.0500, 'Step' : 0.0625, 'Min_price': 97, 'Max_price': 99, 'max_premium': 0.1},
    '0N' : {'Short': 0.0500, 'Step' : 0.100, 'Min_price': 96, 'Max_price': 99, 'max_premium': 0.1},
    '0Q' : {'Short': 0.0500, 'Step' : 0.0625, 'Min_price': 96, 'Max_price': 99, 'max_premium': 0.1},
    'Other': {}
}

def on_underlying_change():
    """Callback: met à jour price_step, price_min, price_max et min_premium_sell quand l'underlying change."""
    und = st.session_state.param_underlying
    if und in UNDERLYING_PARAMS and und != "Other":
        p = UNDERLYING_PARAMS[und]
        st.session_state.param_price_step = p['Step']
        st.session_state.param_price_min = float(p['Min_price'])
        st.session_state.param_price_max = float(p['Max_price'])
        st.session_state.filter_min_premium_sell = p['Short']
        st.session_state.filter_max_premium= p['max_premium']


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
        help="Provide full Bloomberg code",
        key="brut_code_check"
    )
    
    # Defaults
    underlying = "ER"
    years_input = "6"
    months_input = "F"
    code_brut = None  # None by default, list if raw mode
    
    
    default_und = 'ER'
    default_params = UNDERLYING_PARAMS[default_und]

    if brut_code_check is False : 
        # Initialize session state defaults if not already set
        if "param_years" not in st.session_state:
            st.session_state["param_years"] = "6"
        
        c1, c2 = st.columns(2)
        with c1:
            underlying = st.selectbox(
                "Underlying:",
                options=list(UNDERLYING_PARAMS.keys()),
                index=0,
                help="Bloomberg Code (ER = EURIBOR)",
                key="param_underlying",
                on_change=on_underlying_change,
            )
        with c2:
            years_input = st.text_input(
                "Years:", help="6=2026, 7=2027 (comma separated)",
                key="param_years"
            )

        # Si "Other" est sélectionné, afficher un text_input pour saisir le code
        if underlying == "Other":
            underlying = st.text_input(
                "Custom underlying code:",
                value="",
                help="Enter the Bloomberg underlying code",
                key="param_custom_underlying"
            )

        # Initialize session state defaults if not already set
        if "param_months" not in st.session_state:
            st.session_state["param_months"] = "F"
        if "param_price_step" not in st.session_state:
            st.session_state["param_price_step"] = default_params['Step']
        
        c1 , c2= st.columns(2)
        with c1:
            months_input = st.text_input(
                "Expiration Month:",
                help="H=Mar, M=Jun, U=Sep, Z=Dec",
                key="param_months"
            )
    
        with c2:
            price_step = st.number_input(
                "Price Step ($)", step=0.0001, format="%.4f",
                key="param_price_step"
            )

    else:
        c1 , c2= st.columns(2)
        with c1:
            code_brut=st.text_input(
                "Full Bloomberg Code",
                value="RXWF26C2,RXWF26P2",
                help="Search for Bloomberg code and include put and call",
                key="param_brut_code"
            )
        with c2:
            price_step = st.number_input(
                "Price Step ($)", value=default_params['Step'], step=0.0001, format="%.4f",
                key="param_price_step"
            )

    # Initialize session state defaults for price inputs if not already set
    if "param_price_min" not in st.session_state:
        st.session_state["param_price_min"] = float(default_params['Min_price'])
    if "param_price_max" not in st.session_state:
        st.session_state["param_price_max"] = float(default_params['Max_price'])
    
    c1, c2 = st.columns(2)
    with c1:
        price_min = st.number_input(
            "Min Price ($)", step=0.0001, format="%.4f",
            key="param_price_min"
        )
    with c2:
        price_max = st.number_input(
            "Max Price ($)", step=0.0001, format="%.4f",
            key="param_price_max"
            )
    
    roll_expiries: Optional[List[RollExpiry]] = None

    # Roll uniquement en mode standard (pas brut_code)
    if not brut_code_check:
        custom_roll = st.checkbox(
            "Custom roll",
            value=False,
            help="Check to specify roll expiries.",
            key="param_custom_roll"
        )
        
        if custom_roll:
            roll_input = st.text_input(
                "Roll months",
                value="Z5",
                help="Format: M1Y1, M2Y2 (e.g. Z5 or H6, Z5)",
                key="param_roll_input"
            )
            if roll_input:
                roll_expiries = parse_roll_input(roll_input)

    strikes = strike_list(price_min, price_max, price_step)

    # Initialize session state default for max_legs if not already set
    if "param_max_legs" not in st.session_state:
        st.session_state["param_max_legs"] = 4
    
    max_legs = st.slider("Max legs per strategy:", 1, 9, key="param_max_legs")

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
