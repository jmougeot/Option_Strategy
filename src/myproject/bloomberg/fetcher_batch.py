"""
Bloomberg Batch Fetcher
=======================
Récupère toutes les données d'options en un seul appel Bloomberg par ticker.

- Fait UN SEUL appel Bloomberg par ticker
- Récupère TOUS les champs nécessaires d'un coup
- Minimise la charge sur l'API Bloomberg
"""

from typing import Any

import blpapi

from myproject.bloomberg.connection import BloombergConnection


# Liste des champs à récupérer (optimisée - sans doublons)
ALL_OPTION_FIELDS = [
    # Prix
    "LAST_PRICE",
    "PX_LAST",
    "PX_BID",
    "PX_ASK",
    "PX_MID",
    "PREV_SES_LAST_PRICE",
    "ADJUSTED_PREV_LAST_PRICE",
    # Greeks
    "DELTA_MID",
    "OPT_DELTA",
    "GAMMA_MID",
    "OPT_GAMMA",
    "VEGA_MID",
    "OPT_VEGA",
    "THETA_MID",
    "OPT_THETA",
    "RHO_MID",
    "OPT_RHO",
    # Volatilité implicite
    "OPT_IMP_VOL",
    "IMP_VOL",
    "IVOL_MID",
    "OPT_IVOL_MID",
    # Informations du contrat
    "OPT_STRIKE_PX",
    "OPT_UNDL_PX",
    "OPT_PUT_CALL",
    # Volume et Open Interest
    "VOLUME",
    "PX_VOLUME",
    "OPEN_INT",
]


def fetch_options_batch(
    tickers: list[str], use_overrides: bool = True
) -> dict[str, dict[str, Any]]:
    """
    Récupère les données pour plusieurs tickers en un seul appel Bloomberg.

    Args:
        tickers: Liste des tickers Bloomberg
        use_overrides: Si True, ajoute les overrides pour forcer les Greeks

    Returns:
        Dictionnaire {ticker: {field: value}}
    """
    results = {ticker: {} for ticker in tickers}

    try:
        with BloombergConnection() as conn:
            # Créer la requête
            request = conn.create_request("ReferenceDataRequest")

            # Ajouter tous les tickers
            for ticker in tickers:
                request.append("securities", ticker)

            # Ajouter TOUS les champs en un coup
            for field in ALL_OPTION_FIELDS:
                request.append("fields", field)

            # Ajouter les overrides pour forcer le calcul des Greeks
            if use_overrides:
                overrides_element = request.getElement("overrides")

                # Override 1: Forcer le pricing model
                override1 = overrides_element.appendElement()
                override1.setElement("fieldId", "PRICING_SOURCE")
                override1.setElement("value", "BGNE")

                # Override 2: Date de référence
                override2 = overrides_element.appendElement()
                override2.setElement("fieldId", "REFERENCE_DATE")
                override2.setElement("value", "TODAY")

            # Envoyer la requête
            conn.send_request(request)

            # Parser la réponse
            while True:
                event = conn.next_event(timeout_ms=5000)

                if (
                    event.eventType() == blpapi.Event.RESPONSE
                    or event.eventType() == blpapi.Event.PARTIAL_RESPONSE
                ):

                    for msg in event:
                        if msg.hasElement("securityData"):
                            security_data = msg.getElement("securityData")

                            for i in range(security_data.numValues()):
                                security = security_data.getValueAsElement(i)

                                # Récupérer le ticker
                                ticker = security.getElementAsString("security")

                                # Vérifier les erreurs
                                if security.hasElement("securityError"):
                                    error = security.getElement("securityError")
                                    error_msg = (
                                        error.getElementAsString("message")
                                        if error.hasElement("message")
                                        else "Unknown error"
                                    )
                                    print(f"⚠️ Erreur pour {ticker}: {error_msg}")
                                    continue

                                # Extraire tous les champs
                                if security.hasElement("fieldData"):
                                    field_data = security.getElement("fieldData")

                                    # Construire le dictionnaire de résultats
                                    ticker_data = {}
                                    for field in ALL_OPTION_FIELDS:
                                        if field_data.hasElement(field):
                                            try:
                                                value = field_data.getElement(
                                                    field
                                                ).getValue()
                                                ticker_data[field] = value
                                            except Exception:
                                                ticker_data[field] = None
                                        else:
                                            ticker_data[field] = None

                                    # Stocker dans results
                                    results[ticker] = ticker_data

                if event.eventType() == blpapi.Event.RESPONSE:
                    break

        return results

    except Exception as e:
        print(f"✗ Erreur lors de la récupération batch: {e}")
        import traceback

        traceback.print_exc()
        return results


def extract_best_values(data: dict[str, Any]) -> dict[str, Any]:
    """
    Extrait les meilleures valeurs parmi les différents formats de champs.

    Args:
        data: Dictionnaire avec tous les champs Bloomberg bruts

    Returns:
        Dictionnaire avec les valeurs unifiées
    """
    result: dict[str, Any] = {}

    # Prix (cascade de fallbacks)
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
        premium = 0.0

    result["premium"] = premium
    result["bid"] = bid if bid > 0 else 0.0
    result["ask"] = ask if ask > 0 else 0.0

    # Greeks (priorité: _MID > format court > OPT_)
    result["delta"] = (
        data.get("DELTA_MID") or data.get("DELTA") or data.get("OPT_DELTA") or 0.0
    )

    result["gamma"] = (
        data.get("GAMMA_MID") or data.get("GAMMA") or data.get("OPT_GAMMA") or 0.0
    )

    result["vega"] = (
        data.get("VEGA_MID") or data.get("VEGA") or data.get("OPT_VEGA") or 0.0
    )

    result["theta"] = (
        data.get("THETA_MID") or data.get("THETA") or data.get("OPT_THETA") or 0.0
    )

    result["rho"] = data.get("RHO_MID") or data.get("RHO") or data.get("OPT_RHO") or 0.0

    # Volatilité implicite
    iv_value = (
        data.get("OPT_IMP_VOL")
        or data.get("IMP_VOL")
        or data.get("IVOL_MID")
        or data.get("OPT_IVOL_MID")
    )
    result["implied_volatility"] = iv_value or 0.15

    # Informations du contrat
    result["strike"] = data.get("OPT_STRIKE_PX") or 0.0
    result["underlying_price"] = data.get("OPT_UNDL_PX") or result["strike"]

    # Volume et Open Interest
    result["volume"] = int(data.get("VOLUME") or data.get("PX_VOLUME") or 0)
    result["open_interest"] = int(data.get("OPEN_INT") or 0)

    return result
