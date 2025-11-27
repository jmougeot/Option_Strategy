import streamlit as st
from dataclasses import dataclass
from myproject.app.utils import strike_list
from typing import Optional


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
    max_loss:float
    max_premium: float
    ouvert:bool


def sidebar_params() -> UIParams:
    c1, c2 = st.columns(2)
    with c1:
        underlying = st.text_input(
            "Sous-jacent:", value="ER", help="Code Bloomberg (ER = EURIBOR)"
        )
    with c2:
        years_input = st.text_input(
            "Années:", value="6", help="6=2026, 7=2027 (séparées par virgule)"
        )

    c1 , c2= st.columns(2)
    with c1:
        months_input = st.text_input(
            "Mois d'expiration:",
            value="F",
            help="F=Jan, G=Feb, H=Mar, K=Apr, M=Jun, N=Jul, Q=Aug, U=Sep, V=Oct, X=Nov, Z=Dec",
        )
    with c2:
            price_step = st.number_input(
        "Pas de Prix ($)", value=0.0625, step=0.0001, format="%.4f"
    )
    c1 , c2= st.columns(2)

    with c1:
        max_loss= st.number_input(
        "Max loss", value= 0.01, format="%.4f", help="Perte maximum accéptée"
        )
    with c2:
        max_premium = st.number_input(
        "Max premium" , value=0.06, format="%.4f", help="Prix maximum de la stratégie"
        )

    c1, c2 = st.columns(2)
    with c1:
        price_min = st.number_input(
            "Prix Min ($)", value=97.750, step=0.0001, format="%.4f"
        )
    with c2:
        price_max = st.number_input(
            "Prix Max ($)", value=98.750, step=0.0001, format="%.4f"
        )
        
    ouvert = st.checkbox(
        "Risque Ouvert", 
        value=False, 
        help="Autoriser les stratégies à risque illimité (vente de calls/puts non couverts)"
    )


    strikes = strike_list(price_min, price_max, price_step)

    max_legs = st.slider("Nombre maximum de legs par stratégie:", 1, 6, 4)

    years = [int(y.strip()) for y in years_input.split(",") if y.strip()]
    months = [m.strip() for m in months_input.split(",") if m.strip()]

    return UIParams(
        underlying, months, years, price_min, price_max, price_step, max_legs, strikes, max_loss, max_premium, ouvert
    )


@dataclass
class ScenarioData:
    centers: list[float]
    std_devs: list[float]  # std ou std_l si asymétrique
    std_devs_r: list[float]  # std_r si asymétrique, sinon égal à std_devs
    weights: list[float]
    asymmetric: bool = False


