"""
Bloomberg Simple Fetcher - Style Excel
=======================================
Interface ultra-simple pour récupérer des données Bloomberg,
comme si vous utilisiez =BDP() dans Excel.

Usage:
    from fetcher_v2 import bbg_fetch
    
    # Syntaxe simple
    delta = bbg_fetch("ERZ6C 97.5 Comdty", "OPT_DELTA")
    
    # Ou plusieurs champs
    data = bbg_fetch("ERZ6C 97.5 Comdty", ["OPT_DELTA", "PX_LAST", "OPT_IMP_VOL"])

Auteur: BGC Trading Desk
Date: 2025-10-17
"""

from typing import Union, List, Dict, Any, Optional
from connection import BloombergConnection


def bbg_fetch(
    ticker: str,
    fields: Union[str, List[str]],
    use_overrides: bool = True,
    overrides: Optional[Dict[str, str]] = None
) -> Union[Any, Dict[str, Any]]:
    """
    Récupère des données Bloomberg - Style Excel =BDP()
    
    Args:
        ticker: Le ticker Bloomberg complet (ex: "ERZ6C 97.5 Comdty")
        fields: Un champ ou une liste de champs (ex: "OPT_DELTA" ou ["OPT_DELTA", "PX_LAST"])
        use_overrides: Si True, ajoute les overrides pour forcer le calcul des Greeks
        overrides: Dictionnaire optionnel d'overrides personnalisés
    
    Returns:
        - Si un seul champ: la valeur directement
        - Si plusieurs champs: dictionnaire {field: value}
    
    Exemples:
        >>> delta = bbg_fetch("ERZ6C 97.5 Comdty", "OPT_DELTA")
        >>> print(delta)
        0.6234
        
        >>> data = bbg_fetch("ERZ6C 97.5 Comdty", ["OPT_DELTA", "PX_LAST", "OPT_IMP_VOL"])
        >>> print(data)
        {'OPT_DELTA': 0.6234, 'PX_LAST': 0.5625, 'OPT_IMP_VOL': 15.2}
    
    Raises:
        ConnectionError: Si impossible de se connecter à Bloomberg
        ValueError: Si le ticker ou les champs sont invalides
    """
    # Convertir un seul champ en liste pour uniformiser le traitement
    single_field = isinstance(fields, str)
    if single_field:
        fields = [fields]
    
    try:
        with BloombergConnection() as conn:
            # Créer la requête
            request = conn.create_request("ReferenceDataRequest")
            
            # Ajouter le ticker
            request.append("securities", ticker)
            
            # Ajouter les champs
            for field in fields:
                request.append("fields", field)
            
            # Ajouter les overrides si demandé
            if use_overrides:
                overrides_element = request.getElement("overrides")
                
                # Overrides par défaut pour forcer le calcul des Greeks
                default_overrides = {
                    "PRICING_SOURCE": "BGNE",      # Bloomberg Generic Pricing
                    "REFERENCE_DATE": "TODAY",      # Utiliser aujourd'hui
                }
                
                # Fusionner avec les overrides personnalisés
                final_overrides = {**default_overrides, **(overrides or {})}
                
                # Ajouter chaque override
                for field_id, value in final_overrides.items():
                    override = overrides_element.appendElement()
                    override.setElement("fieldId", field_id)
                    override.setElement("value", str(value))
            
            # Envoyer la requête
            conn.send_request(request)
            
            # Parser la réponse
            results = {}
            
            while True:
                event = conn.session.nextEvent(timeout=5000)
                
                if event.eventType() == conn.names.RESPONSE or \
                   event.eventType() == conn.names.PARTIAL_RESPONSE:
                    
                    for msg in event:
                        if msg.hasElement("securityData"):
                            security_data = msg.getElement("securityData")
                            
                            for i in range(security_data.numValues()):
                                security = security_data.getValueAsElement(i)
                                
                                if security.hasElement("fieldData"):
                                    field_data = security.getElement("fieldData")
                                    
                                    # Extraire tous les champs
                                    for field in fields:
                                        if field_data.hasElement(field):
                                            value = field_data.getElement(field).getValue()
                                            results[field] = value
                                        else:
                                            results[field] = None
                
                if event.eventType() == conn.names.RESPONSE:
                    break
            
            # Retourner la valeur directement si un seul champ
            if single_field:
                return results.get(fields[0])
            
            return results
    
    except Exception as e:
        raise ConnectionError(f"Erreur lors de la récupération des données Bloomberg: {e}")


