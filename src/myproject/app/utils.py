# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

from typing import Dict, List
from myproject.option.option_class import Option


def prepare_options_data(options: List[Option]) -> Dict[str, List[Option]]:
    """SÃ©pare les calls et puts."""
    calls = [opt for opt in options if opt.option_type == "call"]
    puts = [opt for opt in options if opt.option_type == "put"]

    return {"calls": calls, "puts": puts}


def format_currency(value: float) -> str:
    """Formats a value as currency."""
    if value == float("inf"):
        return "Unlimited"
    return f"{value:.2f}"


def format_price(value: float, unit: str = "100ème") -> str:
    """Formats a price value, converting to 64ths if needed.
    
    Args:
        value: The price value (in decimal, e.g. 0.0625)
        unit: "64ème" to display in 64ths, otherwise decimal
    """
    if value is None:
        return "-"
    if value == float("inf") or value == float("-inf"):
        return "Unlimited"
    if unit == "64ème":
        ticks_64 = value * 100 / 64
        return f"{ticks_64:.2f}"
    return f"{value:.3f}"


def format_percentage(value: float) -> str:
    """Formats a percentage."""
    return f"{value:.1f}%"


def format_expiration_date(month: str, year: int) -> str:
    """
    Formate la date d'expiration à partir du mois Bloomberg et de l'année.
    """
    month_names = {
        "F": "Jan",
        "G": "Feb",
        "H": "Mar",
        "K": "Apr",
        "M": "Jun",
        "N": "Jul",
        "Q": "Aug",
        "U": "Sep",
        "V": "Oct",
        "X": "Nov",
        "Z": "Dec",
    }

    month_name = month_names.get(month, month)
    full_year = 2020 + year

    return f"{month_name} {full_year}"

def strike_list(strike_min: float, strike_max: float, step: float) -> List[float]:
    """
    Génére une liste de strike entre le point strike min et strike max
    """
    # Calculer le nombre de steps nÃ©cessaires
    num_steps = int(round((strike_max - strike_min) / step)) + 1
    
    # GÃ©nÃ©rer les strikes par multiplication pour Ã©viter l'accumulation d'erreurs
    strike_list = [round(strike_min + i * step, 10) for i in range(num_steps)]
    
    return strike_list
