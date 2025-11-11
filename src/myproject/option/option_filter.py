from typing import List
from myproject.option.option_class import Option


def sort_options_by_expiration(options: List[Option]) -> List[Option]:
    """
    Trie les options par date d'expiration (année > mois > semaine > jour).

    Args:
        options: Liste d'objets Option.

    Returns:
        Liste triée d'objets Option.
    """

    def expiration_key(opt: Option):
        # Convertit expiration_week en valeur numérique
        if opt.expiration_week:
            week = (
                int(opt.expiration_week)
                if isinstance(opt.expiration_week, str)
                and opt.expiration_week.isdigit()
                else 0
            )
        else:
            week = 0

        # expiration_day peut être int ou str
        if opt.expiration_day:
            if isinstance(opt.expiration_day, int):
                day = opt.expiration_day
            elif isinstance(opt.expiration_day, str) and opt.expiration_day.isdigit():
                day = int(opt.expiration_day)
            else:
                day = 0
        else:
            day = 0

        # expiration_month est une lettre (F,G,H...) : on la convertit en index
        month_order = ["F", "G", "H", "J", "K", "M", "N", "Q", "U", "V", "X", "Z"]
        try:
            month_index = month_order.index(opt.expiration_month)
        except ValueError:
            month_index = -1  # si valeur inattendue, met à la fin
        return (opt.expiration_year, month_index, week, day)

    return sorted(options, key=expiration_key)
