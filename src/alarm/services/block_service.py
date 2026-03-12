"""
Block Service
=============
Fetch les données Bloomberg pour les legs d'une stratégie (via BDP/BDH),
puis ajuste proportionnellement les prix individuels pour que la somme
corresponde au prix stratégie saisi par l'utilisateur.
"""
from __future__ import annotations

from typing import List, Optional
from math import gcd
from functools import reduce
from alarm.models.strategy import OptionLeg, Position, Strategy
from bloomberg.config import OPTION_TICKER_BLOCK_RE as _OPTION_TICKER_RE
from app.data_types import UNDERLYING_PARAMS


def tick_for_underlying(underlying: str) -> float:
    """Retourne la taille du tick pour un underlying bloc (source: UNDERLYING_PARAMS)."""
    params = UNDERLYING_PARAMS.get(underlying.upper(), {})
    return params.get("Short", 0.0025)

def _signed_quantity(leg: OptionLeg) -> int:
    """Quantité signée du leg pour le calcul du prix stratégie."""
    sign = 1 if leg.position == Position.LONG else -1
    return sign * leg.quantity


def compute_total_quantities(
    strategy: Strategy, base_total: Optional[int]
) -> None:
    """Calcule et stocke total_qty sur chaque leg proportionnellement à base_total."""
    legs = strategy.legs
    for i, leg in enumerate(legs):
        if base_total is None or not legs:
            leg.total_qty = None
        elif i == 0:
            leg.total_qty = base_total
        else:
            base_signed = _signed_quantity(legs[0])
            if base_signed == 0:
                leg.total_qty = None
            else:
                ratio = _signed_quantity(leg) / base_signed
                leg.total_qty = int(round(base_total * ratio))

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


def build_confirmation_message(strategy: Strategy) -> str:
    """Construit le message de confirmation bloc à partir des résultats courants."""
    lines = ["To confirm, Aurel BGC does the following trades:"]

    for r in strategy.legs:
        price = (r.adjusted_mid or 0.0)
        ticker_text = _format_leg_ticker(r.ticker or "")
        qty = r.total_qty if r.total_qty is not None else r.quantity
        lines.append(f"{qty:+d} {ticker_text} @ {_fmt_price(price)}")

    lines.append(f"Overall Price {_fmt_price(strategy.target_price or 0.0)}")
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


def adjust_prices(strategy: Strategy) -> None:
    """Ajuste les prix des legs en place pour atteindre strategy.target_price."""
    legs = strategy.legs
    target_price = strategy.target_price or 0.0

    if not legs:
        return

    for leg in legs:
        leg.adjusted_mid = None

    step = tick_for_underlying(legs[0].underlying)
    tol = 1e-9

    if step <= 0:
        return

    # target doit être multiple de step
    scaled_target = target_price / step
    T = round(scaled_target)
    if abs(scaled_target - T) > tol:
        return

    coeffs = [_signed_quantity(leg) for leg in legs]
    min_ticks = [1 if coeff != 0 else 0 for coeff in coeffs]

    # quantités actives signées
    qs = [abs(coeff) for coeff in coeffs if coeff != 0]
    if not qs:
        return

    # contrainte pgcd
    g = reduce(gcd, qs)
    base_ns = _initial_ticks(legs, step, T)
    base_ns = [max(base_n, min_n) for base_n, min_n in zip(base_ns, min_ticks)]
    current = sum(coeff * n for coeff, n in zip(coeffs, base_ns))
    diff = T - current

    if diff % g != 0:
        return

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
        return

    # mettre à jour les prix directement sur les legs
    for leg, n in zip(legs, ns):
        leg.adjusted_mid = n * step