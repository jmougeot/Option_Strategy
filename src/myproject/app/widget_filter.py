import streamlit as st
from typing import Optional
from myproject.app.data_types import FilterData, StrategyType, STRATEGYTYPE

# Re-export for backward compatibility
__all__ = ['FilterData', 'StrategyType', 'STRATEGYTYPE', 'filter_params']


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
            "max_premium": 5.0, 
            "ouvert_gauche": 0, 
            "ouvert_droite": 0, 
            "min_premium_sell": 0.005,
            "delta_min": -0.75,
            "delta_max": 0.75,
            "limit_left_filter": 98.5,
            "limit_right_filter": 98,
        }

    
    # Retrieve current values from session_state
    current_filter = st.session_state.filter

    premium_only = st.checkbox(label="Risk Premium only", help= "Accept to loose only the strtegie's premium" )
    
    if premium_only:
        max_loss_left=100
        max_loss_right=100
        limit_left=98
        limit_right=98

    else: 
        max_loss_left_col,limit_left_col, premium_only_left_col= st.columns(3)
        with max_loss_left_col:
            max_loss_left = st.number_input("Max loss downside",
                                                    value=float(current_filter.get("max_loss_left", 0.1)),
                                                    step=0.001,
                                                    format="%.3f",
                                                    key="filter_max_loss",
                                                    help="Premium is included : if you pay 2 and entered 25 ticks, you're authorized to loose 23 ticks and if you received 2 you're autorized 27 ticks")       
        with limit_left_col:
            limit_left = st.number_input("Starting from",
                                                    value=float(current_filter.get("limit_left_filter", 98.5)),
                                                    step=0.001,
                                                    format="%.3f",
                                                    key="limit_left_filter_key",
                                                    help="imit to filter_max_loss_right where the max loss left is applied") 

        max_loss_right_col, limit_right_col, premium_only_right_col = st.columns(3)
        with max_loss_right_col:
            max_loss_right= st.number_input("Max loss upside",
                                                    value = float(current_filter.get("max_loss_right", 0.1)),
                                                    step=0.001,
                                                    format="%.3f",
                                                    key="filter_max_loss_right",
                                                    help= "Choose the max on the right of the target")

        with limit_right_col:
            limit_right= st.number_input("Starting from",
                                                    value = float(current_filter.get("limit_right_filter", 98.0)),
                                                    step=0.001,
                                                    format="%.3f",
                                                    key="limit_right_filter_key",
                                                    help= "limit to filter_max_loss_right where the max loss right is applied")
        
        with premium_only_right_col:
            premium_only_left = st.number_input("Premium only",
                                                    value = float(current_filter.get("limit_right_filter", 98.0)),
                                                    step=0.001,
                                                    format="%.3f",
                                                    key="premium_left_filter_key",
                                                    help= "Premium only")

        
    max_premium_col, min_premium_col = st.columns([1.5, 1.5])
    with max_premium_col:
        max_premium = st.number_input("Max premium",
                                               value=float(current_filter.get("max_premium", 5.0)),
                                               step=0.0025,
                                               format="%.4f",
                                               key="filter_max_premium",
                                               help="Max strategy price (absolute value)")

    with min_premium_col:
        min_premium_sell = st.number_input("Min price for short",
                                        value=float(current_filter.get("min_premium_sell", 0.005)),
                                        step=0.001,
                                        format="%.3f",
                                        key="filter_min_premium_sell",
                                        help="Minimum price to sell an option")

    
    ouvert_gauche_col, ouvert_droite_col = st.columns([2,2])
    with ouvert_gauche_col:
        ouvert_gauche = st.number_input("PUT: Short-Long",
                                               value=int(current_filter.get("ouvert_gauche", 0)),
                                               step=1,
                                               key="filter_ouvert_gauche",
                                               help="Number of puts sold - bought")
    with ouvert_droite_col:
        ouvert_droite = st.number_input("CALL: Short-Long",
                                               value=int(current_filter.get("ouvert_droite", 0)),
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
        "limit_right_filter": limit_right,
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
        limit_right=limit_right,
        premium_only=premium_only,
    )
