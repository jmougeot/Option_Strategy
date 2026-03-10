"""
Block Service
=============
Fetch les données Bloomberg pour les legs d'une stratégie (via BDP/BDH),
puis ajuste proportionnellement les prix individuels pour que la somme
corresponde au prix stratégie saisi par l'utilisateur.
"""
from __future__ import annotations

import re
from dataclasses import replace
from typing import List, Optional
from math import gcd
from functools import reduce
from alarm.models.strategy import OptionLeg, Position, Strategy

_OPTION_TICKER_RE = re.compile(
    r"^([A-Z0-9]+[FGHJKMNQUVXZ]\d+)([CP])\s+([\d.]+)\s+COMDTY$",
    re.IGNORECASE,
)

_TICK_BY_UNDERLYING = {
    "SFR": 0.0025,
    "SFI": 0.0025,
    "ER": 0.0025,
    "0R": 0.0025,
    "0Q": 0.005,
    "0N": 0.0025,
    "RX": 0.01,
    "OE": 0.005,
    "DU": 0.005,
}


def tick_for_underlying(underlying: str) -> float:
    """Retourne la taille du tick pour un underlying bloc."""
    return _TICK_BY_UNDERLYING.get(underlying.upper(), 0.0025)


def _signed_quantity(leg: OptionLeg) -> int:
    """Quantité signée du leg pour le calcul du prix stratégie."""
    sign = 1 if leg.position == Position.LONG else -1
    return sign * leg.quantity

def _format_leg_ticker(ticker: str) -> str:
    raw = (ticker or "").strip().upper()
    match = _OPTION_TICKER_RE.match(raw)
    if not match:
        return raw.replace(" COMDTY", "")

    base, opt_type, strike = match.groups()
    return f"{base}{opt_type} {strike} {opt_type}"


def _fmt_price(val: float) -> str:
    text = f"{val:.4f}".rstrip("0").rstrip(".")
    return "0" if text in {"", "-0"} else text


def build_confirmation_message(results: List[OptionLeg]) -> str:
    """Construit le message de confirmation bloc à partir des résultats courants."""
    lines = ["To confirm, Aurel BGC does the following trades:"]
    overall = 0.0

    for r in results:
        signed_qty = _signed_quantity(r)
        price = (r.adjusted_mid or 0.0) / r.quantity if r.quantity else 0.0
        overall += signed_qty * price
        ticker_text = _format_leg_ticker(r.ticker or "")
        lines.append(f"{signed_qty:+d} {ticker_text} @ {_fmt_price(price)}")

    lines.append(f"Overall Price {_fmt_price(overall)}")
    lines.append("(Leg prices are indicative)")
    lines.append("** Please check details and confirm **")
    return "\n".join(lines)


def _initial_ticks(results: List[OptionLeg], step: float, target_ticks: int) -> List[int]:
    """Construit une base de ticks cohérente pour tous les legs."""
    priced_ticks: List[Optional[int]] = []
    positive_ticks: List[int] = []

    for result in results:
        if result.mid is None or result.mid <= 0:
            priced_ticks.append(None)
            continue

        ticks = max(round(result.mid / step), 0)
        priced_ticks.append(ticks)
        if ticks > 0:
            positive_ticks.append(ticks)

    active_weight = sum(abs(_signed_quantity(result)) for result in results if _signed_quantity(result) != 0)
    if positive_ticks:
        fallback_tick = max(1, round(sum(positive_ticks) / len(positive_ticks)))
    elif active_weight > 0 and abs(target_ticks) > 0:
        fallback_tick = max(1, round(abs(target_ticks) / active_weight))
    else:
        fallback_tick = 0

    ticks_out: List[int] = []
    for result, priced_tick in zip(results, priced_ticks):
        if _signed_quantity(result) == 0:
            ticks_out.append(0)
        elif priced_tick is None:
            ticks_out.append(max(fallback_tick, 1))
        else:
            ticks_out.append(max(priced_tick, 1))

    return ticks_out


def adjust_prices(results: List[OptionLeg], step: float, target_price: float) -> List[OptionLeg]:
    tol = 1e-9
    result_copy = [replace(result) for result in results]
    
    if not result_copy or step <= 0:
        return result_copy

    # target doit être multiple de step
    scaled_target = target_price / step
    T = round(scaled_target)
    if abs(scaled_target - T) > tol:
        return result_copy

    coeffs = [_signed_quantity(result) for result in result_copy]
    min_ticks = [1 if coeff != 0 else 0 for coeff in coeffs]

    # quantités actives signées
    qs = [abs(coeff) for coeff in coeffs if coeff != 0]
    if not qs:
        return result_copy

    # contrainte pgcd
    g = reduce(gcd, qs)
    base_ns = _initial_ticks(result_copy, step, T)
    base_ns = [max(base_n, min_n) for base_n, min_n in zip(base_ns, min_ticks)]
    current = sum(coeff * n for coeff, n in zip(coeffs, base_ns))
    diff = T - current

    if diff % g != 0:
        return result_copy

    # initialisation sur la grille
    ns = base_ns.copy()
    move_counts = [0] * len(ns)

    # correction gloutonne équilibrée
    max_iter = max(10000, 4 * (abs(diff) + len(ns)))
    i = 0

    while diff != 0 and i < max_iter:
        best_move = None

        for idx, coeff in enumerate(coeffs):
            if coeff == 0:
                continue

            for delta_ticks in (1, -1):
                next_n = ns[idx] + delta_ticks
                if next_n < min_ticks[idx]:
                    continue

                next_diff = diff - coeff * delta_ticks
                score = (
                    abs(next_diff),
                    abs(next_n - base_ns[idx]),
                    move_counts[idx],
                    idx,
                )

                if best_move is None or score < best_move[0]:
                    best_move = (score, idx, delta_ticks, next_diff)

        if best_move is None:
            break

        _, idx, delta_ticks, next_diff = best_move
        ns[idx] += delta_ticks
        diff = next_diff
        move_counts[idx] += 1
        i += 1

    if diff != 0:
        return result_copy

    # reconstruire les prix
    for result, n in zip(result_copy, ns):
        result.adjusted_mid = n * step

    return result_copy