"""
Bloomberg — Configuration centralisée
======================================
Source unique de vérité pour :
  - Paramètres de connexion (host / port)
  - Noms des services Bloomberg
  - Listes de champs (subscription live, reference data)
  - Normalisation des tickers

Tous les modules qui touchent Bloomberg importent depuis ici.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
import calendar


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------
MKTDATA_SERVICE = "//blp/mktdata"   # Flux temps réel (subscriptions)
REFDATA_SERVICE  = "//blp/refdata"   # Données de référence (requêtes ponctuelles)


# ---------------------------------------------------------------------------
# Connexion
# ---------------------------------------------------------------------------
@dataclass
class BloombergConfig:
    """Paramètres de connexion au terminal Bloomberg."""
    host: str = "localhost"
    port: int = 8194


# Instance partagée — modifier avant de démarrer toute session.
# Exemple :  from bloomberg.config import config ; config.host = "192.168.1.10"
config = BloombergConfig()


# ---------------------------------------------------------------------------
# Champs Bloomberg
# ---------------------------------------------------------------------------

# Champs pour les subscriptions temps réel (//blp/mktdata)
SUBSCRIPTION_FIELDS: list[str] = [
    "LAST_PRICE", "BID", "ASK",
]

# Champs pour les requêtes de données de référence options (//blp/refdata)
OPTION_FIELDS: list[str] = [
    "PX_BID", "PX_ASK", "PX_MID", "PX_LAST",
    "OPT_DELTA", "OPT_GAMMA", "OPT_VEGA", "OPT_THETA", "OPT_RHO",
    "OPT_IMP_VOL", "IVOL_MID", "IVOL_BID", "IVOL_ASK",
    "OPT_STRIKE_PX", "OPT_UNDL_PX", "OPT_PUT_CALL",
    "VOLUME", "OPEN_INT",
    "LAST_TRADEABLE_DT", "OPT_EXPIRE_DT",
]


# ---------------------------------------------------------------------------
# Normalisation des tickers
# ---------------------------------------------------------------------------
def normalize_ticker(ticker: str) -> str:
    """Normalise un ticker Bloomberg : majuscules, corrige COMDTY, espaces uniques.

    Exemple : ``"sfrh6c 98.0  comdity"`` → ``"SFRH6C 98.0 COMDTY"``
    """
    if not ticker:
        return ""
    ticker = ticker.strip().upper()
    ticker = re.sub(r'\bCOMDITY\b',  'COMDTY', ticker, flags=re.IGNORECASE)
    ticker = re.sub(r'\bCOMODITY\b', 'COMDTY', ticker, flags=re.IGNORECASE)
    ticker = re.sub(r'\bCOMDTY\b',   'COMDTY', ticker, flags=re.IGNORECASE)
    ticker = re.sub(r'\s+', ' ', ticker)
    return ticker


# ---------------------------------------------------------------------------
# Option ticker — expressions régulières (source unique de vérité)
# ---------------------------------------------------------------------------

# Captures: (underlying_2-4_chars, strike) — pour identifier l'underlying et le strike
OPTION_TICKER_RE = re.compile(
    r"^([A-Z0-9]{2,4})[FGHJKMNQUVXZ]\d[CP]\s+(\d+(?:\.\d+)?)\s+COMDTY$",
    re.IGNORECASE,
)

# Captures: (underlying, month_code, year_1-2_digits, C/P, strike) — pour résoudre l'expiry
OPTION_TICKER_DETAILS_RE = re.compile(
    r"^([A-Z0-9]{2,4})([FGHJKMNQUVXZ])(\d{1,2})([CP])\s+(\d+(?:\.\d+)?)\s+COMDTY$",
    re.IGNORECASE,
)

# Captures: (future_code_with_expiry_month_year) — pour dériver le ticker future
FUTURE_TICKER_RE = re.compile(
    r'^([A-Z0-9]+[FGHJKMNQUVXZ]\d+)[CP]\s', re.IGNORECASE
)

# Captures: (base_with_expiry, C/P, strike) — pour le formatage des messages bloc
OPTION_TICKER_BLOCK_RE = re.compile(
    r"^([A-Z0-9]+[FGHJKMNQUVXZ]\d+)([CP])\s+([\d.]+)\s+COMDTY$",
    re.IGNORECASE,
)

# Mapping code mois option → numéro de mois
MONTH_TO_NUMBER: dict[str, int] = {
    "F": 1, "G": 2, "H": 3, "J": 4, "K": 5, "M": 6,
    "N": 7, "Q": 8, "U": 9, "V": 10, "X": 11, "Z": 12,
}


# ---------------------------------------------------------------------------
# Résolution de la date d'expiration (3e mercredi du mois)
# ---------------------------------------------------------------------------

def resolve_expiry_year(year_code: str) -> int:
    """Convertit un code d'année 1 ou 2 chiffres en année calendaire complète."""
    raw_year = int(year_code)
    today = date.today()
    if len(year_code) == 1:
        base_year = (today.year // 10) * 10
        resolved = base_year + raw_year
        if resolved < today.year - 1:
            resolved += 10
        return resolved
    base_year = (today.year // 100) * 100
    resolved = base_year + raw_year
    if resolved < today.year - 20:
        resolved += 100
    return resolved


def third_wednesday(year: int, month: int) -> date:
    """Retourne la date du 3e mercredi d'un mois donné (date d'expiration standard)."""
    weeks = calendar.monthcalendar(year, month)
    wednesdays = [w[calendar.WEDNESDAY] for w in weeks if w[calendar.WEDNESDAY] != 0]
    return date(year, month, wednesdays[2])
