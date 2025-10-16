"""
Bloomberg Data Fetcher
======================
Client simplifié pour récupérer les données d'options depuis Bloomberg.

Ce module orchestre les autres composants (connection, ticker_builder, models)
pour fournir une interface simple d'utilisation.

Auteur: BGC Trading Desk
Date: 2025-10-16
"""

from datetime import date, datetime
from typing import List, Optional, Dict, Any, Literal
import blpapi
from connection import BloombergConnection
from ticker_builder import build_option_ticker, parse_euribor_expiry_code
from models import OptionData, EuriborOptionData


# Champs Bloomberg standards pour les options
DEFAULT_OPTION_FIELDS = [
    # Prix de marché
    'PX_BID',           # Prix bid (acheteur)
    'PX_ASK',           # Prix ask (vendeur)
    'PX_LAST',          # Dernier prix traité
    'PX_MID',           # Prix mid (bid+ask)/2
    'PX_VOLUME',        # Volume du jour
    'OPEN_INT',         # Intérêt ouvert (nombre de contrats ouverts)
    
    # Greeks (sensibilités)
    'DELTA',            # Sensibilité au prix du sous-jacent
    'GAMMA',            # Sensibilité du delta
    'VEGA',             # Sensibilité à la volatilité
    'THETA',            # Déclin temporel (perte de valeur/jour)
    'RHO',              # Sensibilité aux taux d'intérêt
    
    # Volatilité
    'IVOL_MID',         # Volatilité implicite mid
    
    # Informations contractuelles
    'OPT_STRIKE_PX',    # Prix d'exercice (strike)
    'OPT_EXPIRE_DT',    # Date d'expiration
    'OPT_PUT_CALL',     # Type: 'CALL' ou 'PUT'
    'OPT_UNDL_TICKER',  # Ticker du sous-jacent
]


