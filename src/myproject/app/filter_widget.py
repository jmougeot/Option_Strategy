from dataclasses import dataclass
import streamlit as st
from typing import Optional

@dataclass
class StrategyType:
    put_condor: bool 
    call_condor: bool
    put_ladder:bool
    call_ladder: bool
    put_fly: bool
    call_fly: bool

# Patterns de signes par type de stratégie (triés par strike croissant)
# Format: (type_options, pattern_signes)
# type_options: "call", "put", ou "mixed"
# pattern_signes: liste des signes pour chaque leg en ordre de strike croissant
STRATEGYTYPE = {
    # PUT Condor: +P1 -P2 -P3 +P4 (achète ailes, vend corps) - strikes croissants
    "put_condor": {"option_type": "put", "signs": [1, -1, -1, 1]},
    # CALL Condor: +C1 -C2 -C3 +C4 (achète ailes, vend corps) - strikes croissants  
    "call_condor": {"option_type": "call", "signs": [1, -1, -1, 1]},
    # PUT Ladder: +P1 -P2 -P3 (achète 1, vend 2) - strikes croissants
    "put_ladder": {"option_type": "put", "signs": [-1, -1, 1]},
    # CALL Ladder: -C1 -C2 +C3 (vend 2, achète 1) - strikes croissants
    "call_ladder": {"option_type": "call", "signs": [1, -1, -1]},
    # PUT Fly: +P1 -2*P2 +P3 (achète ailes, vend 2x corps) - strikes croissants
    "put_fly": {"option_type": "put", "signs": [1, -1, -1, 1]},  # avec 2 options au milieu
    # CALL Fly: +C1 -2*C2 +C3 (achète ailes, vend 2x corps) - strikes croissants
    "call_fly": {"option_type": "call", "signs": [1, -1, -1, 1]},  # avec 2 options au milieu
}


@dataclass
class FilterData:
    max_loss_left: float
    max_loss_right: float
    max_premium: float
    ouvert_gauche: int
    ouvert_droite: int
    min_premium_sell:float
    filter_type: bool
    strategies_include : Optional[StrategyType]
    delta_min: float
    delta_max: float
    limit_left: float
    limit_right: float

