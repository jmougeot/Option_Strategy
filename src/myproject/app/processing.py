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

    best_target_price = best_strategies[0].target_price

    # Filtrer pour le meilleur prix cible
    comparisons = [c for c in best_strategies if c.target_price == best_target_price]

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
    Sauvegarde les stratégies et paramètres dans session_state.

    Args:
        all_comparisons: Toutes les stratégies
        params: Paramètres de la sidebar
        best_target_price: Prix cible optimal
        scenarios: Scénarios de marché (optionnel)
    """
    import streamlit as st

    st.session_state["current_strategies"] = all_comparisons
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

    # Enregistrer les scénarios si fournis
    if scenarios is not None:
        st.session_state["current_scenarios"] = {
            "centers": scenarios.centers,
            "std_devs": scenarios.std_devs,
            "weights": scenarios.weights,
        }


def display_success_stats(stats: Dict[str, Any]):
    """
    Affiche les statistiques de succès après le traitement.

    Args:
        stats: Dictionnaire des statistiques
    """
    import streamlit as st

    st.success(
        f"""✅ Traitement terminé avec succès !
    • {stats.get('nb_options', 0)} options converties
    • {stats.get('nb_strategies_totales', 0)} stratégies générées
    • {stats.get('nb_strategies_classees', 0)} meilleures stratégies identifiées
    """
    )
