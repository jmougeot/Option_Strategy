"""
GÃ©nÃ©rateur V2 de StratÃ©gies d'Options
======================================

GÃ©nÃ¨re toutes les combinaisons de stratÃ©gies d'options via le module C++.
Le traitement est entiÃ¨rement dÃ©lÃ©guÃ© au batch processor C++ pour des performances optimales.
"""

from typing import List, Tuple, Optional, Dict
from myproject.option.option_class import Option
from myproject.strategy.strategy_class import StrategyComparison
from myproject.strategy.batch_processor import process_batch_cpp_with_scoring, init_cpp_cache
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
        init_cpp_cache(options)
    
    def generate_top_strategies(
        self,
        filter: FilterData,
        max_legs: int = 4,
        top_n: int = 10,
        custom_weights: Optional[Dict[str, float]] = None
    ) -> List[StrategyComparison]:

        strategies = process_batch_cpp_with_scoring(
            max_legs,
            filter,
            top_n=top_n,
            custom_weights=custom_weights
        )
        return strategies

