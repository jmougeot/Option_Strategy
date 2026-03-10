"""
Block Service
=============
Fetch les données Bloomberg pour les legs d'une stratégie (via BDP/BDH),
puis ajuste proportionnellement les prix individuels pour que la somme
corresponde au prix stratégie saisi par l'utilisateur.
"""
from __future__ import annotations

from dataclasses import dataclass
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


def adjust_prices(results: List[LegResult], step: float, target_price: float) -> List["LegResult"]:
    tol = 1e-9
    result_copy = results.copy()

    # target doit être multiple de step
    scaled_target = target_price / step
    T = round(scaled_target)
    if abs(scaled_target - T) > tol:
        return []

    # quantités actives
    qs = [abs(l.leg.quantity) for l in results if l.leg.quantity != 0]
    if not qs:
        return results if abs(target_price) < tol else []

    # contrainte pgcd
    g = reduce(gcd, qs)
    if T % g != 0:
        return result_copy

    # initialisation sur la grille
    ns = []
    for l in results:
        if l.bbg_mid is None:
            n = 0
        else:
            n = round(l.bbg_mid / step)
        ns.append(n)

    # somme actuelle
    current = sum(l.leg.quantity * n for l, n in zip(results, ns))
    diff = T - current

    # correction gloutonne
    max_iter = 10000
    i = 0

    while diff != 0 and i < max_iter:
        best_idx = None
        best_after = abs(diff)

        for idx, l in enumerate(results):
            q = l.leg.quantity

            after_plus = abs(diff - q)
            if after_plus < best_after:
                best_after = after_plus
                best_idx = (idx, 1)

            after_minus = abs(diff + q)
            if after_minus < best_after:
                best_after = after_minus
                best_idx = (idx, -1)

        if best_idx is None:
            break

        idx, direction = best_idx
        ns[idx] += direction
        diff -= direction * results[idx].leg.quantity
        i += 1

    if diff != 0:
        return result_copy

    # reconstruire les prix
    for l, n in zip(results, ns):
        l.adjusted_mid = n * step

    return results