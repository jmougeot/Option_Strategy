"""
Bloomberg Batch Fetcher - Version Simplifiée
=============================================
Récupère les données d'options depuis Bloomberg.
"""

import blpapi
from typing import Any, List, Optional, Tuple
from myproject.bloomberg.connection import get_session, get_service
from myproject.app.data_types import FutureData


# Champs à récupérer (PX_LAST utilisé aussi pour le sous-jacent)
OPTION_FIELDS = [
    "PX_BID", "PX_ASK", "PX_MID", "PX_LAST",
    "OPT_DELTA", "OPT_GAMMA", "OPT_VEGA", "OPT_THETA", "OPT_RHO",
    "OPT_IMP_VOL", "IVOL_MID", "IVOL_BID", "IVOL_ASK",
    "OPT_STRIKE_PX", "OPT_UNDL_PX", "OPT_PUT_CALL",
    "VOLUME", "OPEN_INT",
    "LAST_TRADEABLE_DT", "OPT_EXPIRE_DT",
]


def _safe_get_value(element, field: str) -> Any:
    """Extrait une valeur d'un élément Bloomberg de façon sécurisée."""
    if not element.hasElement(field):
        return None
    try:
        return element.getElement(field).getValue()
    except Exception:
        return None


def _extract_underlying_price(field_data) -> Optional[float]:
    """Extrait le prix du sous-jacent depuis PX_LAST ou PX_MID."""
    for field in ["PX_LAST", "PX_MID"]:
        price = _safe_get_value(field_data, field)
        if price is not None:
            return price
    return None


def _compute_mid(bid: float, ask: float, mid: float) -> Optional[float]:
    """Calcule le premium à partir de bid/ask/mid."""
    if mid > 0:
        return mid
    if bid > 0 and ask > 0:
        return (bid + ask) / 2
    if ask > 0:
        return ask / 2
    return None

def fetch_options_batch(tickers: list[str], use_overrides: bool = True, underlyings: Optional[str] = None) -> Tuple[dict[str, dict[str, Any]], FutureData, List[str]]:
    """
    Récupère les données pour plusieurs tickers Bloomberg.

    Args:
        tickers: Liste des tickers Bloomberg (ex: ["SPX 12/20/24 C5000 Equity"])
        use_overrides: Si True, ajoute les overrides pour forcer les Greeks
        underlyings: Ticker du sous-jacent pour récupérer son prix (optionnel)

    Returns:
        Tuple (résultats options, FutureData avec prix sous-jacent et date, warnings)
    """
    results = {ticker: {} for ticker in tickers}

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

        # Ajouter le sous-jacent en premier si fourni
        if underlyings is not None:
            request.append(securities, underlyings)

        for ticker in tickers:
            request.append(securities, ticker)

        for field in OPTION_FIELDS:
            request.append(fields, field)
        
        if use_overrides:
            overrides = request.getElement(overrid)
            override1 = overrides.appendElement()
            override1.setElement(fieldId, "PRICING_SOURCE")
            override1.setElement(value, "BGNE")

        # Envoyer
        session.sendRequest(request)
        underlying_price : Optional[float] = None
        last_tradable_date : Optional[str] = None
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
                                err = security.getElement("securityError")
                                err_msg = err.getElementAsString("message") if err.hasElement("message") else "Unknown"
                                print(f"⚠️ Erreur pour {ticker}: {err_msg}")
                                continue
                            
                            if security.hasElement("fieldData"):
                                field_data = security.getElement("fieldData")
                                
                                # Si c'est le sous-jacent, extraire son prix
                                if underlyings is not None and ticker == underlyings:
                                    price = _extract_underlying_price(field_data)
                                    if price is not None:
                                        underlying_price = price
                                else:
                                    # Extraire tous les champs pour les options
                                    results[ticker] = {field: _safe_get_value(field_data, field) for field in OPTION_FIELDS}
                                    
                                    # Extraire LAST_TRADEABLE_DT du premier ticker (une seule fois)
                                    if last_tradable_date is None:
                                        dt = _safe_get_value(field_data, "LAST_TRADEABLE_DT")
                                        if dt is not None:
                                            last_tradable_date = str(dt)
                                        else :
                                            dt = "Unknown"

            if event.eventType() == blpapi.event.Event.RESPONSE:
                break

        # Vérifier les options sans bid/ask et afficher un warning Streamlit
        missing_both = []
        wide_spread = []
        for ticker, data in results.items():
            if not data:
                continue
            bid = data.get("PX_BID")
            ask = data.get("PX_ASK")
            if bid is None and ask is None:
                missing_both.append(ticker)
                results[ticker]["_warning"] = True
            if ask and bid is None and ask > 0.1:
                wide_spread.append(ticker)
                results[ticker]["_warning"] = True
            if ask and bid:
                spread = ask - bid
                if spread > 0.08:
                    wide_spread.append(f"{ticker} (spread={spread:.4f})")
                    results[ticker]["_warning"] = True

        warnings: List[str] = []
        if missing_both:
            warnings.append(f"Sans Bid ni Ask ({len(missing_both)}): " + ", ".join(missing_both))
        if wide_spread:
            warnings.append(f"Spread Bid-Ask > 8 ticks ({len(wide_spread)}): " + ", ".join(wide_spread))

        return results, FutureData(underlying_price, last_tradable_date), warnings

    except Exception as e:
        print(f"✗ Erreur fetch: {e}")
        import traceback
        traceback.print_exc()
        return results, FutureData(None, None), []


def extract_best_values(data: dict[str, Any]) -> dict[str, Any]:
    """
    Extrait les valeurs utiles des données Bloomberg brutes.
    """
    bid = data.get("PX_BID") or 0.0
    ask = data.get("PX_ASK") or 0.0
    mid = data.get("PX_MID") or 0.0
    iv_bid = data.get("IVOL_BID") or 0.0
    iv_ask = data.get("IVOL_MID") or 0.0
    iv_mid = data.get("IVOL_MID") or 0.0

    return {
        "premium": _compute_mid(bid, ask, mid),
        "implied_volatility": _compute_mid(iv_bid, iv_ask, iv_mid),
        "bid": bid if bid > 0 else 0.0,
        "ask": ask if ask > 0 else 0.0,
        "delta": data.get("OPT_DELTA") or 0.0,
        "gamma": data.get("OPT_GAMMA") or 0.0,
        "vega": data.get("OPT_VEGA") or 0.0,
        "theta": data.get("OPT_THETA") or 0.0,
        "strike": data.get("OPT_STRIKE_PX") or 0.0,
        "underlying_price": data.get("OPT_UNDL_PX") or 0.0,
    }