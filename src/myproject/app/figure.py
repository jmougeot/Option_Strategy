import pandas as pd
from myproject.app.utils import format_currency

def create_comparison_table(comparisons) -> pd.DataFrame:
    """Crée un tableau de comparaison des stratégies - VERSION SUPPRIMÉE, utiliser app.utils"""
    # Cette fonction est maintenant dans app/utils.py pour éviter les doublons
    from myproject.app.utils import create_comparison_table as _create_comparison_table
    return _create_comparison_table(comparisons)
