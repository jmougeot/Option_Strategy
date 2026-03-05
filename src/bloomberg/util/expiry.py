"""
Utilitaires de gestion des échéances Bloomberg
===============================================
Constantes pour manipuler les mois et années d'expiration.
"""

# Liste ordonnée des mois Bloomberg
# F=Jan, G=Feb, H=Mar, J=Apr, K=May, M=Jun, N=Jul, Q=Aug, U=Sep, V=Oct, X=Nov, Z=Dec
MONTH_ORDER = ["F", "G", "H", "J", "K", "M", "N", "Q", "U", "V", "X", "Z"]

# Mois trimestriels pour le roll (H=Mar, M=Jun, U=Sep, Z=Dec)
QUARTERLY_MONTHS = ["H", "M", "U", "Z"]

# Mapping des mois Bloomberg vers les noms complets
MONTH_NAMES = {
    "F": "January",
    "G": "February",
    "H": "March",
    "J": "April",
    "K": "May",
    "M": "June",
    "N": "July",
    "Q": "August",
    "U": "September",
    "V": "October",
    "X": "November",
    "Z": "December",
}
