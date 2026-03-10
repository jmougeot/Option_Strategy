"""
Column indices and headers for the AlarmPage table.
"""

# ── column indices ────────────────────────────────────────────────────────────
from bloomberg.util import expiry


C_CLIENT = 0
C_NAME   = 1
C_ACTION = 2
C_LEGS   = 3
C_PRICE  = 4
C_COND   = 5
C_TARGET = 6
C_STATUS = 7
C_DELTA  = 8
C_GAMMA  = 9
C_THETA  = 10
C_IV     = 11
C_FUT    = 12
C_EXPIRY= 13


HEADERS = ["Client", "Stratégie", "Action", "Legs",
           "Prix", "Alarm if", "Cible", "Statut",
           "Δ", "Γ", "Θ ", "IV%", "Fut.", "expiry"]

# How long a price must stay in the alarm zone before the alert fires (seconds)
WARN_DELAY: float = 5.0
