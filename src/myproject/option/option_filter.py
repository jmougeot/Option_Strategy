from typing import List
from myproject.option.option_class import Option


def sort_options_by_strike(options: List[Option]) -> List[Option]:
    """
    Trie les options par strike croissant.

    Args:
        options: Liste d'objets Option.

    Returns:
        Liste triée d'objets Option par strike croissant.
    """
    return sorted(options, key=lambda opt: opt.strike)


def sort_options_by_expiration(options: List[Option]) -> List[Option]:
    """
    Trie les options par date d'expiration (année > mois > semaine > jour).

    Args:
        options: Liste d'objets Option.

    Returns:
        Liste triée d'objets Option.
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
