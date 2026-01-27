"""
Bloomberg Batch Fetcher - Version Simplifiée
=============================================
Récupère les données d'options depuis Bloomberg.
"""

import blpapi
from typing import Any, Optional, Tuple
from myproject.bloomberg.connection import get_session, get_service


# Champs à récupérer
OPTION_FIELDS = [
    "PX_BID", "PX_ASK", "PX_MID", "PX_LAST",
    "OPT_DELTA", "OPT_GAMMA", "OPT_VEGA", "OPT_THETA", "OPT_RHO",
    "OPT_IMP_VOL",
    "OPT_STRIKE_PX", "OPT_UNDL_PX", "OPT_PUT_CALL",
    "VOLUME", "OPEN_INT",
]


def fetch_options_batch(tickers: list[str], use_overrides: bool = True, underlyings: Optional[str] = None) -> Tuple[dict[str, dict[str, Any]], Optional[dict]]:
    """
    Récupère les données pour plusieurs tickers Bloomberg.

    Args:
        tickers: Liste des tickers Bloomberg (ex: ["SPX 12/20/24 C5000 Equity"])
        use_overrides: Si True, ajoute les overrides pour forcer les Greeks

    Returns:
        Dictionnaire {ticker: {field: value}}
    """
    results = {ticker: {} for ticker in tickers}
    underlying_ref = {}

    try:
        session = get_session()
        service = get_service()

        # Créer la requête
        request = service.createRequest("ReferenceDataRequest")
        securities = blpapi.name.Name("securities")
        fields = blpapi.name.Name("fields")
        overrid = blpapi.name.Name("overrides")
        fieldId = blpapi.name.Name("fieldId")
        value = blpapi.name.Name("value")
        underlying= blpapi.name.Name("underlying")

        if underlyings is not None:
            request.append(underlying, underlyings)

        for ticker in tickers:
            request.append(securities, ticker)

        for field in OPTION_FIELDS:
            request.append(fields, field)
        


        # Ajouter les overrides si demandé
        if use_overrides:
            overrides = request.getElement(overrid)
            override1 = overrides.appendElement()
            override1.setElement(fieldId, "PRICING_SOURCE")
            override1.setElement(value, "BGNE")

        # Envoyer
        session.sendRequest(request)

        # Lire la réponse
        while True:
            event = session.nextEvent(5000)

            if event.eventType() in [blpapi.event.Event.RESPONSE, blpapi.event.Event.PARTIAL_RESPONSE]:
                for msg in event:
                    if msg.hasElement("securityData"):
                        security_data = msg.getElement("securityData")                            

                        for i in range(security_data.numValues()):
                            security = security_data.getValueAsElement(i)
                            ticker = security.getElementAsString("security")

                            if security.hasElement("securityError"):
                                print(f"⚠️ Erreur pour {ticker}")
                                continue
                            if security.hasElement("underlying"):
                                underlying_ref= security.getElement("underlying")
                            if security.hasElement("fieldData"):
                                field_data = security.getElement("fieldData")
                                ticker_data = {}

                                for field in OPTION_FIELDS:
                                    if field_data.hasElement(field):
                                        try:
                                            ticker_data[field] = field_data.getElement(field).getValue()
                                        except:
                                            ticker_data[field] = None
                                    else:
                                        ticker_data[field] = None

                                results[ticker] = ticker_data

            if event.eventType() == blpapi.event.Event.RESPONSE:
                break
        return results, underlying_ref

    except Exception as e:
        print(f"✗ Erreur fetch: {e}")
        return results, None


def extract_best_values(data: dict[str, Any]) -> dict[str, Any]:
    """
    Extrait les valeurs utiles des données Bloomberg brutes.
    """
    bid = data.get("PX_BID") or 0.0
    ask = data.get("PX_ASK") or 0.0
    mid = data.get("PX_MID") or 0.0

    if mid > 0:
        premium = mid
    elif bid > 0 and ask > 0:
        premium = (bid + ask) / 2
    elif ask > 0:
        premium = ask / 2
    else:
        premium = None

    return {
        "premium": premium,
        "bid": bid if bid > 0 else 0.0,
        "ask": ask if ask > 0 else 0.0,
        "delta": data.get("OPT_DELTA") or 0.0,
        "gamma": data.get("OPT_GAMMA") or 0.0,
        "vega": data.get("OPT_VEGA") or 0.0,
        "theta": data.get("OPT_THETA") or 0.0,
        "rho": data.get("OPT_RHO") or 0.0,
        "implied_volatility": data.get("OPT_IMP_VOL") or 0.15,
        "strike": data.get("OPT_STRIKE_PX") or 0.0,
        "underlying_price": data.get("OPT_UNDL_PX") or 0.0,
        "volume": int(data.get("VOLUME") or 0),
        "open_interest": int(data.get("OPEN_INT") or 0),
    }