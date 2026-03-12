from typing import List, Dict, Optional, Tuple, Union
from datetime import datetime
from dateutil.relativedelta import relativedelta
from strategy.option_generator_v2 import OptionStrategyGeneratorV2
from strategy.strategy_class import StrategyComparison
from strategy.multi_ranking import MultiRankingResult
from bloomberg.refdata.importer import import_options
from bloomberg.refdata.importer_offline import import_options_offline, is_offline_mode
from app.data_types import ScenarioData, FilterData, FutureData
from strategy.batch_processor import clear_caches
from mixture.mixture_utils import create_mixture_from_scenarios
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
    top_n: int = 30,
    scoring_weights: Optional[Union[Dict[str, float], List[Dict[str, float]]]] = None,
    num_points: int = 200,
    brut_code: Optional[List[str]] = None,
    roll_expiries: Optional[List[Tuple[str, int]]] = None,
    recalibrate: bool = True,
    vol_model: str = "sabr",
    leg_penalty: float = 0.0,
    prefilled_options: Optional[List] = None,
) -> Tuple[Union[List[StrategyComparison], MultiRankingResult], Dict, Tuple[np.ndarray, np.ndarray, float], FutureData]:
    """
    Fonction principale simplifiee pour Streamlit.
    Importe les options depuis Bloomberg (ou simulation offline) et retourne les meilleures strategies + stats.
    """

    stats = {}
    future_data = FutureData(None, None)

    # Creer la mixture de scenarios
    mixture = create_mixture_from_scenarios(
        scenarios, price_min, price_max, num_points
    )

    # -- Shortcut: options pré-chargées (rerun depuis page Volatility) --
    if prefilled_options is not None:
        options = prefilled_options
        stats["future_data"] = future_data
        stats["all_options"] = options
        stats["nb_options"] = len(options)
        if not options:
            return [], stats, mixture, future_data
        # Recalculer pnl_array / average_pnl / sigma_pnl avec les premium/IV édités
        prices_grid, mixture_probs, _ = mixture
        for opt in options:
            opt.prices = prices_grid
            opt.mixture = mixture_probs
            opt._calcul_all_surface()
        # Générer les stratégies
        generator = OptionStrategyGeneratorV2(options)
        if isinstance(scoring_weights, list):
            weight_sets = scoring_weights
        elif isinstance(scoring_weights, dict):
            weight_sets = [scoring_weights]
        else:
            weight_sets = [{}]
        best_strategies = generator.generate_top_strategies_multi(
            filter=filter,
            max_legs=max_legs,
            top_n=top_n,
            weight_sets=weight_sets,
            leg_penalty=leg_penalty,
        )
        from math import comb
        n_opts = len(options)
        stats["nb_strategies_possibles"] = sum(comb(n_opts, k) * (2 ** k) for k in range(1, max_legs + 1))
        stats["nb_strategies_classees"] = len(best_strategies.consensus_strategies)
        clear_caches()
        return best_strategies, stats, mixture, future_data

    # Verifier le mode offline
    offline = is_offline_mode()

    # Fetch options: Bloomberg ou Simulation selon OFFLINE_MODE
    if offline:
        options, underlying_price, sabr_calibration = import_options_offline(
            mixture=mixture,
            underlying=underlying,
            months=months,
            years=years,
            strikes=strikes,
            default_position="long",
            recalibrate=recalibrate,
            vol_model=vol_model,
        )
        # En mode offline, définir une date par défaut de 5 mois dans le futur
        default_expiry_date = (datetime.now() + relativedelta(months=5)).strftime("%Y-%m-%d")
        future_data = FutureData(underlying_price, default_expiry_date)
    else:
        options, future_data, fetch_warnings, sabr_calibration = import_options(
            mixture=mixture,
            underlying=underlying,
            months=months,
            years=years,
            strikes=strikes,
            roll_expiries=roll_expiries,
            brut_code=brut_code,
            default_position="long",
            recalibrate=recalibrate,
            vol_model=vol_model,
        )

    # Tracker du fetch
    stats["future_data"] = future_data
    stats["all_options"] = options  # Toutes les options importées (pour page Volatility)
    stats["sabr_calibration"] = sabr_calibration

    if not offline and fetch_warnings: #type: ignore
        stats["fetch_warnings"] = fetch_warnings


    stats["nb_options"] = len(options)

    if not options:
        return [], stats, mixture, future_data

    # Generer les strategies avec SCORING C++ int�gr�
    generator = OptionStrategyGeneratorV2(options)

    # Normaliser en liste de dicts de poids
    if isinstance(scoring_weights, list):
        weight_sets = scoring_weights
    elif isinstance(scoring_weights, dict):
        weight_sets = [scoring_weights]
    else:
        weight_sets = [{}]

    # Toujours utiliser le multi-scoring (fonctionne aussi avec 1 jeu)
    best_strategies = generator.generate_top_strategies_multi(
        filter=filter,
        max_legs=max_legs,
        top_n=top_n,
        weight_sets=weight_sets,
        leg_penalty=leg_penalty,
    )

    # Estimer le nombre de combinaisons screened
    # Pour N options et k legs: C(N,k) * 2^k (long/short pour chaque leg)
    # Total = S(k=1 � max_legs) C(N,k) * 2^k
    from math import comb
    n_opts = len(options)
    total_combinations = sum(comb(n_opts, k) * (2 ** k) for k in range(1, max_legs + 1))
    stats["nb_strategies_possibles"] = total_combinations
    stats["nb_strategies_classees"] = len(best_strategies.consensus_strategies)

    # Lib�rer les caches (les r�sultats sont d�j� dans best_strategies)
    clear_caches()

    return best_strategies, stats, mixture, future_data

