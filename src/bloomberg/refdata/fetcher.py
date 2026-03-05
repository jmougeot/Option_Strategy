"""
Bloomberg Batch Fetcher
========================
Récupère les données d'options en une seule requête ReferenceDataRequest.
Utilise la session synchrone de bloomberg.connection.
"""
from __future__ import annotations

import blpapi
from typing import Any, List, Optional, Tuple

from bloomberg.config import OPTION_FIELDS
from bloomberg.connection import get_session, get_service
from app.data_types import FutureData


def _safe_get_value(element, field: str) -> Any:
    """Extrait une valeur d'un élément Bloomberg de façon sécurisée."""
    if not element.hasElement(field):
        return None
    try:
        return element.getElement(field).getValue()
    except Exception:
        return None


def _extract_underlying_price(field_data) -> Optional[float]:
    for field in ("PX_LAST", "PX_MID"):
        price = _safe_get_value(field_data, field)
        if price is not None:
            return price
    return None


def _compute_mid(bid: float, ask: float, mid: float) -> Optional[float]:
    if mid > 0:
        return mid
    if bid > 0 and ask > 0:
        return (bid + ask) / 2
    if ask > 0:
        return ask / 2
    return None


def fetch_options_batch(
    tickers: list[str],
    use_overrides: bool = True,
    underlyings: Optional[str] = None,
) -> Tuple[dict[str, dict[str, Any]], FutureData, List[str]]:
    """Récupère les données pour une liste de tickers Bloomberg.

    Returns:
        (résultats par ticker, FutureData, liste de warnings)
    """
    results: dict[str, dict[str, Any]] = {t: {} for t in tickers}

    try:
        session = get_session()
        service = get_service()

        request = service.createRequest("ReferenceDataRequest")
        securities = blpapi.name.Name("securities")
        fields_nm  = blpapi.name.Name("fields")
        overrid    = blpapi.name.Name("overrides")
        fieldId    = blpapi.name.Name("fieldId")
        value      = blpapi.name.Name("value")

        if underlyings is not None:
            request.append(securities, underlyings)
        for ticker in tickers:
            request.append(securities, ticker)
        for field in OPTION_FIELDS:
            request.append(fields_nm, field)

        if use_overrides:
            ov  = request.getElement(overrid)
            ov1 = ov.appendElement()
            ov1.setElement(fieldId, "PRICING_SOURCE")
            ov1.setElement(value, "BGNE")

        session.sendRequest(request)

        underlying_price: Optional[float] = None
        last_tradable_date: Optional[str] = None

        while True:
            event = session.nextEvent(5000)
            if event.eventType() in (blpapi.event.Event.RESPONSE,
                                     blpapi.event.Event.PARTIAL_RESPONSE):
                for msg in event:
                    if not msg.hasElement("securityData"):
                        continue
                    sec_data = msg.getElement("securityData")
                    for i in range(sec_data.numValues()):
                        sec = sec_data.getValueAsElement(i)
                        ticker = sec.getElementAsString("security")

                        if sec.hasElement("securityError"):
                            err = sec.getElement("securityError")
                            err_msg = err.getElementAsString("message") if err.hasElement("message") else "Unknown"
                            print(f"⚠️ Erreur pour {ticker}: {err_msg}")
                            continue

                        if not sec.hasElement("fieldData"):
                            continue
                        fd = sec.getElement("fieldData")

                        if underlyings is not None and ticker == underlyings:
                            price = _extract_underlying_price(fd)
                            if price is not None:
                                underlying_price = price
                        else:
                            results[ticker] = {f: _safe_get_value(fd, f) for f in OPTION_FIELDS}
                            if last_tradable_date is None:
                                dt = _safe_get_value(fd, "LAST_TRADEABLE_DT")
                                last_tradable_date = str(dt) if dt is not None else None

            if event.eventType() == blpapi.event.Event.RESPONSE:
                break

        # Quality warnings
        missing_both: List[str] = []
        wide_spread:  List[str] = []
        for t, data in results.items():
            if not data:
                results[t] = {"_warning": True}
                missing_both.append(t)
                continue
            bid = data.get("PX_BID")
            ask = data.get("PX_ASK")
            if bid is None and ask is None:
                missing_both.append(t)
                results[t]["_warning"] = True
            if ask and bid is None and ask > 0.08:
                wide_spread.append(t)
                results[t]["_warning"] = True
            if ask and bid and (ask - bid) > 0.08:
                wide_spread.append(f"{t} (spread={ask - bid:.4f})")
                results[t]["_warning"] = True

        warnings: List[str] = []
        if missing_both:
            warnings.append(f"Sans Bid ni Ask ({len(missing_both)}): " + ", ".join(missing_both))
        if wide_spread:
            warnings.append(f"Spread > 8 ticks ({len(wide_spread)}): " + ", ".join(wide_spread))

        return results, FutureData(underlying_price, last_tradable_date), warnings

    except Exception as e:
        import traceback
        print(f"✗ Erreur fetch: {e}")
        traceback.print_exc()
        return results, FutureData(None, None), []


def extract_best_values(data: dict[str, Any]) -> dict[str, Any]:
    """Extrait et normalise les valeurs utiles depuis les données Bloomberg brutes."""
    bid    = data.get("PX_BID")  or 0.0
    ask    = data.get("PX_ASK")  or 0.0
    mid    = data.get("PX_MID")  or 0.0
    iv_bid = data.get("IVOL_BID") or 0.0
    iv_ask = data.get("IVOL_ASK") or 0.0
    iv_mid = data.get("IVOL_MID") or 0.0
    return {
        "premium":           _compute_mid(bid, ask, mid),
        "implied_volatility": _compute_mid(iv_bid, iv_ask, iv_mid),
        "bid":               bid if bid > 0 else 0.0,
        "ask":               ask if ask > 0 else 0.0,
        "delta":             data.get("OPT_DELTA")    or 0.0,
        "gamma":             data.get("OPT_GAMMA")    or 0.0,
        "vega":              data.get("OPT_VEGA")     or 0.0,
        "theta":             data.get("OPT_THETA")    or 0.0,
        "strike":            data.get("OPT_STRIKE_PX") or 0.0,
        "underlying_price":  data.get("OPT_UNDL_PX")  or 0.0,
    }
