"""
Column indices and headers for the AlarmPage table.
"""

# ── column indices ────────────────────────────────────────────────────────────
C_DOT    = 0
C_CLIENT = 1
C_NAME   = 2
C_ACTION = 3
C_LEGS   = 4
C_PRICE  = 5
C_COND   = 6
C_TARGET = 7
C_STATUS = 8
C_DELTA  = 9
C_GAMMA  = 10
C_THETA  = 11
C_IV     = 12
C_FUT    = 13

HEADERS = ["⬤", "Client", "Stratégie", "Action", "Legs",
           "Prix", "Alarme si", "Cible", "Statut",
           "Δ Delta", "Γ Gamma", "Θ Theta", "IV%", "Fut."]

# How long a price must stay in the alarm zone before the alert fires (seconds)
WARN_DELAY: float = 5.0
