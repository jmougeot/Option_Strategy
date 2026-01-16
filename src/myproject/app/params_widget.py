import streamlit as st
from dataclasses import dataclass
from myproject.app.utils import strike_list
from typing import Optional,List


# Mois Bloomberg disponibles
MONTH_OPTIONS = ["H", "M", "U", "Z"]
MONTH_NAMES = {"H": "March", "M": "June","U": "September",  "Z": "December"}


@dataclass
class UIParams:
    underlying: str
    months: list[str]
    years: list[int]
    price_min: float
    price_max: float
    price_step: float
    max_legs: int
    strikes: list[float]
    brut_code: Optional[List[str]]=None
    compute_roll: bool = True
    roll_month: Optional[str] = None
    roll_year: Optional[int] = None


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
    
    roll_month: Optional[str] = None
    roll_year: Optional[int] = None
    

    custom_roll = st.checkbox(
        "Custom roll",
        value=False,
        help="By default: previous month. Check to specify a custom month."
    )
    
    if custom_roll:
        c1, c2 = st.columns(2)
        with c1:
            roll_month_idx = st.selectbox(
                "Roll Month",
                options=range(len(MONTH_OPTIONS)),
                format_func=lambda i: f"{MONTH_OPTIONS[i]} ({MONTH_NAMES[MONTH_OPTIONS[i]]})",
                index=0,
                key="roll_month_select"
            )
            roll_month = MONTH_OPTIONS[roll_month_idx]
        with c2:
            roll_year = st.number_input(
                "Roll Year",
                value=6,
                min_value=5,
                max_value=10,
                step=1,
                help="Year for roll (6=2026, etc.)",
                key="roll_year_input"
            )

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
        compute_roll=True,
        roll_month=roll_month,
        roll_year=roll_year,
    )