class BloombergOptionFetcher:
    """
    Client principal pour récupérer les données d'options Bloomberg.
    
    Utilisation recommandée avec context manager:
        with BloombergOptionFetcher() as fetcher:
            data = fetcher.get_option_data("AAPL", date(2024, 12, 20), "C", 150.0)
            print(data.delta, data.implied_volatility)
    
    Fonctionnalités:
    - Récupération de données pour une option spécifique
    - Liste des dates d'expiration disponibles
    - Scan de toutes les options pour un strike donné
    - Support complet EURIBOR (futures de taux)
    """
    
    def __init__(self, fields: Optional[List[str]] = None):
        """
        Initialise le fetcher avec les champs Bloomberg désirés.
        
        Args:
            fields: Liste des champs Bloomberg à récupérer
                   (utilise DEFAULT_OPTION_FIELDS si None)
        """
        self.connection = BloombergConnection()
        self.fields = fields or DEFAULT_OPTION_FIELDS
    
    def connect(self):
        """Établit la connexion Bloomberg."""
        print("[DEBUG fetcher] Tentative de connexion Bloomberg...")
        try:
            self.connection.connect()
            print("[DEBUG fetcher] ✓ Connexion Bloomberg établie")
        except Exception as e:
            print(f"[DEBUG fetcher] ✗ Erreur de connexion: {type(e).__name__}: {e}")
            raise
    
    def disconnect(self):
        """Ferme la connexion Bloomberg."""
        print("[DEBUG fetcher] Fermeture de la connexion Bloomberg...")
        self.connection.disconnect()
        print("[DEBUG fetcher] ✓ Connexion fermée")
    
    # Context Manager
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False
    
    def _parse_field(self, field_data: blpapi.Element) -> Any:
        """
        Parse un champ Bloomberg en type Python approprié.
        
        Args:
            field_data: Élément blpapi contenant la donnée
        
        Returns:
            Valeur Python (float, str, date, etc.)
        """
        if not field_data or field_data.isNull():
            return None
        
        # Convertir selon le type
        if field_data.datatype() == blpapi.DataType.FLOAT64:
            return field_data.getValueAsFloat()
        elif field_data.datatype() == blpapi.DataType.INT32:
            return field_data.getValueAsInteger()
        elif field_data.datatype() == blpapi.DataType.STRING:
            return field_data.getValueAsString()
        elif field_data.datatype() == blpapi.DataType.DATE:
            dt = field_data.getValueAsDatetime()
            # Handle different types that blpapi may return (datetime, date, or unexpectedly time)
            if isinstance(dt, datetime):
                return dt.date()
            if isinstance(dt, date):
                return dt
            # Fallback: try to parse a string representation like "YYYY-MM-DD"
            try:
                return datetime.strptime(str(dt), "%Y-%m-%d").date()
            except Exception:
                return None
        else:
            return str(field_data.getValue())
    
    def _send_request(self, ticker: str, fields: List[str]) -> Dict[str, Any]:
        """
        Envoie une requête ReferenceDataRequest à Bloomberg.
        
        Args:
            ticker: Ticker Bloomberg complet
            fields: Liste des champs à récupérer
        
        Returns:
            Dictionnaire {field_name: value}
        """
        # Créer la requête
        request = self.connection.service.createRequest("ReferenceDataRequest")
        request.append("securities", ticker)
        
        for field in fields:
            request.append("fields", field)
        
        # Envoyer et attendre la réponse
        self.connection.session.sendRequest(request)
        
        # Parser la réponse
        result = {}
        while True:
            event = self.connection.session.nextEvent(500)  # timeout 500ms
            
            for msg in event:
                if msg.hasElement("securityData"):
                    sec_data = msg.getElement("securityData")
                    sec_data_element = sec_data.getValueAsElement(0)
                    
                    if sec_data_element.hasElement("fieldData"):
                        field_data = sec_data_element.getElement("fieldData")
                        
                        for field in fields:
                            if field_data.hasElement(field):
                                result[field] = self._parse_field(field_data.getElement(field))
            
            if event.eventType() == blpapi.Event.RESPONSE:
                break
        
        return result
    
    def get_option_data(
        self,
        underlying: str,
        expiry: date,
        option_type: Literal['C', 'P', 'CALL', 'PUT'],
        strike: float,
        is_euribor: bool = False
    ) -> Optional[OptionData]:
        """
        Récupère toutes les données d'une option spécifique.
        
        Args:
            underlying: Symbole du sous-jacent (ex: "AAPL", "ER")
            expiry: Date d'expiration
            option_type: "C"/"CALL" ou "P"/"PUT"
            strike: Prix d'exercice
            is_euribor: True pour options EURIBOR (auto-détecté si False)
        
        Exemple:
            >>> with BloombergOptionFetcher() as fetcher:
            ...     opt = fetcher.get_option_data("AAPL", date(2024, 12, 20), "C", 150.0)
            ...     print(f"Delta: {opt.delta}, IV: {opt.implied_volatility}%")
        """
        # Construire le ticker
        print(f"[DEBUG fetcher] Construction du ticker: underlying={underlying}, expiry={expiry}, type={option_type}, strike={strike}, is_euribor={is_euribor}")
        ticker = build_option_ticker(underlying, expiry, option_type, strike, is_euribor)
        print(f"[DEBUG fetcher] Ticker construit: {ticker}")
        
        # Récupérer les données
        print(f"[DEBUG fetcher] Envoi de la requête Bloomberg pour {ticker}")
        print(f"[DEBUG fetcher] Champs demandés: {len(self.fields)} champs")
        data = self._send_request(ticker, self.fields)
        print(f"[DEBUG fetcher] Réponse Bloomberg reçue: {len(data)} champs retournés")
        
        if not data:
            print(f"[DEBUG fetcher] ✗ Aucune donnée retournée pour {ticker}")
            return None
        
        print(f"[DEBUG fetcher] Données reçues: {list(data.keys())}")
        
        # Créer l'objet approprié
        if is_euribor or underlying.upper() in ['ER', 'EURIBOR']:
            print(f"[DEBUG fetcher] Création d'un objet EuriborOptionData")
            option = EuriborOptionData(
                ticker=ticker,
                underlying=underlying.upper(),
                option_type=option_type.upper() if len(option_type) > 1 else ('CALL' if option_type == 'C' else 'PUT'),
                strike=strike,
                expiry=expiry,
                
                bid=data.get('PX_BID'),
                ask=data.get('PX_ASK'),
                last=data.get('PX_LAST'),
                mid=data.get('PX_MID'),
                volume=data.get('PX_VOLUME'),
                open_interest=data.get('OPEN_INT'),
                
                delta=data.get('DELTA'),
                gamma=data.get('GAMMA'),
                vega=data.get('VEGA'),
                theta=data.get('THETA'),
                rho=data.get('RHO'),
                
                implied_volatility=data.get('IVOL_MID'),
            )
        else:
            option = OptionData(
                ticker=ticker,
                underlying=underlying.upper(),
                option_type=option_type.upper() if len(option_type) > 1 else ('CALL' if option_type == 'C' else 'PUT'),
                strike=strike,
                expiry=expiry,
                
                bid=data.get('PX_BID'),
                ask=data.get('PX_ASK'),
                last=data.get('PX_LAST'),
                mid=data.get('PX_MID'),
                volume=data.get('PX_VOLUME'),
                open_interest=data.get('OPEN_INT'),
                
                delta=data.get('DELTA'),
                gamma=data.get('GAMMA'),
                vega=data.get('VEGA'),
                theta=data.get('THETA'),
                rho=data.get('RHO'),
                
                implied_volatility=data.get('IVOL_MID'),
            )
        
        return option
    
    def list_expiries(self, underlying: str, is_euribor: bool = False) -> List[date]:
        """
        Liste toutes les dates d'expiration disponibles pour un sous-jacent.
        
        Args:
            underlying: Symbole du sous-jacent (ex: "AAPL", "ER")
            is_euribor: True pour EURIBOR (format différent)
        
        Returns:
            Liste des dates d'expiration triées
        
        Exemple:
            >>> with BloombergOptionFetcher() as fetcher:
            ...     expiries = fetcher.list_expiries("AAPL")
            ...     print(f"Prochaine expiration: {expiries[0]}")
        """
        # Pour EURIBOR, on liste les contrats trimestriels standard
        if is_euribor or underlying.upper() in ['ER', 'EURIBOR']:
            # Requête sur le ticker EURIBOR générique
            ticker = "ER1 Comdty"
            data = self._send_request(ticker, ['OPT_EXPIRE_DT_LIST'])
            
            if 'OPT_EXPIRE_DT_LIST' in data and data['OPT_EXPIRE_DT_LIST']:
                # Parser la liste de dates
                expiry_list = data['OPT_EXPIRE_DT_LIST']
                if isinstance(expiry_list, list):
                    return sorted([d for d in expiry_list if isinstance(d, date)])
                
        else:
            # Pour actions/indices, utiliser le ticker standard
            ticker = f"{underlying.upper()} US Equity" if ' ' not in underlying else underlying
            data = self._send_request(ticker, ['OPT_EXPIRE_DT_LIST'])
            
            if 'OPT_EXPIRE_DT_LIST' in data and data['OPT_EXPIRE_DT_LIST']:
                expiry_list = data['OPT_EXPIRE_DT_LIST']
                if isinstance(expiry_list, list):
                    return sorted([d for d in expiry_list if isinstance(d, date)])
        
        return []
    
    def get_options_by_strike(
        self,
        underlying: str,
        strike: float,
        option_type: Literal["P", "C"],
        expiries: Optional[List[date]] = None,
        is_euribor: bool = False
    ) -> List[OptionData]:
        """
        Récupère toutes les options pour un strike donné sur plusieurs expiries.
        
        Utile pour analyser la structure de terme (term structure) de la volatilité.
        
        Args:
            underlying: Symbole du sous-jacent
            strike: Prix d'exercice fixe
            option_type: "C"/"CALL" ou "P"/"PUT"
            expiries: Liste des expiries (liste auto si None)
            is_euribor: True pour EURIBOR
        
        Returns:
            Liste des OptionData pour chaque expiry
        
        Exemple:
            >>> with BloombergOptionFetcher() as fetcher:
            ...     # Toutes les calls à 150 sur AAPL
            ...     chain = fetcher.get_options_by_strike("AAPL", 150.0, "C")
            ...     for opt in chain:
            ...         print(f"{opt.expiry}: IV={opt.implied_volatility}%")
        """
        # Récupérer les expiries si non fournies
        if expiries is None:
            expiries = self.list_expiries(underlying, is_euribor)
        
        # Récupérer chaque option
        options = []
        for expiry in expiries:
            try:
                opt = self.get_option_data(underlying, expiry, option_type, strike, is_euribor)
                if opt:
                    options.append(opt)
            except Exception as e:
                # Continuer si une option échoue
                print(f"Erreur pour {underlying} {expiry} {option_type}{strike}: {e}")
                continue
        
        return options


