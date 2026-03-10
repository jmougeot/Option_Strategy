"""
Block Service
=============
Fetch les données Bloomberg pour les legs d'une stratégie (via BDP/BDH),
puis ajuste proportionnellement les prix individuels pour que la somme
corresponde au prix stratégie saisi par l'utilisateur.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import List, Optional
from math import gcd
from functools import reduce
from alarm.models.strategy import OptionLeg, Position, Strategy


@dataclass
class LegResult:
    """Résultat pour un leg après fetch + ajustement."""
    leg: OptionLeg
    bbg_bid: Optional[float] = None
    bbg_ask: Optional[float] = None
    bbg_mid: Optional[float] = None
    adjusted_mid: Optional[float] = None


def _signed_quantity(result: LegResult) -> int:
    """Quantité signée du leg pour le calcul du prix stratégie."""
    sign = 1 if result.leg.position == Position.LONG else -1
    return sign * result.leg.quantity


def _clone_results(results: List[LegResult]) -> List[LegResult]:
    """Clone superficiellement les LegResult pour éviter les effets de bord."""
    return [replace(result) for result in results]


def _initial_ticks(results: List[LegResult], step: float, target_ticks: int) -> List[int]:
    """Construit une base de ticks cohérente pour tous les legs."""
    priced_ticks: List[Optional[int]] = []
    positive_ticks: List[int] = []

    for result in results:
        if result.bbg_mid is None or result.bbg_mid <= 0:
            priced_ticks.append(None)
            continue

        ticks = max(round(result.bbg_mid / step), 0)
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


def fetch_legs_prices(strategy: Strategy) -> List[LegResult]:
    """Fetch les prix Bloomberg pour chaque leg de la stratégie.

    Utilise le fetcher existant (BDP + BDH fallback).
    Retourne une liste de LegResult avec les prix bruts Bloomberg.
    """
    from bloomberg.refdata.fetcher import _bdp_fetch, _bdh_fallback, _has_prices
    from bloomberg.connection import get_session, get_service

    tickers = [leg.ticker for leg in strategy.legs if leg.ticker]
    if not tickers:
        return [LegResult(leg=leg) for leg in strategy.legs]

    session = get_session()
    service = get_service()

    # BDP pour tous les champs
    bdp_raw = _bdp_fetch(session, service, tickers, use_overrides=True)

    # BDH fallback pour ceux sans prix
    missing = [t for t in tickers if not _has_prices(bdp_raw.get(t, {}))]
    bdh_raw = {}
    if missing:
        bdh_raw = _bdh_fallback(session, service, missing, lookback_days=10, use_overrides=True)

    results: List[LegResult] = []
    for leg in strategy.legs:
        lr = LegResult(leg=leg)
        if not leg.ticker:
            results.append(lr)
            continue

        data = dict(bdp_raw.get(leg.ticker, {}))
        if leg.ticker in bdh_raw:
            data.update(bdh_raw[leg.ticker])

        bid = data.get("PX_BID")
        ask = data.get("PX_ASK")
        mid = data.get("PX_MID")

        lr.bbg_bid = float(bid) if bid is not None else None
        lr.bbg_ask = float(ask) if ask is not None else None

        # Calculer le mid
        if mid is not None and float(mid) > 0:
            lr.bbg_mid = float(mid)
        elif lr.bbg_bid is not None and lr.bbg_ask is not None:
            lr.bbg_mid = (lr.bbg_bid + lr.bbg_ask) / 2
        elif lr.bbg_ask is not None:
            lr.bbg_mid = lr.bbg_ask / 2
        elif lr.bbg_bid is not None:
            lr.bbg_mid = lr.bbg_bid

        results.append(lr)

    return results



def is_possible(target: float, 
                step : float):
    if (target / step) :
        return


def adjust_prices(results: List[LegResult], step: float, target_price: float) -> List[LegResult]:
    tol = 1e-9
    result_copy = _clone_results(results)

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