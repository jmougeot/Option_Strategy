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
    Les valeurs sont sauvegardées dans st.session_state.filter
    """
    # Initialisation des valeurs par défaut dans session_state
    if "filter" not in st.session_state:
        st.session_state.filter = {
            "max_loss": 0.1, 
            "max_premium": 0.05, 
            "ouvert_gauche": 0, 
            "ouvert_droite": 0, 
            "min_premium_sell": 0.005
        }

    # Récupérer les valeurs actuelles du session_state
    current_filter = st.session_state.filter

    max_loss_col, max_premium_col, min_premium_col = st.columns([2,2,2])
    with max_loss_col:
        max_loss = st.number_input("Max loss acceptée",
                                               value=float(current_filter["max_loss"]),
                                               step=0.01,
                                               key="filter_max_loss",
                                               help="Max loss acceptée")
    with max_premium_col:
        max_premium = st.number_input("Max premium",
                                               value=float(current_filter["max_premium"]),
                                               step=0.01,
                                               key="filter_max_premium",
                                               help="Prix max de la stratégie (valeur absolue)")

    with min_premium_col:
        min_premium_sell = st.number_input("Prix min pour short",
                                        value=float(current_filter["min_premium_sell"]),
                                        step=0.001,
                                        format="%.3f",
                                        key="filter_min_premium_sell",
                                        help="Prix minimum pour vendre une option")

    ouvert_gauche_col, ouvert_droite_col = st.columns([2,2])
    with ouvert_gauche_col:
        ouvert_gauche = st.number_input("PUT : Short-long",
                                               value=int(current_filter["ouvert_gauche"]),
                                               step=1,
                                               key="filter_ouvert_gauche",
                                               help="Nombre de put vendus - achetés")
    with ouvert_droite_col:
        ouvert_droite = st.number_input("CALL: Short - long",
                                               value=int(current_filter["ouvert_droite"]),
                                               step=1,
                                               key="filter_ouvert_droite",
                                               help="Nombre de call vendus - achetés")

    # Sauvegarder les nouvelles valeurs dans session_state
    st.session_state.filter = {
        "max_loss": max_loss,
        "max_premium": max_premium,
        "ouvert_gauche": ouvert_gauche,
        "ouvert_droite": ouvert_droite,
        "min_premium_sell": min_premium_sell
    }

    return FilterData(
        max_loss=max_loss,
        max_premium=max_premium,
        ouvert_gauche=ouvert_gauche,
        ouvert_droite=ouvert_droite,
        min_premium_sell=min_premium_sell
    )
