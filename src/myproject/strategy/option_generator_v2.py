"""
GÃ©nÃ©rateur V2 de StratÃ©gies d'Options
======================================

GÃ©nÃ¨re toutes les combinaisons de stratÃ©gies d'options via le module C++.
Le traitement est entiÃ¨rement dÃ©lÃ©guÃ© au batch processor C++ pour des performances optimales.
"""

from typing import List, Tuple
from myproject.option.option_class import Option
from myproject.strategy.strategy_class import StrategyComparison
from myproject.strategy.batch_processor import generate_all_strategies_batch
from myproject.option.option_filter import sort_options_by_expiration, sort_options_by_strike
from myproject.app.filter_widget import FilterData


class OptionStrategyGeneratorV2:
    """
    Génère toutes les strtégies à partir d'une liste d'options 
    """

    def __init__(self, options: List[Option]):
        """
        Initilisation du générateur 
        """
        # Trier les options par expiration puis par strike croissant
        sorted_by_exp = sort_options_by_expiration(options)
        self.options = sort_options_by_strike(sorted_by_exp)

    def generate_all_combinations(
        self, 
        filter: FilterData, 
        max_legs: int = 4,
        progress_tracker=None,
    ) -> Tuple[List[StrategyComparison], int]:
        """
        Géneration         
        Traitement au batch processor C++ pour des performances optimales.
        """        
        strategies, grand_total = generate_all_strategies_batch(
            progress_tracker,
            self.options, 
            filter, 
            max_legs
        )
        return strategies, grand_total

