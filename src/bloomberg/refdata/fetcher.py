"""
Bloomberg Batch Fetcher
========================
Récupère les données d'options via ReferenceDataRequest (BDP) pour les prix
et les Greeks. Si un ticker n'a pas de prix, on utilise HistoricalDataRequest
(BDH) avec un lookback de quelques jours en fallback.
"""
from __future__ import annotations

import blpapi
from blpapi.name import Name
from datetime import date, timedelta
from typing import Any, List, Optional, Tuple
from bloomberg.config import OPTION_FIELDS
from bloomberg.connection import get_session, get_service
from app.data_types import FutureData

# Champs prix utilisés pour le BDH fallback
_BDH_FIELDS = ["PX_BID", "PX_ASK", "PX_MID", "PX_LAST"]
# Set pour vérifier rapidement si un ticker a des prix
_PRICE_FIELD_SET = set(_BDH_FIELDS)


def _safe_get_value(element, field: str) -> Any:
    """Extrait une valeur d'un élément Bloomberg de façon sécurisée."""
    if not element.hasElement(field):
        return None
    try:
        return element.getElement(field).getValue()
    except Exception:
        return None


def _extract_underlying_price(data: dict[str, Any]) -> Optional[float]:
    """Extrait le prix du sous-jacent depuis un dict de champs."""
    for field in ("PX_LAST", "PX_MID"):
        price = data.get(field)
        if price is not None:
            return float(price)
    return None


def _compute_mid(bid: float, ask: float, mid: float) -> Optional[float]:
    if mid > 0:
        return mid
    if bid > 0 and ask > 0:
        return (bid + ask) / 2
    if ask > 0:
        return ask / 2
    return None


def _pick_last_valid_row(field_data, fields: list[str]) -> dict[str, Any]:
    """Parcourt les lignes historiques et retourne la dernière avec des prix."""
    best: dict[str, Any] = {}
    for i in range(field_data.numValues()):
        row = field_data.getValueAsElement(i)
        row_data = {f: _safe_get_value(row, f) for f in fields}
        if any(row_data.get(pf) is not None for pf in _PRICE_FIELD_SET):
            best = row_data
    return best


def _has_prices(data: dict[str, Any]) -> bool:
    """Vérifie qu'un ticker a au moins un prix bid ou ask."""
    return bool(data.get("PX_BID") or data.get("PX_ASK") or data.get("PX_MID"))


def _bdp_fetch(
    session, service,
    all_securities: list[str],
    use_overrides: bool,
) -> dict[str, dict[str, Any]]:
    """ReferenceDataRequest (BDP) — tous les champs y compris Greeks."""
    raw: dict[str, dict[str, Any]] = {}

    request = service.createRequest("ReferenceDataRequest")
    securities = Name("securities")
    fields = Name("fields")
    overrides = Name("overrides")
    fieldId = Name("fieldId")
    value = Name("value")

    for sec in all_securities:
        request.append(securities, sec)
    for field in OPTION_FIELDS:
        request.append(fields, field)

    if use_overrides:
        ov = request.getElement(overrides)
        ov1 = ov.appendElement()
        ov1.setElement(fieldId, "PRICING_SOURCE")
        ov1.setElement(value, "BGNE")

    session.sendRequest(request)

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
                        print(f"⚠️ Erreur BDP pour {ticker}: {err_msg}")
                        continue

                    if not sec.hasElement("fieldData"):
                        continue
                    fd = sec.getElement("fieldData")
                    raw[ticker] = {f: _safe_get_value(fd, f) for f in OPTION_FIELDS}

        if event.eventType() == blpapi.event.Event.RESPONSE:
            break

    return raw


