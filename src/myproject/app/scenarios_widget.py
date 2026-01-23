from myproject.mixture.mixture_gaussienne import mixture
from myproject.mixture.gauss import gaussian, asymetric_gaussian
import numpy as np
from typing import Tuple
from dataclasses import dataclass
import streamlit as st
from typing import Optional
import uuid

@dataclass
class ScenarioData:
    centers: list[float]
    std_devs: list[float]  # std ou std_l si asymétrique
    std_devs_r: list[float]  # std_r si asymétrique, sinon égal à std_devs
    weights: list[float]
    asymmetric: bool = False


def delete_scenario(scenario_id: str):
    """Delete scenario with given id from session state."""
    if len(st.session_state.scenarios) > 1:
        st.session_state.scenarios = [s for s in st.session_state.scenarios if s["id"] != scenario_id]


def add_scenario():
    """Add a new scenario with default values."""
    last_price = (
        st.session_state.scenarios[-1]["price"]
        if st.session_state.scenarios
        else 98.0
    )
    st.session_state.scenarios.append(
        {"id": str(uuid.uuid4()), "price": last_price + 0.10, "std": 0.10, "std_r": 0.10, "weight": 25.0}
    )


def scenario_params() -> Optional[ScenarioData]:
    """
    Interface to define market scenarios (Gaussian mixture).
    The user can add as many scenarios as they wish.
    Each scenario = (target price, uncertainty/volatility, probability)
    """
    if "scenarios" not in st.session_state:
        st.session_state.scenarios = [
            {"id": str(uuid.uuid4()), "price": 98.0, "std": 0.10, "std_r": 0.10, "weight": 50.0},  # Neutral scenario by default
        ]
    
    # Migration: ajouter un id aux scénarios existants s'ils n'en ont pas
    for scenario in st.session_state.scenarios:
        if "id" not in scenario:
            scenario["id"] = str(uuid.uuid4())

    asym_incertitude=st.checkbox(label = "Asymmetric Uncertainty", value = False)

    for i, scenario in enumerate(st.session_state.scenarios):
        scenario_id = scenario["id"]
        with st.container():
            # Ensure std_r exists (backward compatibility)
            if "std_r" not in scenario:
                scenario["std_r"] = scenario["std"]
            
            if asym_incertitude:
                # 5 columns for asymmetric mode
                col_name, col_price, col_std_l, col_std_r, col_weight, col_del = st.columns([1.5, 1.5, 1.5, 1.5, 1.5, 1])
                
                with col_name:
                    st.markdown(f"**Scenario {i+1}**")
                
                with col_price:
                    price = st.number_input(
                        "Target Price",
                        value=float(scenario["price"]),
                        step=0.01,
                        format="%.4f",
                        key=f"price_{scenario_id}",
                        help="Expected price for this scenario",
                    )
                    scenario["price"] = price
                
                with col_std_l:
                    std_l = st.number_input(
                        "σ left",
                        value=float(scenario["std"]),
                        min_value=0.001,
                        step=0.01,
                        format="%.4f",
                        key=f"std_l_{scenario_id}",
                        help="Downside uncertainty",
                    )
                    scenario["std"] = std_l
                
                with col_std_r:
                    std_r = st.number_input(
                        "σ right",
                        value=float(scenario["std_r"]),
                        min_value=0.001,
                        step=0.01,
                        format="%.4f",
                        key=f"std_r_{scenario_id}",
                        help="Upside uncertainty",
                    )
                    scenario["std_r"] = std_r
                
                with col_weight:
                    weight = st.number_input(
                        "Prob",
                        value=float(scenario["weight"]),
                        step=1.0,
                        format="%.1f",
                        key=f"weight_{scenario_id}",
                        help="Scenario weight (will be normalized)",
                    )
                    scenario["weight"] = weight
                
                with col_del:
                    st.markdown("")  # Spacing
                    if len(st.session_state.scenarios) > 1:
                        st.button("🗑️", key=f"delete_{scenario_id}", help="Delete this scenario", on_click=delete_scenario, args=(scenario_id,))
                    else:
                        st.caption("Min: 1")
            
            else:
                # 4 columns for symmetric mode
                col_name, col_price, col_std, col_weight, col_del = st.columns([2, 2, 2, 1.4, 0.7])
                
                with col_name:
                    st.markdown(f"**Scenario {i+1}**")
                
                with col_price:
                    price = st.number_input(
                        "Target Price",
                        value=float(scenario["price"]),
                        step=0.01,
                        format="%.4f",
                        key=f"price_{scenario_id}",
                        help="Expected price for this scenario",
                    )
                    scenario["price"] = price
                
                with col_std:
                    std = st.number_input(
                        "Uncertainty",
                        value=float(scenario["std"]),
                        min_value=0.001,
                        step=0.01,
                        format="%.4f",
                        key=f"std_{scenario_id}",
                        help="Standard deviation: larger means more uncertain",
                    )
                    scenario["std"] = std
                    scenario["std_r"] = std
                
                with col_weight:
                    weight = st.number_input(
                        "Probability",
                        value=float(scenario["weight"]),
                        max_value=100.0,
                        step=1.0,
                        format="%.1f",
                        key=f"weight_{scenario_id}",
                        help="Scenario weight (will be normalized)",
                    )
                    scenario["weight"] = weight
                
                with col_del:
                    if len(st.session_state.scenarios) > 1:
                        st.button("🗑️", key=f"delete_{scenario_id}", help="Delete this scenario", on_click=delete_scenario, args=(scenario_id,))

    # Bouton pour ajouter un nouveau scénario
    st.button("➕ Add Scenario", on_click=add_scenario)

    # Calculer les poids normalisés
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


def create_mixture_from_scenarios(
    scenarios: ScenarioData,
    price_min: float,
    price_max: float,
    num_points: int = 50,
) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    Crée une mixture gaussienne à partir des scénarios définis par l'utilisateur.
    Supporte les gaussiennes symétriques et asymétriques.

    Args:
        scenarios: ScenarioData avec centers, std_devs, std_devs_r, weights, asymmetric
        price_min: Prix minimum de la grille
        price_max: Prix maximum de la grille
        num_points: Nombre de points dans la grille

    Returns:
        (prices, mixture_normalized): Grille de prix et mixture gaussienne normalisée
    """
    # Extraire les paramètres des scénarios
    centers = scenarios.centers
    std_devs = scenarios.std_devs
    std_devs_r = scenarios.std_devs_r
    proba = scenarios.weights
    is_asymmetric = getattr(scenarios, 'asymmetric', False)

    if is_asymmetric:
        # Mode asymétrique: utiliser asymetric_gaussian
        prices, mix = mixture(
            price_min=price_min,
            price_max=price_max,
            num_points=num_points,
            proba=proba,
            mus=centers,
            sigmas=std_devs,
            f=asymetric_gaussian,
            sigmas_r=std_devs_r,
        )
    else:
        # Mode symétrique: utiliser gaussian standard
        prices, mix = mixture(
            price_min=price_min,
            price_max=price_max,
            num_points=num_points,
            proba=proba,
            mus=centers,
            sigmas=std_devs,
            f=gaussian,
        )
    average = float(np.average(prices, weights=mix))
    
    return prices, mix, average