if __name__ == "__main__":
    # Test rapide
    print("=== Test Bloomberg Option Fetcher ===")
    print("Assurez-vous que Bloomberg Terminal est lancé.\n")
    
    try:
        with BloombergOptionFetcher() as fetcher:
            # Test EURIBOR
            print("Test EURIBOR option:")
            euribor_opt = fetcher.get_option_data("ER", date(2025, 3, 15), "C", 97.50, is_euribor=True)
            if euribor_opt:
                print(f"  Ticker: {euribor_opt.ticker}")
                print(f"  Last: {euribor_opt.last}")
                print(f"  Delta: {euribor_opt.delta}")
                print(f"  IV: {euribor_opt.implied_volatility}%")
                if isinstance(euribor_opt, EuriborOptionData):
                    print(f"  Implied Rate: {euribor_opt.implied_rate:.2f}%")
            else:
                print("  Option non trouvée (vérifier que la date d'expiry existe)")
            
            # Test liste des expiries
            print("\nListe des expiries EURIBOR:")
            expiries = fetcher.list_expiries("ER", is_euribor=True)
            for exp in expiries[:5]:  # Afficher les 5 premières
                print(f"  - {exp}")
                
    except Exception as e:
        print(f"Erreur: {e}")
        print("Vérifiez que Bloomberg Terminal est lancé et connecté.")
