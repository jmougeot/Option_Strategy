"""
Workflow Principal - Bloomberg to Strategy Comparison
======================================================
Ce module implémente le workflow complet :
1. Import des données Bloomberg
2. Conversion en objets Option
3. Génération de toutes les stratégies possibles
4. Comparaison et ranking des stratégies

Utilise les fonctions optimisées des modules :
- option_generator_v2.OptionStrategyGeneratorV2
- comparor_v2.StrategyComparerV2
"""

from typing import List, Dict, Optional, Tuple
from myproject.strategy.option_generator_v2 import OptionStrategyGeneratorV2
from myproject.strategy.scoring.comparer import StrategyComparerV2
from myproject.strategy.comparison_class import StrategyComparison
from myproject.bloomberg.bloomberg_data_importer import import_euribor_options
from myproject.app.scenarios_widget import create_mixture_from_scenarios
from myproject.app.scenarios_widget import ScenarioData
from myproject.app.utils import filter_same_strategies
from myproject.app.filter_widget import FilterData
import numpy as np


def process_bloomberg_to_strategies(
    filter: FilterData,
    scenarios: ScenarioData,
    underlying: str = "ER",
    months: List[str] = [],
    years: List[int] = [],
    strikes: List[float] = [],
    price_min: float = 0.0,
    price_max: float = 100.0,
    max_legs: int = 4,
    top_n: int = 10,
    scoring_weights: Optional[Dict[str, float]] = None,
    num_points: int = 200,
    brut_code: Optional[List[str]] = None,
    compute_roll: bool = True,
    roll_month: Optional[str] = None,
    roll_year: Optional[int] = None,
) -> Tuple[List[StrategyComparison], Dict, Tuple[np.ndarray, np.ndarray]]:
    """
    Fonction principale simplifiée pour Streamlit.
    Importe les options depuis Bloomberg et retourne les meilleures stratégies + stats.

    Args:
        underlying: Symbole du sous-jacent (ex: "ER")
        months: Liste des mois Bloomberg (ex: ['M', 'U'])
        years: Liste des années (ex: [6, 7])
        strikes: Liste des strikes
        target_price: Prix cible
        price_min: Prix minimum
        price_max: Prix maximum
        max_legs: Nombre max de legs par stratégie
        top_n: Nombre de meilleures stratégies à retourner
        scoring_weights: Poids personnalisés pour le scoring
        verbose: Affichage détaillé
    """
    stats = {}

    mixture = create_mixture_from_scenarios(
        scenarios, price_min, price_max, num_points
    )

    options = import_euribor_options(
        brut_code=brut_code,
        underlying=underlying,
        months=months,
        years=years,
        strikes=strikes,
        default_position="long",
        mixture=mixture,
        compute_roll=compute_roll,
        roll_month=roll_month,
        roll_year=roll_year,
    )

    stats["nb_options"] = len(options)

    if not options:
        return [], stats, mixture

    generator = OptionStrategyGeneratorV2(options)

    all_strategies = generator.generate_all_combinations(
        price_min=price_min,
        price_max=price_max,
        max_legs=max_legs,
        filter=filter
    )

    stats["nb_strategies_totales"] = len(all_strategies)


    comparer = StrategyComparerV2()
    best_strategies = comparer.compare_and_rank(
        strategies=all_strategies, top_n=top_n, weights=scoring_weights
    )

    # Remove duplicate strategies with identical P&L profiles
    best_strategies = filter_same_strategies(best_strategies)

    stats["nb_strategies_classees"] = len(best_strategies)

    return best_strategies, stats, mixture
