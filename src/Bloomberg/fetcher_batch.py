"""
Bloomberg Batch Fetcher - Optimisé
===================================
Récupère toutes les données d'options en un seul appel Bloomberg par ticker.
Plus efficace que de faire plusieurs appels pour chaque champ.

- Fait UN SEUL appel Bloomberg par ticker
- Récupère TOUS les champs nécessaires d'un coup
- Réduit drastiquement le temps d'import
- Minimise la charge sur l'API Bloomberg
"""

import sys
from pathlib import Path
from typing import Dict, List, Any

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent))

import blpapi
from myproject.bloomberg.connection import BloombergConnection


# Liste complète des champs à récupérer (tous en un coup)
ALL_OPTION_FIELDS = [
    # Prix
    "PX_LAST",
    "PX_BID",
    "PX_ASK",
    "PX_MID",
    # Greeks - tous les formats possibles
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
    # Greeks bid/ask
    "OPT_DELTA_BID",
    "OPT_DELTA_ASK",
    # Volatilité implicite - tous les formats
    "OPT_IMP_VOL",
    "IMP_VOL",
    "IVOL_MID",
    "OPT_IVOL_MID",
    "OPT_IVOL_BID",
    "OPT_IVOL_ASK",
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
    tickers: List[str], use_overrides: bool = True
) -> Dict[str, Dict[str, Any]]:
    """
    Récupère les données pour plusieurs tickers en un seul appel Bloomberg.

    Args:
        tickers: Liste des tickers Bloomberg (ex: ["ERF6C 97.5 Comdty", "ERF6P 97.5 Comdty"])
        use_overrides: Si True, ajoute les overrides pour forcer les Greeks

    Returns:
        Dictionnaire {ticker: {field: value}}

    Example:
        >>> tickers = ["ERF6C 97.5 Comdty", "ERG6C 97.5 Comdty"]
        >>> data = fetch_options_batch(tickers)
        >>> print(data["ERF6C 97.5 Comdty"]["DELTA_MID"])
        0.6234
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
                                    print(f"⚠️  Erreur pour {ticker}: {error_msg}")
                                    continue

                                # Extraire tous les champs
                                if security.hasElement("fieldData"):
                                    field_data = security.getElement("fieldData")

                                    for field in ALL_OPTION_FIELDS:
                                        if field_data.hasElement(field):
                                            try:
                                                value = field_data.getElement(
                                                    field
                                                ).getValue()
                                                results[ticker][field] = value
                                            except:
                                                results[ticker][field] = None
                                        else:
                                            results[ticker][field] = None

                if event.eventType() == blpapi.Event.RESPONSE:
                    break

        return results

    except Exception as e:
        print(f"✗ Erreur lors de la récupération batch: {e}")
        import traceback

        traceback.print_exc()
        return results


def extract_best_values(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrait les meilleures valeurs parmi les différents formats de champs.

    Args:
        data: Dictionnaire avec tous les champs Bloomberg bruts

    Returns:
        Dictionnaire avec les valeurs unifiées
    """
    result = {}

    # Prix (priorité: LAST > MID > moyenne BID/ASK)
    result["premium"] = data.get("PX_MID")
    if not result["premium"] and data.get("PX_BID") and data.get("PX_ASK"):
        result["premium"] = (data["PX_BID"] + data["PX_ASK"]) / 2
    result["premium"] = result["premium"] or 0.0

    result["bid"] = data.get("PX_BID") or result["premium"] * 0.98
    result["ask"] = data.get("PX_ASK") or result["premium"] * 1.02

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
    result["implied_volatility"] = (
        data.get("OPT_IMP_VOL")
        or data.get("IMP_VOL")
        or data.get("IVOL_MID")
        or data.get("OPT_IVOL_MID")
        or 0.15
    )

    # Informations du contrat
    result["strike"] = data.get("OPT_STRIKE_PX") or 0.0
    result["underlying_price"] = data.get("OPT_UNDL_PX") or result["strike"]

    # Volume et Open Interest
    result["volume"] = int(data.get("VOLUME") or data.get("PX_VOLUME") or 0)
    result["open_interest"] = int(data.get("OPEN_INT") or 0)

    return result
