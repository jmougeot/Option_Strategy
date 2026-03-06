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


def adjust_prices(
    results: List[LegResult],
    target_price: float,
) -> List[LegResult]:
    """Ajuste proportionnellement les mids pour que le prix stratégie = target_price.

    Le prix stratégie Bloomberg = Σ (sign_i × qty_i × mid_i) sur les legs ayant un mid.
    On calcule un ratio = target_price / prix_bbg et on applique ratio × mid_i.
    Les legs sans mid sont ignorés (adjusted_mid reste None).
    """
    # Calculer le prix stratégie Bloomberg sur les legs disponibles
    bbg_total = 0.0
    has_any = False
    for lr in results:
        if lr.bbg_mid is None:
            lr.adjusted_mid = None
            continue
        has_any = True
        sign = 1 if lr.leg.position == Position.LONG else -1
        bbg_total += sign * lr.leg.quantity * lr.bbg_mid

    if not has_any or bbg_total == 0:
        for lr in results:
            lr.adjusted_mid = lr.bbg_mid
        return results

    ratio = target_price / bbg_total

    for lr in results:
        if lr.bbg_mid is not None:
            lr.adjusted_mid = lr.bbg_mid * ratio

    return results

    return results
