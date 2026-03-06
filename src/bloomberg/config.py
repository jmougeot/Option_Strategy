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
    "DELTA", "GAMMA", "THETA", "IVOL_MID",
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
