"""
Fonctions de scoring pour les métriques
"""


def score_higher_better(value: float, min_val: float, max_val: float) -> float:
    """Score normalisé: plus élevé = meilleur.
    Fonctionne avec des valeurs négatives en normalisant sur [min, max]."""
    if max_val <= min_val:
        return 0.5  # Toutes les valeurs identiques
    return (value - min_val) / (max_val - min_val)


def score_lower_better(value: float, min_val: float, max_val: float) -> float:
    """Score normalisé inversé: plus bas = meilleur."""
    if max_val <= min_val:
        return 0.0
    normalized = (value - min_val) / (max_val - min_val)
    return 1.0 - normalized


def score_moderate_better(value: float, min_val: float, max_val: float) -> float:
    """Score favorisant les valeurs modérées (autour de 0.5 de la plage)."""
    if max_val <= 0:
        return 0.0
    normalized = value / max_val
    score = 1.0 - abs(normalized - 0.5) * 2.0
    return max(0.0, score)


def score_positive_better(value: float, min_val: float, max_val: float) -> float:
    """Score favorisant les valeurs positives."""
    if value >= 0 and max_val > min_val:
        return (value - min_val) / (max_val - min_val)
    return 0.0


def score_call_put(value: float, min_val: float, max_val: float) -> float:
    """Score pour protection put (puts long = meilleur)."""
    if value <= -1:  # Puts LONG (protection)
        return 1.0
    elif value == 0:  # Neutre
        return 0.8
    elif value == 1:  # 1 short
        return 0.3
    return 0.0  # 2+ shorts