def filter_params() -> FilterData:
    """
    Interface to define filters
    The user can choose: max price, open or closed risk, etc...
    Values are saved in st.session_state.filter
    """
    # Initialize default values in session_state
    if "filter" not in st.session_state:
        st.session_state.filter = {
            "max_loss_right": 0.1,
            "max_loss_left":0.1, 
            "max_premium": 0.05, 
            "ouvert_gauche": 0, 
            "ouvert_droite": 0, 
            "min_premium_sell": 0.05,
            "delta_min": -0.75,
            "delta_max": 0.75,
            "limit_left_filter": 98.5,
            "limit_right_filter": 98
        }

    
    # Retrieve current values from session_state
    current_filter = st.session_state.filter
    unlimited_loss = st.checkbox(label="unlimited loss", value=False)
    if unlimited_loss:
        max_loss_left=10
        max_loss_right=10
        limit_left=98
        limit_right=98
    else: 
        max_loss_left_col, max_loss_right_col, limit_left_col, limit_right_col = st.columns([1.5, 1.5, 1.5, 1.5])
        with max_loss_left_col:
            max_loss_left = st.number_input("Max loss left",
                                                    value=float(current_filter["max_loss_left"]),
                                                    step=0.001,
                                                    format="%.3f",
                                                    key="filter_max_loss",
                                                    help="Max loss left")       
        with max_loss_right_col:
            max_loss_right= st.number_input("Max loss right",
                                                    value = float(current_filter["max_loss_right"]),
                                                    step=0.001,
                                                    format="%.3f",
                                                    key="filter_max_loss_right",
                                                    help= "Choose the max on the right of the target")
        with limit_left_col:
            limit_left = st.number_input("Limit left",
                                                    value=float(current_filter["limit_left_filter"]),
                                                    step=0.001,
                                                    format="%.3f",
                                                    key="limit_left_filter_key",
                                                    help="imit to filter_max_loss_right where the max loss left is applied") 
        with limit_right_col:
            limit_right= st.number_input("Limit right",
                                                    value = float(current_filter["limit_right_filter"]),
                                                    step=0.001,
                                                    format="%.3f",
                                                    key="limit_right_filter_key",
                                                    help= "limit to filter_max_loss_right where the max loss right is applied")

        
    max_premium_col, min_premium_col = st.columns([1.5, 1.5])
    with max_premium_col:
        max_premium = st.number_input("Max premium",
                                               value=float(current_filter["max_premium"]),
                                               step=0.0025,
                                               format="%.4f",
                                               key="filter_max_premium",
                                               help="Max strategy price (absolute value)")

    with min_premium_col:
        min_premium_sell = st.number_input("Min price for short",
                                        value=float(current_filter["min_premium_sell"]),
                                        step=0.001,
                                        format="%.3f",
                                        key="filter_min_premium_sell",
                                        help="Minimum price to sell an option")

    
    ouvert_gauche_col, ouvert_droite_col = st.columns([2,2])
    with ouvert_gauche_col:
        ouvert_gauche = st.number_input("PUT: Short-Long",
                                               value=int(current_filter["ouvert_gauche"]),
                                               step=1,
                                               key="filter_ouvert_gauche",
                                               help="Number of puts sold - bought")
    with ouvert_droite_col:
        ouvert_droite = st.number_input("CALL: Short-Long",
                                               value=int(current_filter["ouvert_droite"]),
                                               step=1,
                                               key="filter_ouvert_droite",
                                               help="Number of calls sold - bought")
        
    delat_min_col, delat_max_col = st.columns([2,2])
    with delat_min_col:
        delta_min = st.number_input("Delta Min",
                                               value=float(current_filter.get("delta_min", -0.75)),
                                               step=0.01,
                                               key="delta_min",
                                               help="Minimum delta for strategy")
    with delat_max_col:
        delta_max = st.number_input("Delta Max",
                                               value=float(current_filter.get("delta_max", 0.75)),
                                               step=0.01,
                                               key="delta_max",
                                               help="Maximum delta for strategy")
        
    
    filter_type = st.checkbox(label="Select strategy Type",
                                    value= False,
                                    help= "Select the type of strategies you want to compare")
                        
    strat_include = None

    if filter_type :
        with st.expander(label="Select the Strategy you want to compare"):
            put_condor = st.checkbox(label="Put Condor", value=False)
            call_condor=st.checkbox(label="Call Condor", value=False)
            put_ladder=st.checkbox(label="Put ladder", value=False)
            call_ladder=st.checkbox(label="Call Ladder", value=False)
            put_fly=st.checkbox(label="Put Fly", value=False)
            call_fly=st.checkbox(label="Call Fly", value=False)

        strat_include = StrategyType(
            put_condor=put_condor,
            call_condor=call_condor,
            put_ladder=put_ladder,
            call_ladder=call_ladder,
            put_fly=put_fly,
            call_fly=call_fly,
        )

    # Save new values in session_state
    st.session_state.filter = {
        "max_loss_right": max_loss_right,
        "max_loss_left" : max_loss_left,
        "max_premium": max_premium,
        "ouvert_gauche": ouvert_gauche,
        "delta_min": delta_min,
        "delta_max": delta_max,
        "ouvert_droite": ouvert_droite,
        "min_premium_sell": min_premium_sell,
        "limit_left_filter": limit_left,
        "limit_right_filter": limit_right
    }


    return FilterData(
        max_loss_left=max_loss_left,
        max_loss_right=max_loss_right,
        max_premium=max_premium,
        ouvert_gauche=ouvert_gauche,
        ouvert_droite=ouvert_droite,
        min_premium_sell=min_premium_sell,
        filter_type=filter_type,
        strategies_include=strat_include,
        delta_min=delta_min,
        delta_max=delta_max,
        limit_left=limit_left,
        limit_right=limit_right
    )
