from myproject.option.option_class import Option

from typing import List, Dict, Optional, Tuple
from myproject.strategy.option_generator_v2 import OptionStrategyGeneratorV2
from myproject.strategy.comparor_v2 import StrategyComparerV2
from myproject.strategy.comparison_class import StrategyComparison

price_min = 95
max_legs = 4
price_max =110
target_price = 100

opt1 = Option(option_type='call', strike=100, premium=2.50000, delta=0.55, gamma=0.08, vega=0.12, theta=-0.03, rho=0.04)
opt2 = Option(option_type='call', strike=105, premium=1.20000, delta=0.35, gamma=0.07, vega=0.10, theta=-0.02, rho=0.03)
opt3 = Option(option_type='put',  strike=95,  premium=2.80000, delta=-0.45, gamma=0.09, vega=0.13, theta=-0.04, rho=-0.05)
opt4 = Option(option_type='put',  strike=90,  premium=1.00000, delta=-0.25, gamma=0.06, vega=0.09, theta=-0.015, rho=-0.03)


List_option = [opt1, opt2, opt3, opt4]

generator = OptionStrategyGeneratorV2(List_option)


all_strategies = generator.generate_all_combinations(
    target_price=target_price,
    price_min=price_min,
    price_max=price_max,
    max_legs=max_legs,
    include_long=True,
    include_short=True
)
for stra in all_strategies :
    for leg in stra.all_options : 
        print (leg.option_type, leg.position, leg.premium)
    print (stra.strategy_name, stra.premium)
    print ("-------------------------------------------------------------------------")


