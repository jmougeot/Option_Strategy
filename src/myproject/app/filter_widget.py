from dataclasses import dataclass
import streamlit as st 


@dataclass
class FilterData:
    max_loss:float
    max_premium: float
    ouvert_gauche: int
    ouvert_droite: int
    min_premium_sell:float
   


def filter_params() -> FilterData:
    """
    Interface pour définir les filtres
    L'utilisateur peut choisir : le prix max, risque ouvert ou fermé, etc ...
    """
    if "filter" not in st.session_state:
        st.session_state.filter = [
            {"max_loss": 0.1, "max_premium": 0.1, "ouvert_gauche": 0, "ouvert_droite": 0, "min_premium_sell": 0}
        ]

    max_loss_col, max_premium_col, min_premium_col = st.columns([2,2,2])
    with max_loss_col:
        max_loss = st.number_input("Max loss acceptée",
                                               value=0.1,
                                               step=0.01,
                                               help="Max loss acceptée")
    with max_premium_col:
        max_premium = st.number_input("Max premium",
                                               value=0.05,
                                               step=0.01,
                                               help="Prix max de la stratégie (valeur absolue)")

    with min_premium_col:
        min_premium_sell = st.number_input("Prix min pour short",
                                        value=0.005,
                                        step=0.001,
                                        help="Prix minimum pour vendre une option")


    ouvert_gauche, ouvert_droite = st.columns([2,2])
    with ouvert_gauche:
        ouvert_gauche = st.number_input("PUT : Short-long",
                                               value=0,
                                               step=1,
                                               help="Nombre de put vendus - achetés")
    with ouvert_droite:
        ouvert_droite = st.number_input("CALL: Short - long",
                                               value=0,
                                               step=1,
                                               help="Nombre de put vendus - achetés")

    return FilterData(
    max_loss = max_loss,
    max_premium=max_premium,
    ouvert_gauche=ouvert_gauche,
    ouvert_droite=ouvert_droite,
    min_premium_sell=min_premium_sell)
