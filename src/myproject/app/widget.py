import streamlit as st
from dataclasses import dataclass
from myproject.app.utils import strike_list
from typing import Optional 

@dataclass
class UIParams:
    underlying: str
    months: list[str]
    years: list[int]
    strike: float
    price_min: float
    price_max: float
    price_step: float
    max_legs: int
    strikes: list[float]

def sidebar_params() -> UIParams:
    st.header("⚙️ Paramètres")

    c1, c2 = st.columns(2)
    with c1:
        underlying = st.text_input("Sous-jacent:", value="ER", help="Code Bloomberg (ER = EURIBOR)")
    with c2:
        years_input = st.text_input("Années:", value="6", help="6=2026, 7=2027 (séparées par virgule)")

    c1, c2 = st.columns(2)
    with c1:
        months_input = st.text_input("Mois d'expiration:", value="F",
                                     help="F=Jan, G=Feb, H=Mar, K=Apr, M=Jun, N=Jul, Q=Aug, U=Sep, V=Oct, X=Nov, Z=Dec")
    with c2:
        strike = st.number_input("Strike :", value=98.0, format="%.4f", help="Target Price")

    c1, c2 = st.columns(2)
    with c1:
        price_min = st.number_input("Prix Min ($)", value=97.750, step=0.0001, format="%.4f")
    with c2:
        price_max = st.number_input("Prix Max ($)", value=98.750, step=0.0001, format="%.4f")

    price_step = st.number_input("Pas de Prix ($)", value=0.0625, step=0.0001, format="%.4f")
    strikes = strike_list(price_min, price_max, price_step)


    max_legs = st.slider("Nombre maximum de legs par stratégie:", 1, 4, 4)

    years = [int(y.strip()) for y in years_input.split(",") if y.strip()]
    months = [m.strip() for m in months_input.split(",") if m.strip()]

    return UIParams(underlying, months, years, strike, price_min, price_max, price_step, max_legs, strikes)

@dataclass
class ScenarioData:
    centers: list[float]
    std_devs: list[float]
    weights: list[float]

def scenario_params() -> Optional[ScenarioData]:
    """
    Interface pour définir les scénarios de marché (mixture gaussienne).
    L'utilisateur peut ajouter autant de scénarios qu'il souhaite.
    Chaque scénario = (prix cible, incertitude/volatilité, probabilité)
    """    
    a = st.checkbox("Ajouter des scénarios ")
    if a == True : 
        if 'scenarios' not in st.session_state:
            st.session_state.scenarios = [
                {'price': 98.0, 'std': 0.10, 'weight': 50.0},  # Scénario neutre par défaut
            ]
        
        scenarios_to_delete = []
    
        for i, scenario in enumerate(st.session_state.scenarios):
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])
                
                with col1:
                    st.markdown(f"**Scénario {i+1}**")
                
                with col2:
                    price = st.number_input(
                        "Prix Cible",
                        value=float(scenario['price']),
                        step=0.01,
                        format="%.4f",
                        key=f"price_{i}",
                        help="Prix attendu pour ce scénario"
                    )
                    st.session_state.scenarios[i]['price'] = price
                
                with col3:
                    std = st.number_input(
                        "Incertitude",
                        value=float(scenario['std']),
                        min_value=0.001,
                        step=0.01,
                        format="%.4f",
                        key=f"std_{i}",
                        help="Écart-type : plus c'est grand, plus le scénario est incertain"
                    )
                    st.session_state.scenarios[i]['std'] = std
                
                with col4:
                    weight = st.number_input(
                        "Probabilité",
                        value=float(scenario['weight']),
                        min_value=0.1,
                        max_value=100.0,
                        step=1.0,
                        format="%.1f",
                        key=f"weight_{i}",
                        help="Poids du scénario (sera normalisé)"
                    )
                    st.session_state.scenarios[i]['weight'] = weight
                
                with col5:
                    if len(st.session_state.scenarios) > 1:
                        if st.button("🗑️", key=f"delete_{i}", help="Supprimer ce scénario"):
                            scenarios_to_delete.append(i)
                
                st.divider()
        
        # Supprimer les scénarios marqués
        for idx in sorted(scenarios_to_delete, reverse=True):
            st.session_state.scenarios.pop(idx)
            st.rerun()
        
        if st.button("➕ Ajouter un scénario", use_container_width=True):
            # Ajouter un nouveau scénario avec des valeurs par défaut
            last_price = st.session_state.scenarios[-1]['price'] if st.session_state.scenarios else 98.0
            st.session_state.scenarios.append({
                'price': last_price + 0.10,
                'std': 0.10,
                'weight': 25.0
            })
            st.rerun()
        
        total_weight = sum(s['weight'] for s in st.session_state.scenarios)
        normalized_weights = [s['weight'] / total_weight for s in st.session_state.scenarios]
        

        # Préparer les données pour le retour
        centers = [s['price'] for s in st.session_state.scenarios]
        std_devs = [s['std'] for s in st.session_state.scenarios]
        weights = normalized_weights
        
        return ScenarioData(centers=centers, std_devs=std_devs, weights=weights)
    else : 
        
        return None 