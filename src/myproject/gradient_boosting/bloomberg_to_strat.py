from typing import List, Optional
from myproject.gradient_boosting.option_generator_v2 import OptionStrategyGeneratorV2
from myproject.strategy.comparison_class import StrategyComparison
from myproject.bloomberg.bloomberg_data_importer import import_euribor_options
from myproject.app.scenario import create_mixture_from_scenarios
from myproject.app.widget import ScenarioData


def process_bloomberg_to_strategies(
    underlying: str = "ER",
    months: List[str] = [],
    years: List[int] = [],
    strikes: List[float] = [],
    target_price: float = 0.0,
    price_min: float = 0.0,
    price_max: float = 100.0,
    max_legs: int = 4,
    scenarios: Optional[ScenarioData] = None,
    num_points: int = 200,
) -> List[StrategyComparison]:
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
        scenarios, price_min, price_max, num_points, target_price
    )

    options = import_euribor_options(
        underlying=underlying,
        months=months,
        years=years,
        strikes=strikes,
        default_position="long",
        mixture=mixture,
    )

    stats["nb_options"] = len(options)

    generator = OptionStrategyGeneratorV2(options)

    all_strategies = generator.generate_all_combinations(
        target_price=target_price,
        price_min=price_min,
        price_max=price_max,
        max_legs=max_legs,
        include_long=True,
        include_short=True,
    )

    return all_strategies
