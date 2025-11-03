from myproject.option.option_class import Option
from typing import List, Optional, Literal, Tuple
import numpy as np


def import_local_option(mixture) -> List[Option]:
    """
    Définit 16 options réelles avec les données Bloomberg.
    
    Returns:
        Liste de 16 objets Option (données réelles)
    """
    option_list: List[Option] = []
    
    # ========== OPTIONS RÉELLES BLOOMBERG ==========
    
    # Option 1: Call 97.75
    option_list.append(Option(
        option_type='call',
        strike=97.75,
        premium=0.26,
        position='long',
        delta=0.9276614039279945,
        implied_volatility=0.17838912443762343,
        expiration_month='Z',
        expiration_year=5,
        expiration_day='15'
    ))
    
    # Option 2: Call 97.8125
    option_list.append(Option(
        option_type='call',
        strike=97.8125,
        premium=0.19875,
        position='long',
        delta=0.9017197009713277,
        implied_volatility=0.15438953443057803,
        expiration_month='Z',
        expiration_year=5,
        expiration_day='15'
    ))
    
    # Option 3: Call 97.875
    option_list.append(Option(
        option_type='call',
        strike=97.875,
        premium=0.1375,
        position='long',
        delta=0.8641537460485881,
        implied_volatility=0.12448310390691912,
        expiration_month='Z',
        expiration_year=5,
        expiration_day='15'
    ))
    
    # Option 4: Call 97.9375
    option_list.append(Option(
        option_type='call',
        strike=97.9375,
        premium=0.07875,
        position='long',
        delta=0.771609,
        implied_volatility=0.09655055,
        expiration_month='Z',
        expiration_year=5,
        expiration_day='15'
    ))
    
    # Option 5: Put 97.9375
    option_list.append(Option(
        option_type='put',
        strike=97.9375,
        premium=0.00875,
        position='long',
        delta=-0.216523,
        implied_volatility=0.09190805,
        expiration_month='Z',
        expiration_year=5,
        expiration_day='15'
    ))
    
    # Option 6: Call 98.0
    option_list.append(Option(
        option_type='call',
        strike=98.0,
        premium=0.04125,
        position='long',
        delta=0.509936,
        implied_volatility=0.11140582,
        expiration_month='Z',
        expiration_year=5,
        expiration_day='15'
    ))
    
    # Option 7: Put 98.0
    option_list.append(Option(
        option_type='put',
        strike=98.0,
        premium=0.0325,
        position='long',
        delta=-0.488108,
        implied_volatility=0.10445158,
        expiration_month='Z',
        expiration_year=5,
        expiration_day='15'
    ))
    
    # Option 8: Call 98.0625
    option_list.append(Option(
        option_type='call',
        strike=98.0625,
        premium=0.02625,
        position='long',
        delta=0.31129,
        implied_volatility=0.1411286,
        expiration_month='Z',
        expiration_year=5,
        expiration_day='15'
    ))
    
    # Option 9: Put 98.0625
    option_list.append(Option(
        option_type='put',
        strike=98.0625,
        premium=0.07875,
        position='long',
        delta=-0.697689,
        implied_volatility=0.13323329,
        expiration_month='Z',
        expiration_year=5,
        expiration_day='15'
    ))
    
    # Option 10: Call 98.125
    option_list.append(Option(
        option_type='call',
        strike=98.125,
        premium=0.01625,
        position='long',
        delta=0.19821,
        implied_volatility=0.17023583,
        expiration_month='Z',
        expiration_year=5,
        expiration_day='15'
    ))
    
    # Option 11: Put 98.125
    option_list.append(Option(
        option_type='put',
        strike=98.125,
        premium=0.13125,
        position='long',
        delta=-0.822653,
        implied_volatility=0.15477908,
        expiration_month='Z',
        expiration_year=5,
        expiration_day='15'
    ))
    
    # Option 12: Call 98.1875
    option_list.append(Option(
        option_type='call',
        strike=98.1875,
        premium=0.00875,
        position='long',
        delta=0.109122,
        implied_volatility=0.17903791,
        expiration_month='Z',
        expiration_year=5,
        expiration_day='15'
    ))
    
    # Option 13: Put 98.1875
    option_list.append(Option(
        option_type='put',
        strike=98.1875,
        premium=0.1875,
        position='long',
        delta=-0.910502,
        implied_volatility=0.16310608,
        expiration_month='Z',
        expiration_year=5,
        expiration_day='15'
    ))
    
    # Option 14: Call 98.25
    option_list.append(Option(
        option_type='call',
        strike=98.25,
        premium=0.00625,
        position='long',
        delta=0.081576,
        implied_volatility=0.21635963,
        expiration_month='Z',
        expiration_year=5,
        expiration_day='15'
    ))
    
    # Option 15: Put 98.25
    option_list.append(Option(
        option_type='put',
        strike=98.25,
        premium=0.2475,
        position='long',
        delta=-0.9757908660593342,
        implied_volatility=0.15008222303984677,
        expiration_month='Z',
        expiration_year=5,
        expiration_day='15'
    ))
    
    # Option 16: Put 98.3125
    option_list.append(Option(
        option_type='put',
        strike=98.3125,
        premium=0.3075,
        position='long',
        delta=-0.9997952791421547,
        implied_volatility=0.10547756861652507,
        expiration_month='Z',
        expiration_year=5,
        expiration_day='15'
    ))
    
    # Option 17: Put 98.375 (note: IV original = 0.15, probablement 15%)
    option_list.append(Option(
        option_type='put',
        strike=98.375,
        premium=0.37,
        position='long',
        delta=-0.971057,
        implied_volatility=0.15,
        expiration_month='Z',
        expiration_year=5,
        expiration_day='15'
    ))
    
    for option in option_list :
            option.prices, option.mixture = mixture
            option._calcul_all_surface()
         


    return option_list

