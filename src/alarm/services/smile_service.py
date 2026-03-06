"""
Smile Service
=============
Génère une grille de strikes autour de l'ATM, fetch les IV Bloomberg,
et retourne les données nécessaires pour afficher le smile de volatilité.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ── Configuration par underlying ──────────────────────────────────────────────
DATA_UNDERLYING: Dict[str, Dict] = {
    "SFR": {"atm": 98, "step": 0.0125, "research_zone": 1.5},
}


@dataclass
class SmilePoint:
    """Un point du smile : strike + IV call/put + prix."""
    strike: float
    call_ticker: str = ""
    put_ticker: str = ""
    call_iv: Optional[float] = None
    put_iv: Optional[float] = None
    call_mid: Optional[float] = None
    put_mid: Optional[float] = None
    call_bid: Optional[float] = None
    call_ask: Optional[float] = None
    put_bid: Optional[float] = None
    put_ask: Optional[float] = None
    underlying_price: Optional[float] = None
    warning: bool = False


@dataclass
class SmileResult:
    """Résultat complet du fetch smile."""
    underlying: str
    expiry: str
    points: List[SmilePoint] = field(default_factory=list)
    forward_price: Optional[float] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_option_ticker(ticker: str) -> Optional[Dict[str, str]]:
    """Parse un ticker Bloomberg option → {underlying, expiry, type, strike}.

    Ex: "SFRH6C 98.0 COMDTY" → {underlying: "SFR", expiry: "H6", type: "C", strike: "98.0"}
    """
    m = re.match(
        r'^([A-Z]+)([FGHJKMNQUVXZ]\d+)([CP])\s+([\d.]+)\s+COMDTY$',
        ticker.strip().upper(),
    )
    if not m:
        return None
    return {
        "underlying": m.group(1),
        "expiry": m.group(2),
        "type": m.group(3),
        "strike": m.group(4),
    }


def generate_strikes(atm: float, research_zone: float, step: float) -> List[float]:
    """Génère une liste de strikes autour de l'ATM."""
    strikes = []
    s = atm - research_zone
    while s <= atm + research_zone + step * 0.5:
        strikes.append(round(s, 6))
        s += step
    return sorted(strikes)


def build_tickers(underlying: str, expiry: str, strike: float) -> Tuple[str, str]:
    """Construit les tickers call et put pour un strike donné."""
    s = f"{strike:g}"
    return (
        f"{underlying}{expiry}C {s} COMDTY",
        f"{underlying}{expiry}P {s} COMDTY",
    )


def _extract_iv(data: Dict, field_prio: Optional[List[str]] = None) -> Optional[float]:
    """Extrait l'IV depuis un dict Bloomberg, en essayant plusieurs champs."""
    if field_prio is None:
        field_prio = ["IVOL_MID", "OPT_IMP_VOL", "IVOL_BID", "IVOL_ASK"]
    for f in field_prio:
        v = data.get(f)
        if v is not None and float(v) > 0:
            return float(v)
    return None


def _extract_mid(data: Dict) -> Optional[float]:
    """Calcule le mid depuis un dict Bloomberg."""
    mid = data.get("PX_MID")
    if mid is not None and float(mid) > 0:
        return float(mid)
    bid = data.get("PX_BID")
    ask = data.get("PX_ASK")
    if bid is not None and ask is not None and float(bid) >= 0 and float(ask) > 0:
        return (float(bid) + float(ask)) / 2
    if ask is not None and float(ask) > 0:
        return float(ask) / 2
    if bid is not None and float(bid) > 0:
        return float(bid)
    return None


# ── Fonction principale ──────────────────────────────────────────────────────

def fetch_smile(underlying: str, expiry: str) -> SmileResult:
    """Fetch le smile de volatilité pour un underlying + expiry.

    Génère les strikes, fetch les IV/prix via Bloomberg BDP,
    et retourne un SmileResult prêt à être affiché.
    """
    from bloomberg.refdata.fetcher import _bdp_fetch, _bdh_fallback, _has_prices
    from bloomberg.connection import get_session, get_service

    result = SmileResult(underlying=underlying, expiry=expiry)

    # Déterminer la grille de strikes
    cfg = DATA_UNDERLYING.get(underlying)
    if cfg is None:
        return result

    strikes = generate_strikes(cfg["atm"], cfg["research_zone"], cfg["step"])

    # Construire tous les tickers
    all_tickers: List[str] = []
    strike_map: Dict[str, Tuple[float, str]] = {}  # ticker → (strike, "C"|"P")

    for K in strikes:
        call_t, put_t = build_tickers(underlying, expiry, K)
        all_tickers.extend([call_t, put_t])
        strike_map[call_t] = (K, "C")
        strike_map[put_t] = (K, "P")

    if not all_tickers:
        return result

    # Fetch Bloomberg
    session = get_session()
    service = get_service()

    bdp_raw = _bdp_fetch(session, service, all_tickers, use_overrides=True)

    missing = [t for t in all_tickers if not _has_prices(bdp_raw.get(t, {}))]
    bdh_raw: Dict = {}
    if missing:
        bdh_raw = _bdh_fallback(session, service, missing, lookback_days=10, use_overrides=True)

    # Organiser par strike
    data_by_strike: Dict[float, SmilePoint] = {}
    for K in strikes:
        call_t, put_t = build_tickers(underlying, expiry, K)
        data_by_strike[K] = SmilePoint(strike=K, call_ticker=call_t, put_ticker=put_t)

    for ticker, (K, opt_type) in strike_map.items():
        data = dict(bdp_raw.get(ticker, {}))
        warning = False
        if ticker in bdh_raw:
            data.update(bdh_raw[ticker])
            warning = True

        mid = _extract_mid(data)
        undl = data.get("OPT_UNDL_PX")

        bid_raw = data.get("PX_BID")
        ask_raw = data.get("PX_ASK")
        bid = float(bid_raw) if bid_raw is not None and float(bid_raw) >= 0 else None
        ask = float(ask_raw) if ask_raw is not None and float(ask_raw) > 0 else None

        sp = data_by_strike[K]
        if warning:
            sp.warning = True

        if opt_type == "C":
            sp.call_mid = mid
            sp.call_bid = bid
            sp.call_ask = ask
        else:
            sp.put_mid = mid
            sp.put_bid = bid
            sp.put_ask = ask

        if undl is not None and float(undl) > 0:
            sp.underlying_price = float(undl)

    result.points = [data_by_strike[K] for K in strikes]

    # Forward price = price du sous-jacent le plus fréquent
    undl_prices = [p.underlying_price for p in result.points if p.underlying_price]
    if undl_prices:
        result.forward_price = undl_prices[len(undl_prices) // 2]

    # ── Calcul IV Bachelier depuis les prix mid ──────────────────────────
    from option.bachelier import Bachelier

    F = result.forward_price
    T = 0.25

    if F and F > 0:
        for sp in result.points:
            if sp.call_mid and sp.call_mid > 0:
                iv = Bachelier(F, sp.strike, 0.0, T, True, sp.call_mid).implied_vol()
                sp.call_iv = iv if iv > 0 else None
            else:
                sp.call_iv = None
            if sp.put_mid and sp.put_mid > 0:
                iv = Bachelier(F, sp.strike, 0.0, T, False, sp.put_mid).implied_vol()
                sp.put_iv = iv if iv > 0 else None
            else:
                sp.put_iv = None

    return result