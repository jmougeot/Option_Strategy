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
from myproject.app.filter_widget import FilterData

def sort_options_by_expiration(options: List[Option]) -> List[Option]:
    """
    Trie les options par date d'expiration (année > mois > semaine > jour).
    """

    def expiration_key(opt: Option):
        # expiration_month est une lettre (F,G,H...) : on la convertit en index
        month_order = ["F", "G", "H", "J", "K", "M", "N", "Q", "U", "V", "X", "Z"]
        try:
            month_index = month_order.index(opt.expiration_month)
        except ValueError:
            month_index = -1  # si valeur inattendue, met à la fin
        return (opt.expiration_year, month_index)

    return sorted(options, key=expiration_key)


class OptionStrategyGeneratorV2:
    """
    Génère toutes les strtégies à partir d'une liste d'options 
    """


    def __init__(self, options: List[Option]):
        """
        Initilisation du générateur 
        """
        sorted_by_exp = sort_options_by_expiration(options)
        self.options = sorted(sorted_by_exp, key=lambda opt: opt.strike)
        
        # Initialiser le cache C++ avec les options
        if not init_cpp_cache(self.options):
            raise RuntimeError("Failed to initialize C++ cache with options")

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