def bbg_fetch_multi(
    tickers: List[str],
    fields: Union[str, List[str]],
    use_overrides: bool = True
) -> Dict[str, Union[Any, Dict[str, Any]]]:
    """
    Récupère des données pour plusieurs tickers en une seule requête.
    
    Args:
        tickers: Liste de tickers Bloomberg
        fields: Un champ ou une liste de champs
        use_overrides: Si True, ajoute les overrides pour forcer le calcul
    
    Returns:
        Dictionnaire {ticker: valeur} ou {ticker: {field: valeur}}
    
    Exemple:
        >>> data = bbg_fetch_multi(
        ...     ["ERZ6C 97.5 Comdty", "ERZ6P 97.5 Comdty"],
        ...     ["OPT_DELTA", "PX_LAST"]
        ... )
        >>> print(data)
        {
            'ERZ6C 97.5 Comdty': {'OPT_DELTA': 0.6234, 'PX_LAST': 0.5625},
            'ERZ6P 97.5 Comdty': {'OPT_DELTA': -0.3766, 'PX_LAST': 0.0125}
        }
    """
    single_field = isinstance(fields, str)
    if single_field:
        fields = [fields]
    
    try:
        with BloombergConnection() as conn:
            request = conn.create_request("ReferenceDataRequest")
            
            # Ajouter tous les tickers
            for ticker in tickers:
                request.append("securities", ticker)
            
            # Ajouter les champs
            for field in fields:
                request.append("fields", field)
            
            # Ajouter les overrides
            if use_overrides:
                overrides_element = request.getElement("overrides")
                
                override1 = overrides_element.appendElement()
                override1.setElement("fieldId", "PRICING_SOURCE")
                override1.setElement("value", "BGNE")
                
                override2 = overrides_element.appendElement()
                override2.setElement("fieldId", "REFERENCE_DATE")
                override2.setElement("value", "TODAY")
            
            # Envoyer la requête
            conn.send_request(request)
            
            # Parser la réponse
            results = {ticker: {} for ticker in tickers}
            
            while True:
                event = conn.session.nextEvent(timeout=5000)
                
                if event.eventType() == conn.names.RESPONSE or \
                   event.eventType() == conn.names.PARTIAL_RESPONSE:
                    
                    for msg in event:
                        if msg.hasElement("securityData"):
                            security_data = msg.getElement("securityData")
                            
                            for i in range(security_data.numValues()):
                                security = security_data.getValueAsElement(i)
                                
                                # Récupérer le ticker
                                ticker = security.getElementAsString("security")
                                
                                if security.hasElement("fieldData"):
                                    field_data = security.getElement("fieldData")
                                    
                                    # Extraire tous les champs
                                    for field in fields:
                                        if field_data.hasElement(field):
                                            value = field_data.getElement(field).getValue()
                                            results[ticker][field] = value
                                        else:
                                            results[ticker][field] = None
                
                if event.eventType() == conn.names.RESPONSE:
                    break
            
            # Simplifier si un seul champ
            if single_field:
                return {ticker: data.get(fields[0]) for ticker, data in results.items()}
            
            return results
    
    except Exception as e:
        raise ConnectionError(f"Erreur lors de la récupération des données Bloomberg: {e}")


# Alias pour compatibilité style Excel
bdp = bbg_fetch  # Bloomberg Data Point (=BDP dans Excel)


if __name__ == "__main__":
    """
    Tests rapides du fetcher
    """
    print("="*70)
    print("TEST BLOOMBERG FETCHER V2 - Style Excel")
    print("="*70)
    print()
    
    # Test 1: Un seul champ
    print("Test 1: Récupération d'un seul champ")
    print("-"*70)
    try:
        delta = bbg_fetch("ERH6C 97.5 ", "OPT_DELTA")
        print(f"✓ Delta: {delta}")
    except Exception as e:
        print(f"✗ Erreur: {e}")
    print()
    
    # Test 2: Plusieurs champs
    print("Test 2: Récupération de plusieurs champs")
    print("-"*70)
    try:
        data = bbg_fetch("ERH6C 97.5 Comdty", ["OPT_DELTA", "PX_LAST", "OPT_IMP_VOL", "OPT_GAMMA"])
        for field, value in data.items():
            print(f"  {field:20} = {value}")
    except Exception as e:
        print(f"✗ Erreur: {e}")
    print()
    
    # Test 3: Plusieurs tickers
    print("Test 3: Récupération pour plusieurs tickers")
    print("-"*70)
    try:
        tickers = [
            "ERH6C 97.5 ",
            "ERH6C 98.0 ",
            "ERH6P 97.5 "
        ]
        data = bbg_fetch_multi(tickers, ["OPT_DELTA", "PX_LAST"])
        
        for ticker, fields in data.items():
            print(f"\n{ticker}:")
            for field, value in fields.items():
                print(f"  {field:20} = {value}")
    except Exception as e:
        print(f"✗ Erreur: {e}")
    print()
    
    # Test 4: Alias bdp
    print("Test 4: Test de l'alias bdp() (style Excel)")
    print("-"*70)
    try:
        price = bdp("ERH6C 97.5", "PX_LAST")
        print(f"✓ Prix (via bdp): {price}")
    except Exception as e:
        print(f"✗ Erreur: {e}")
    
    print()
    print("="*70)
    print("TESTS TERMINÉS")
    print("="*70)