def _bdh_fallback(
    session, service,
    missing_tickers: list[str],
    lookback_days: int,
    use_overrides: bool,
) -> dict[str, dict[str, Any]]:
    """HistoricalDataRequest (BDH) fallback — uniquement les prix."""
    raw: dict[str, dict[str, Any]] = {}
    if not missing_tickers:
        return raw

    request = service.createRequest("HistoricalDataRequest")
    securities = Name("securities")
    fields = Name("fields")
    startDate = Name("startDate")
    endDate = Name("endDate")
    periodicitySelection = Name("periodicitySelection")
    overrides = Name("overrides")
    fieldId = Name("fieldId")
    value = Name("value")

    for sec in missing_tickers:
        request.append(securities, sec)
    for field in _BDH_FIELDS:
        request.append(fields, field)

    end_dt = date.today()
    start_dt = end_dt - timedelta(days=lookback_days)
    request.set(startDate, start_dt.strftime("%Y%m%d"))
    request.set(endDate, end_dt.strftime("%Y%m%d"))
    request.set(periodicitySelection, "DAILY")

    if use_overrides:
        ov = request.getElement(overrides)
        ov1 = ov.appendElement()
        ov1.setElement(fieldId, "PRICING_SOURCE")
        ov1.setElement(value, "BGNE")

    session.sendRequest(request)

    while True:
        event = session.nextEvent(10_000)
        if event.eventType() in (blpapi.event.Event.RESPONSE,
                                 blpapi.event.Event.PARTIAL_RESPONSE):
            for msg in event:
                if not msg.hasElement("securityData"):
                    continue
                sec_data = msg.getElement("securityData")
                ticker = sec_data.getElementAsString("security")

                if sec_data.hasElement("securityError"):
                    continue
                if not sec_data.hasElement("fieldData"):
                    continue
                fd = sec_data.getElement("fieldData")
                best = _pick_last_valid_row(fd, _BDH_FIELDS)
                if best:
                    raw[ticker] = best

        if event.eventType() == blpapi.event.Event.RESPONSE:
            break

    return raw


def fetch_options_batch(
    tickers: list[str],
    use_overrides: bool = True,
    underlyings: str = "SFR",
    lookback_days: int = 3,
) -> Tuple[dict[str, dict[str, Any]], FutureData, List[str]]:
    """Récupère les données pour une liste de tickers Bloomberg.

    Returns:
        (résultats par ticker, FutureData, liste de warnings)
    """
    results: dict[str, dict[str, Any]] = {t: {} for t in tickers}

    try:
        session = get_session()
        service = get_service()

        # Liste complète des securities pour le BDP
        all_securities = list(tickers)
        if underlyings is not None:
            all_securities = [underlyings] + all_securities

        # ── Étape 1 : BDP (prix + Greeks) ──────────────────────────────
        bdp_raw = _bdp_fetch(session, service, all_securities, use_overrides)

        underlying_price: Optional[float] = None
        last_tradable_date: Optional[str] = None

        # Extraire le sous-jacent
        if underlyings is not None and underlyings in bdp_raw:
            price = _extract_underlying_price(bdp_raw[underlyings])
            if price is not None:
                underlying_price = price

        # Remplir les résultats depuis BDP
        for t in tickers:
            data = bdp_raw.get(t, {})
            if data:
                results[t] = data
                if last_tradable_date is None:
                    dt = data.get("LAST_TRADEABLE_DT")
                    last_tradable_date = str(dt) if dt is not None else None

        # ── Étape 2 : BDH fallback pour tickers sans prix ─────────────
        # missing = [t for t in tickers if not _has_prices(results.get(t, {}))]
        # if missing:
        #     bdh_raw = _bdh_fallback(session, service, missing, lookback_days, use_overrides)
        #     # Aussi le sous-jacent si pas de prix
        #     if underlyings is not None and underlying_price is None:
        #         undl_bdh = _bdh_fallback(session, service, [underlyings], lookback_days, use_overrides)
        #         if underlyings in undl_bdh:
        #             price = _extract_underlying_price(undl_bdh[underlyings])
        #             if price is not None:
        #                 underlying_price = price

        #     for t in missing:
        #         if t in bdh_raw:
        #             # Merger : on conserve les Greeks du BDP, on remplace les prix
        #             merged = dict(results.get(t, {}))
        #             merged.update(bdh_raw[t])
        #             results[t] = merged

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
            if ask and bid is None and ask > 0.005:
                wide_spread.append(t)
                results[t]["_warning"] = True
            if ask and bid and (ask - bid) > 0.008:
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
