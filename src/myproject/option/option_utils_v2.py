import numpy as np
from myproject.option.option_class import Option 
from typing import List, Any, Dict


def get_expiration_info(options: List[Option]) -> Dict[str, Any]:
    """
    Extrait les informations d'expiration communes d'une liste d'options.
    
    Args:
        options: Liste d'options
    
    Returns:
        Dict avec expiration_month, expiration_year, expiration_day, expiration_week
    """
    if not options:
        return {
            'expiration_month': 'F',
            'expiration_year': 6,
            'expiration_day': None,
            'expiration_week': None
        }
    
    first_option = options[0]
    return {
        'expiration_month': first_option.expiration_month,
        'expiration_year': first_option.expiration_year,
        'expiration_day': first_option.expiration_day,
        'expiration_week': first_option.expiration_week
    }
