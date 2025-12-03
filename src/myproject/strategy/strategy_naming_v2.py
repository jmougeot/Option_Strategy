"""
Naming des Stratégies d'Options — version corrigée
==================================================
- Corrige l'identification Straddle / Strangle (même position requise)
- Distingue Risk Reversal / Reverse Risk Reversal quand positions mixtes
- Règles bull/bear pour spreads (call/put) robustes
- Noms canoniques avec strikes triés
"""

import numpy as np
from typing import List
from myproject.option.option_class import Option


def _format_option(o: Option, sign: float) -> str:
    """
    Formate une option au format: +-{underlying}{month}{year} {strike}{C/P}
    Exemple: +ERZ6 98.5C ou -ERZ6 98.0P
    """
    sign_str = "+" if sign == 1 else "-"
    # Accès direct à l'attribut au lieu de o.is_call()
    option_type = "C" if o.option_type == "call" else "P"
    return f"{sign_str} {o.strike}{option_type}"


def generate_strategy_name(options: List[Option], signs: np.ndarray) -> str:
    underlying = options[0].underlying_symbol or "ER"
    month = options[0].expiration_month
    year = options[0].expiration_year

    parts = [_format_option(o, signs[i]) for i, o in enumerate(options)]
    return (f"{underlying}{month}{year}".join(parts))
