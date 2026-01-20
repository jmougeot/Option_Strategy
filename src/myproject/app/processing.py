"""
Module pour la logique de traitement et de filtrage des stratégies
"""

from typing import List, Tuple, Optional, Dict, Any, TYPE_CHECKING
from myproject.strategy.comparison_class import StrategyComparison
from myproject.app.scenarios_widget import ScenarioData


def process_comparison_results(
    best_strategies: List[StrategyComparison],
) -> Tuple[List[StrategyComparison], List[StrategyComparison], Optional[float]]:
    """
    Traite les résultats de comparaison et filtre pour le meilleur prix cible.

    Args:
        best_strategies: Liste des meilleures stratégies

    Returns:
        Tuple (all_comparisons, top_5_comparisons, best_target_price)
    """
    if not best_strategies:
        return [], [], None

    # Utiliser le milieu de la plage de prix comme target_price
    first_strategy = best_strategies[0]
    best_target_price = (first_strategy.prices[0] + first_strategy.prices[-1]) / 2 if len(first_strategy.prices) > 0 else None

    # Toutes les stratégies sont valides
    comparisons = best_strategies

    # Top 5 pour le diagramme
    top_5_comparisons = comparisons[:5]

    return comparisons, top_5_comparisons, best_target_price


def save_to_session_state(
    all_comparisons: List[StrategyComparison],
    params: Any,
    best_target_price: Optional[float],
    scenarios: Optional["ScenarioData"] = None,
):
    """
    Saves strategies and parameters in session_state.

    Args:
        all_comparisons: All strategies
        params: Sidebar parameters
        best_target_price: Optimal target price
        scenarios: Market scenarios (optional)
    """
    import streamlit as st

    st.session_state["current_strategies"] = all_comparisons
    st.session_state["comparisons"] = all_comparisons  # For email link access
    st.session_state["current_params"] = {
        "underlying": params.underlying,
        "target_price": best_target_price,
        "months": params.months,
        "years": params.years,
        "strikes": params.strikes,
        "max_legs": params.max_legs,
        "price_min": params.price_min,
        "price_max": params.price_max,
    }

    # Save scenarios if provided
    if scenarios is not None:
        st.session_state["current_scenarios"] = {
            "centers": scenarios.centers,
            "std_devs": scenarios.std_devs,
            "weights": scenarios.weights,
        }


def display_success_stats(stats: Dict[str, Any]):
    """
    Displays success statistics after processing.

    Args:
        stats: Statistics dictionary
    """
    import streamlit as st

    st.success(
        f"""✅ Processing completed successfully!
    • {stats.get('nb_options', 0)} options converted
    • {stats.get('nb_strategies_totales', 0)} strategies generated
    • {stats.get('nb_strategies_classees', 0)} best strategies identified
    """
    )