def scenario_params() -> Optional[ScenarioData]:
    """
    Interface pour définir les scénarios de marché (mixture gaussienne).
    L'utilisateur peut ajouter autant de scénarios qu'il souhaite.
    Chaque scénario = (prix cible, incertitude/volatilité, probabilité)
    """
    if "scenarios" not in st.session_state:
        st.session_state.scenarios = [
            {"price": 98.0, "std": 0.10, "std_r": 0.10, "weight": 50.0},  # Scénario neutre par défaut
        ]

    scenarios_to_delete = []
    asym_incertitude=st.checkbox(label = "Incertitude asymetric", value = False)

    for i, scenario in enumerate(st.session_state.scenarios):
        with st.container():
            # Assurer que std_r existe (rétrocompatibilité)
            if "std_r" not in scenario:
                st.session_state.scenarios[i]["std_r"] = scenario["std"]
            
            if asym_incertitude:
                # 5 colonnes pour mode asymétrique
                col_name, col_price, col_std_l, col_std_r, col_weight, col_del = st.columns([1.5, 1.5, 1.5, 1.5, 1.5, 1])
                
                with col_name:
                    st.markdown(f"**Scénario {i+1}**")
                
                with col_price:
                    price = st.number_input(
                        "Prix Cible",
                        value=float(scenario["price"]),
                        step=0.01,
                        format="%.4f",
                        key=f"price_{i}",
                        help="Prix attendu pour ce scénario",
                    )
                    st.session_state.scenarios[i]["price"] = price
                
                with col_std_l:
                    std_l = st.number_input(
                        "σ gauche",
                        value=float(scenario["std"]),
                        min_value=0.001,
                        step=0.01,
                        format="%.4f",
                        key=f"std_l_{i}",
                        help="Incertitude côté baissier",
                    )
                    st.session_state.scenarios[i]["std"] = std_l
                
                with col_std_r:
                    std_r = st.number_input(
                        "σ droite",
                        value=float(scenario["std_r"]),
                        min_value=0.001,
                        step=0.01,
                        format="%.4f",
                        key=f"std_r_{i}",
                        help="Incertitude côté haussier",
                    )
                    st.session_state.scenarios[i]["std_r"] = std_r
                
                with col_weight:
                    weight = st.number_input(
                        "Proba",
                        value=float(scenario["weight"]),
                        max_value=100.0,
                        step=1.0,
                        format="%.1f",
                        key=f"weight_{i}",
                        help="Poids du scénario (sera normalisé)",
                    )
                    st.session_state.scenarios[i]["weight"] = weight
                
                with col_del:
                    st.markdown("")  # Espacement
                    if len(st.session_state.scenarios) > 1:
                        if st.button("🗑️", key=f"delete_{i}", help="Supprimer ce scénario"):
                            scenarios_to_delete.append(i)
                    else:
                        st.caption("Min: 1")
            
            else:
                # 4 colonnes pour mode symétrique
                col_name, col_price, col_std, col_weight, col_del = st.columns([2, 2, 2, 2, 0.5])
                
                with col_name:
                    st.markdown(f"**Scénario {i+1}**")
                
                with col_price:
                    price = st.number_input(
                        "Prix Cible",
                        value=float(scenario["price"]),
                        step=0.01,
                        format="%.4f",
                        key=f"price_{i}",
                        help="Prix attendu pour ce scénario",
                    )
                    st.session_state.scenarios[i]["price"] = price
                
                with col_std:
                    std = st.number_input(
                        "Incertitude",
                        value=float(scenario["std"]),
                        min_value=0.001,
                        step=0.01,
                        format="%.4f",
                        key=f"std_{i}",
                        help="Écart-type : plus c'est grand, plus le scénario est incertain",
                    )
                    st.session_state.scenarios[i]["std"] = std
                    st.session_state.scenarios[i]["std_r"] = std
                
                with col_weight:
                    weight = st.number_input(
                        "Probabilité",
                        value=float(scenario["weight"]),
                        max_value=100.0,
                        step=1.0,
                        format="%.1f",
                        key=f"weight_{i}",
                        help="Poids du scénario (sera normalisé)",
                    )
                    st.session_state.scenarios[i]["weight"] = weight
                
                with col_del:
                    st.markdown("")  # Espacement
                    if len(st.session_state.scenarios) > 1:
                        if st.button("🗑️", key=f"delete_{i}", help="Supprimer ce scénario"):
                            scenarios_to_delete.append(i)
                    else:
                        st.caption("Min: 1")

            st.divider()

    if (
        scenarios_to_delete
        and len(st.session_state.scenarios) - len(scenarios_to_delete) >= 1
    ):
        for idx in sorted(scenarios_to_delete, reverse=True):
            st.session_state.scenarios.pop(idx)
        st.rerun()
    elif scenarios_to_delete:
        st.warning("⚠️ Vous devez conserver au moins 1 scénario")

    if st.button("➕ Ajouter un scénario", use_container_width=True):
        # Ajouter un nouveau scénario avec des valeurs par défaut
        last_price = (
            st.session_state.scenarios[-1]["price"]
            if st.session_state.scenarios
            else 98.0
        )
        st.session_state.scenarios.append(
            {"price": last_price + 0.10, "std": 0.10, "std_r": 0.10, "weight": 25.0}
        )
        st.rerun()

    total_weight = sum(s["weight"] for s in st.session_state.scenarios)
    normalized_weights = [
        s["weight"] / total_weight for s in st.session_state.scenarios
    ]

    # Préparer les données pour le retour
    centers = [s["price"] for s in st.session_state.scenarios]
    std_devs = [s["std"] for s in st.session_state.scenarios]
    std_devs_r = [s.get("std_r", s["std"]) for s in st.session_state.scenarios]
    weights = normalized_weights

    return ScenarioData(
        centers=centers, 
        std_devs=std_devs, 
        std_devs_r=std_devs_r,
        weights=weights,
        asymmetric=asym_incertitude
    )
