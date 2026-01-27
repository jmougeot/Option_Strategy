from myproject.option.option_class import Option
from typing import List, Any, Dict, Union


def get_expiration_info(options: Union[List[Option], List[List[Option]]]) -> Dict[str, Any]:
    """
    Extrait les informations d'expiration communes d'une liste d'options.

    Args:
        options: Liste d'options ou liste de listes d'options

    Returns:
        Dict avec expiration_month, expiration_year
    """
    default = {
        "expiration_month": "F",
        "expiration_year": 6,
    }
    
    if not options:
        return default

    first_option = options[0]
    
    # Si c'est une liste de listes, prendre le premier élément de la première liste
    if isinstance(first_option, list):
        if not first_option:
            return default
        first_option = first_option[0]
    
    # Vérifier que c'est bien un objet Option
    if not isinstance(first_option, Option):
        return default
    
    return {
        "expiration_month": first_option.expiration_month,
        "expiration_year": first_option.expiration_year,
    }
