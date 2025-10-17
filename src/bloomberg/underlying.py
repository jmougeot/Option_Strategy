"""
Underlying Assets Configuration
"""

from datetime import date, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


# ============================================================================
# FUTURES DE TAUX D'INTÉRÊT
# ============================================================================

# Futures de taux court terme (Money Market)
EURIBOR = "ER"    # 3M Euribor Future (Eurex) - Principal pour Europe
SONIA   = "SF"    # 3M SONIA Future (ICE) - UK
SOFR    = "SR"    # 3M SOFR Future (CME) - US (remplace Eurodollar)
ED      = "ED"    # Eurodollar (legacy, remplacé par SOFR)

# Futures obligations européennes (German Bunds)
RX      = "RX"    # Euro-Bund Future (10Y German) - Référence Europe
PY      = "PY"    # Euro-Bobl Future (5Y German)
OE      = "OE"    # Euro-Schatz Future (2Y German)
OQ      = "OQ"    # Euro-Buxl Future (30Y German)

# Futures obligations autres pays européens
DU      = "DU"    # Euro-OAT Future (10Y France)

# Futures obligations US (Treasury)
UB      = "UB"    # Ultra U.S. Treasury Bond Future (CME) - 30Y+
WN      = "WN"    # Ultra 10Y U.S. Treasury Future (CME)
TY      = "TY"    # 10Y U.S. Treasury Note Future (CME) - Référence US
FV      = "FV"    # 5Y U.S. Treasury Note Future (CME)
TU      = "TU"    # 2Y U.S. Treasury Note Future (CME)


# ============================================================================
# CONFIGURATION DÉTAILLÉE DES FUTURES DE TAUX
# ============================================================================

RATE_FUTURES_CONFIG = {
    # Money Market Futures
    'ER': {  # EURIBOR
        'name': 'EURIBOR 3 Month Future',
        'exchange': 'Eurex',
        'contract_size': 2500.0,  # €2,500 par point de base
        'tick_size': 0.01,  # 0.01 point = 1 basis point
        'tick_value': 25.0,  # €25 par tick
        'currency': 'EUR',
        'expiry_months': [3, 6, 9, 12],  # Trimestriel (H, M, U, Z)
        'underlying': '3-Month Euro Interbank Offered Rate',
    },
    
    'SF': {  # SONIA
        'name': 'Three Month SONIA Future',
        'exchange': 'ICE',
        'contract_size': 2500.0,  # £2,500 par point de base
        'tick_size': 0.005,  # 0.5 basis point
        'tick_value': 12.50,  # £12.50 par tick
        'currency': 'GBP',
        'expiry_months': [3, 6, 9, 12],
        'underlying': 'Sterling Overnight Index Average',
    },
    
    'SR': {  # SOFR
        'name': 'Three Month SOFR Future',
        'exchange': 'CME',
        'contract_size': 2500.0,  # $2,500 par point de base
        'tick_size': 0.0025,  # 0.25 basis point
        'tick_value': 6.25,  # $6.25 par tick
        'currency': 'USD',
        'expiry_months': [3, 6, 9, 12],
        'underlying': 'Secured Overnight Financing Rate',
    },
    
    # Bond Futures - German Bunds
    'RX': {  # Euro-Bund (10Y)
        'name': 'Euro-Bund Future',
        'exchange': 'Eurex',
        'contract_size': 100000.0,  # €100,000 nominal
        'tick_size': 0.01,  # 0.01 point
        'tick_value': 10.0,  # €10 par tick
        'currency': 'EUR',
        'expiry_months': [3, 6, 9, 12],
        'underlying': '10-Year German Government Bond',
        'maturity': '10Y',
    },
    
    'PY': {  # Euro-Bobl (5Y)
        'name': 'Euro-Bobl Future',
        'exchange': 'Eurex',
        'contract_size': 100000.0,
        'tick_size': 0.01,
        'tick_value': 10.0,
        'currency': 'EUR',
        'expiry_months': [3, 6, 9, 12],
        'underlying': '5-Year German Government Bond',
        'maturity': '5Y',
    },
    
    'OE': {  # Euro-Schatz (2Y)
        'name': 'Euro-Schatz Future',
        'exchange': 'Eurex',
        'contract_size': 100000.0,
        'tick_size': 0.01,
        'tick_value': 10.0,
        'currency': 'EUR',
        'expiry_months': [3, 6, 9, 12],
        'underlying': '2-Year German Government Bond',
        'maturity': '2Y',
    },
    
    # US Treasury Futures
    'TY': {  # 10Y US Treasury
        'name': '10-Year U.S. Treasury Note Future',
        'exchange': 'CME',
        'contract_size': 100000.0,  # $100,000 nominal
        'tick_size': 0.015625,  # 1/64 of a point
        'tick_value': 15.625,  # $15.625 par tick
        'currency': 'USD',
        'expiry_months': [3, 6, 9, 12],
        'underlying': '10-Year U.S. Treasury Note',
        'maturity': '10Y',
    },
    
    'FV': {  # 5Y US Treasury
        'name': '5-Year U.S. Treasury Note Future',
        'exchange': 'CME',
        'contract_size': 100000.0,
        'tick_size': 0.0078125,  # 1/128 of a point
        'tick_value': 7.8125,
        'currency': 'USD',
        'expiry_months': [3, 6, 9, 12],
        'underlying': '5-Year U.S. Treasury Note',
        'maturity': '5Y',
    },
}


# ============================================================================
# ACTIONS ET INDICES
# ============================================================================

EQUITIES = {
    'AAPL': {'name': 'Apple Inc.', 'sector': 'Technology'},
    'MSFT': {'name': 'Microsoft Corp.', 'sector': 'Technology'},
    'GOOGL': {'name': 'Alphabet Inc.', 'sector': 'Technology'},
    'AMZN': {'name': 'Amazon.com Inc.', 'sector': 'Consumer'},
    'TSLA': {'name': 'Tesla Inc.', 'sector': 'Automotive'},
    'NVDA': {'name': 'NVIDIA Corp.', 'sector': 'Technology'},
    'META': {'name': 'Meta Platforms Inc.', 'sector': 'Technology'},
}

INDICES = {
    'SPX': {'name': 'S&P 500 Index', 'multiplier': 100},
    'NDX': {'name': 'NASDAQ 100 Index', 'multiplier': 100},
    'RUT': {'name': 'Russell 2000 Index', 'multiplier': 100},
}

MONTH_CODES = {
    1: 'F',   # Janvier
    2: 'G',   # Février
    3: 'H',   # Mars
    4: 'J',   # Avril
    5: 'K',   # Mai
    6: 'M',   # Juin
    7: 'N',   # Juillet
    8: 'Q',   # Août
    9: 'U',   # Septembre
    10: 'V',  # Octobre
    11: 'X',  # Novembre
    12: 'Z'   # Décembre
}

__all__ = [
    # Symboles futures de taux
    'EURIBOR', 'SONIA', 'SOFR', 'ED',
    'RX', 'PY', 'OE', 'OQ', 'DU',
    'UB', 'WN', 'TY', 'FV', 'TU',
    
    # Configurations
    'RATE_FUTURES_CONFIG',
    'EQUITIES',
    'INDICES',
]
