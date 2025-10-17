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
from ticker_builder import build_option_ticker
from models import OptionData


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
        """Établit la connexion Bloomberg (délégué à BloombergConnection)."""
        return self.connection.connect()
    
    def disconnect(self):
        """Ferme la connexion Bloomberg (délégué à BloombergConnection)."""
        return self.connection.disconnect()
    
    def is_connected(self) -> bool:
        """Vérifie si la connexion est active (délégué à BloombergConnection)."""
        return self.connection.is_connected()
    
    # Context Manager - délégué à BloombergConnection
    def __enter__(self):
        """Permet d'utiliser 'with BloombergOptionFetcher() as fetcher:'"""
        self.connection.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ferme automatiquement la connexion à la sortie du bloc 'with'."""
        return self.connection.__exit__(exc_type, exc_val, exc_tb)
    
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
        print(f"[DEBUG fetcher._send_request] Création requête pour ticker={ticker}")
        print(f"[DEBUG fetcher._send_request] Champs demandés: {fields[:5]}... ({len(fields)} total)")
        
        # Créer la requête en utilisant la méthode de connection
        request = self.connection.create_request("ReferenceDataRequest")
        request.append("securities", ticker)
        
        for field in fields:
            request.append("fields", field)
        
        print(f"[DEBUG fetcher._send_request] Envoi de la requête...")
        
        # Envoyer la requête en utilisant la méthode de connection
        self.connection.send_request(request)
        
        # Parser la réponse
        result = {}
        print(f"[DEBUG fetcher._send_request] En attente de la réponse...")
        
        while True:
            # Utiliser la méthode next_event de connection
            event = self.connection.next_event(500)  # timeout 500ms
            
            for msg in event:
                if msg.hasElement("securityData"):
                    sec_data = msg.getElement("securityData")
                    sec_data_element = sec_data.getValueAsElement(0)
                    
                    # Vérifier les erreurs de sécurité
                    if sec_data_element.hasElement("securityError"):
                        error = sec_data_element.getElement("securityError")
                        error_msg = error.getElementAsString("message") if error.hasElement("message") else "Unknown error"
                        print(f"[DEBUG fetcher._send_request] ✗ Erreur Bloomberg pour {ticker}: {error_msg}")
                        return {}
                    
                    if sec_data_element.hasElement("fieldData"):
                        field_data = sec_data_element.getElement("fieldData")
                        
                        for field in fields:
                            if field_data.hasElement(field):
                                result[field] = self._parse_field(field_data.getElement(field))
            
            if event.eventType() == blpapi.Event.RESPONSE:
                break
        
        print(f"[DEBUG fetcher._send_request] ✓ Réponse reçue: {len(result)} champs")
        return result
    
    def get_option_data(
        self,
        underlying: str,
        expiry_month : Literal['F' , 'G', 'H', 'K', 'M', 'N', 'Q', 'U', 'V', 'X', 'Z' ],
        expiry_year : int,
        option_type: Literal['C', 'P'],
        strike: float,
    ) -> Optional[OptionData]:
        
        """
        Récupère toutes les données d'une option spécifique.
        """

        # Construire le ticker
        print(f"[DEBUG fetcher] Construction du ticker: underlying={underlying}, expiry_month={expiry_month}, expiry_year=202{expiry_year} type={option_type}, strike={strike}")
        ticker = build_option_ticker(underlying, expiry_month, expiry_year, option_type, strike, suffix="Comdty")
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
        option = OptionData(
            ticker=ticker,
            underlying=underlying.upper(),
            option_type=option_type.upper() if len(option_type) > 1 else ('CALL' if option_type == 'C' else 'PUT'),
            strike=strike,
            expiry_month=expiry_month,
            expiry_year=expiry_year,
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
    
    def list_expiries(self, underlying: str) -> List[date]:
        """
        Liste toutes les dates d'expiration disponibles pour un sous-jacent.
        """
    
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
        expiry_year: int,
        is_euribor: bool = False
    ) -> List[OptionData]:
        """
        Récupère toutes les options pour un strike donné sur plusieurs expiries.
                
        Args:
            underlying: Symbole du sous-jacent
            strike: Prix d'exercice fixe
            option_type: "C"/"CALL" ou "P"/"PUT"
            expiry_year: Année maximale à scanner (format 1 chiffre: 5 pour 2025)
            is_euribor: True pour EURIBOR
        
        Returns:
            Liste des OptionData pour chaque expiry
        """
        
        # Récupérer les expiries si non fournies
        year = date.today().year % 10
        list_year = []

        # Liste typée des mois Bloomberg
        list_month: List[Literal['F', 'G', 'H', 'K', 'M', 'N', 'Q', 'U', 'V', 'X', 'Z']] = [
            'F', 'G', 'H', 'K', 'M', 'N', 'Q', 'U', 'V', 'X', 'Z'
        ]

        while year <= expiry_year:
            list_year.append(year)
            year += 1
            
        # Récupérer chaque option
        options = []
        for year in list_year:
            for month in list_month:
                try:
                    opt = self.get_option_data(underlying, month, year, option_type, strike)
                    if opt:
                        options.append(opt)
                except Exception as e:
                    # Continuer si une option échoue
                    print(f"Erreur pour {underlying}{month}{year} {option_type} {strike}: {e}")
                    continue
        
        return options
    
    def get_options_by_range_strike(
        self,
        underlying: str,
        strike_center: float,
        option_type: Literal["P", "C"],
        expiry_month: Literal['F', 'G', 'H', 'K', 'M', 'N', 'Q', 'U', 'V', 'X', 'Z'],
        expiry_year: int,
        strike_range: float = 30.0,
        strike_step: float = 0.25,
        is_euribor: bool = False
    ) -> List[OptionData]:
        """
        Récupère toutes les options dans un intervalle de strikes autour d'un strike central.
        
        Args:
            underlying: Symbole du sous-jacent (ex: "ER" pour EURIBOR)
            strike_center: Strike central (ex: 97.50)
            option_type: "C" pour Call ou "P" pour Put
            expiry_month: Mois d'expiration (ex: 'H' pour Mars)
            expiry_year: Année d'expiration sur 1 chiffre (ex: 5 pour 2025)
            strike_range: Intervalle autour du strike central (défaut: ±30)
            strike_step: Pas entre chaque strike (défaut: 0.25 pour EURIBOR)
            is_euribor: True pour EURIBOR
        
        Returns:
            Liste des OptionData pour tous les strikes dans l'intervalle

        """
        
        # Calculer les bornes de l'intervalle
        strike_min = strike_center - strike_range
        strike_max = strike_center + strike_range
        
        print(f"[DEBUG] Recherche options {underlying} {option_type} pour {expiry_month}{expiry_year}")
        print(f"[DEBUG] Intervalle strikes: {strike_min} à {strike_max} (pas: {strike_step})")
        
        # Générer la liste de tous les strikes à tester
        strikes = []
        current_strike = strike_min
        while current_strike <= strike_max:
            strikes.append(round(current_strike, 2))  # Arrondir à 2 décimales
            current_strike += strike_step
        
        print(f"[DEBUG] Nombre de strikes à tester: {len(strikes)}")
        
        # Récupérer chaque option
        options = []
        for strike in strikes:
            try:
                opt = self.get_option_data(
                    underlying=underlying,
                    expiry_month=expiry_month,
                    expiry_year=expiry_year,
                    option_type=option_type,
                    strike=strike
                )
                if opt:
                    options.append(opt)
                    print(f"[DEBUG] ✓ Trouvé: {opt.ticker}")
            except Exception as e:
                # Continuer silencieusement si un strike n'existe pas
                continue
        
        print(f"[DEBUG] ✓ Total options trouvées: {len(options)}/{len(strikes)}")
        return options