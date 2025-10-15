"""
Bloomberg Option Data Fetcher
==============================
Module pour récupérer les prix et Greeks des options via Bloomberg API.

Auteur: BGC Trading Desk
Date: 2025-10-15
"""

import blpapi
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date
from dataclasses import dataclass
import logging

# Configuration du logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class OptionData:
    """Structure de données pour une option avec prix et Greeks"""
    ticker: str
    underlying: str
    option_type: str  # 'CALL' ou 'PUT'
    strike: float
    expiration: date
    
    # Prix
    bid: Optional[float] = None
    ask: Optional[float] = None
    last: Optional[float] = None
    mid: Optional[float] = None
    
    # Greeks
    delta: Optional[float] = None
    gamma: Optional[float] = None
    vega: Optional[float] = None
    theta: Optional[float] = None
    rho: Optional[float] = None
    
    # Autres données
    implied_volatility: Optional[float] = None
    open_interest: Optional[int] = None
    volume: Optional[int] = None
    
    def __repr__(self):
        return (f"OptionData({self.ticker} | Strike=${self.strike} | "
                f"Last=${self.last} | Delta={self.delta} | IV={self.implied_volatility}%)")


class BloombergOptionFetcher:
    """
    Client Bloomberg pour récupérer les données d'options
    
    Usage:
        fetcher = BloombergOptionFetcher()
        fetcher.connect()
        option_data = fetcher.get_option_data('SPY', 'CALL', 450.0, '2024-12-20')
        fetcher.disconnect()
    """
    
    # Champs Bloomberg pour les options
    OPTION_FIELDS = [
        'PX_BID',              # Prix Bid
        'PX_ASK',              # Prix Ask
        'PX_LAST',             # Dernier prix
        'PX_MID',              # Prix Mid
        'DELTA',               # Delta
        'GAMMA',               # Gamma
        'VEGA',                # Vega
        'THETA',               # Theta
        'RHO',                 # Rho
        'IVOL_MID',            # Volatilité implicite
        'OPEN_INT',            # Open Interest
        'PX_VOLUME',           # Volume
        'OPT_STRIKE_PX',       # Strike Price
        'OPT_EXPIRE_DT',       # Date d'expiration
    ]
    
    def __init__(self, host: str = "localhost", port: int = 8194):
        """
        Initialise le connecteur Bloomberg
        
        Args:
            host: Adresse du serveur Bloomberg (défaut: localhost)
            port: Port du serveur Bloomberg (défaut: 8194)
        """
        self.host = host
        self.port = port
        self.session = None
        self.refdata_service = None
        
    def connect(self) -> bool:
        """
        Établit la connexion avec Bloomberg Terminal
        
        Returns:
            True si connexion réussie, False sinon
        """
        try:
            logger.info(f"🔌 Connexion à Bloomberg sur {self.host}:{self.port}...")
            
            # Configuration de la session
            session_options = blpapi.SessionOptions()
            session_options.setServerHost(self.host)
            session_options.setServerPort(self.port)
            
            # Création de la session
            self.session = blpapi.Session(session_options)
            
            # Démarrage de la session
            if not self.session.start():
                logger.error("❌ Échec du démarrage de la session Bloomberg")
                return False
            
            logger.info("✅ Session Bloomberg démarrée")
            
            # Ouverture du service refdata
            if not self.session.openService("//blp/refdata"):
                logger.error("❌ Échec de l'ouverture du service //blp/refdata")
                self.session.stop()
                return False
            
            self.refdata_service = self.session.getService("//blp/refdata")
            logger.info("✅ Service refdata ouvert")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la connexion: {e}")
            return False
    
    def disconnect(self):
        """Ferme la connexion Bloomberg"""
        if self.session:
            self.session.stop()
            logger.info("🔌 Connexion Bloomberg fermée")
    
    def _build_option_ticker(self, 
                            underlying: str, 
                            option_type: str, 
                            strike: float, 
                            expiration: str) -> str:
        """
        Construit le ticker Bloomberg pour une option
        
        Format: UNDERLYING MM/DD/YY C/P STRIKE Index/Equity
        Exemple: SPY 12/20/24 C450 Index
        
        Args:
            underlying: Symbole du sous-jacent (ex: 'SPY', 'AAPL')
            option_type: 'CALL' ou 'PUT'
            strike: Prix d'exercice
            expiration: Date d'expiration 'YYYY-MM-DD'
        
        Returns:
            Ticker Bloomberg formaté
        """
        # Parser la date
        exp_date = datetime.strptime(expiration, "%Y-%m-%d")
        date_str = exp_date.strftime("%m/%d/%y")
        
        # Type d'option
        opt_char = 'C' if option_type.upper() == 'CALL' else 'P'
        
        # Strike (supprimer .0 si entier)
        strike_str = str(int(strike)) if strike == int(strike) else str(strike)
        
        # Déterminer le suffixe (Index pour les ETF/indices, Equity pour les actions)
        suffix = "Index" if underlying in ['SPX', 'SPY', 'QQQ', 'IWM'] else "Equity"
        
        ticker = f"{underlying} {date_str} {opt_char}{strike_str} {suffix}"
        
        return ticker
    
    def get_option_data(self,
                       underlying: str,
                       option_type: str,
                       strike: float,
                       expiration: str,
                       fields: Optional[List[str]] = None) -> Optional[OptionData]:
        """
        Récupère les données d'une option spécifique
        
        Args:
            underlying: Symbole du sous-jacent (ex: 'SPY', 'AAPL')
            option_type: 'CALL' ou 'PUT'
            strike: Prix d'exercice
            expiration: Date d'expiration 'YYYY-MM-DD'
            fields: Liste des champs à récupérer (défaut: tous les champs)
        
        Returns:
            OptionData ou None si échec
        
        Example:
            >>> fetcher = BloombergOptionFetcher()
            >>> fetcher.connect()
            >>> option = fetcher.get_option_data('SPY', 'CALL', 450.0, '2024-12-20')
            >>> print(f"Delta: {option.delta}")
        """
        if not self.session or not self.refdata_service:
            logger.error("❌ Session Bloomberg non connectée. Appelez connect() d'abord.")
            return None
        
        # Construire le ticker
        ticker = self._build_option_ticker(underlying, option_type, strike, expiration)
        logger.info(f"🔍 Récupération des données pour {ticker}...")
        
        # Champs à récupérer
        if fields is None:
            fields = self.OPTION_FIELDS
        
        try:
            # Créer la requête
            request = self.refdata_service.createRequest("ReferenceDataRequest")
            request.append("securities", ticker)
            
            for field in fields:
                request.append("fields", field)
            
            # Envoyer la requête
            self.session.sendRequest(request)
            
            # Traiter la réponse
            data = {}
            while True:
                event = self.session.nextEvent(500)
                
                if event.eventType() == blpapi.Event.RESPONSE or \
                   event.eventType() == blpapi.Event.PARTIAL_RESPONSE:
                    
                    for msg in event:
                        if msg.hasElement("securityData"):
                            sec_data = msg.getElement("securityData")
                            
                            for i in range(sec_data.numValues()):
                                sec = sec_data.getValueAsElement(i)
                                
                                if sec.hasElement("fieldData"):
                                    field_data = sec.getElement("fieldData")
                                    
                                    for field in fields:
                                        if field_data.hasElement(field):
                                            try:
                                                value = field_data.getElementAsFloat(field)
                                                data[field] = value
                                            except:
                                                try:
                                                    value = field_data.getElementAsInteger(field)
                                                    data[field] = value
                                                except:
                                                    try:
                                                        value = field_data.getElementAsString(field)
                                                        data[field] = value
                                                    except:
                                                        data[field] = None
                
                if event.eventType() == blpapi.Event.RESPONSE:
                    break
            
            # Créer l'objet OptionData
            exp_date = datetime.strptime(expiration, "%Y-%m-%d").date()
            
            option_data = OptionData(
                ticker=ticker,
                underlying=underlying,
                option_type=option_type.upper(),
                strike=strike,
                expiration=exp_date,
                bid=data.get('PX_BID'),
                ask=data.get('PX_ASK'),
                last=data.get('PX_LAST'),
                mid=data.get('PX_MID'),
                delta=data.get('DELTA'),
                gamma=data.get('GAMMA'),
                vega=data.get('VEGA'),
                theta=data.get('THETA'),
                rho=data.get('RHO'),
                implied_volatility=data.get('IVOL_MID'),
                open_interest=data.get('OPEN_INT'),
                volume=data.get('PX_VOLUME')
            )
            
            logger.info(f"✅ Données récupérées: {option_data}")
            return option_data
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_option_chain(self,
                        underlying: str,
                        expiration: str,
                        strikes: Optional[List[float]] = None,
                        option_types: List[str] = ['CALL', 'PUT']) -> List[OptionData]:
        """
        Récupère une chaîne d'options pour plusieurs strikes
        
        Args:
            underlying: Symbole du sous-jacent
            expiration: Date d'expiration 'YYYY-MM-DD'
            strikes: Liste des strikes (défaut: None = tous)
            option_types: Types d'options à récupérer (défaut: ['CALL', 'PUT'])
        
        Returns:
            Liste d'OptionData
        """
        results = []
        
        if strikes is None:
            logger.warning("⚠️ Aucun strike spécifié. Veuillez fournir une liste de strikes.")
            return results
        
        for strike in strikes:
            for opt_type in option_types:
                option = self.get_option_data(underlying, opt_type, strike, expiration)
                if option:
                    results.append(option)
        
        logger.info(f"✅ {len(results)} options récupérées")
        return results
    
    def __enter__(self):
        """Support du context manager"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Support du context manager"""
        self.disconnect()


# ============================================================================
# FONCTIONS HELPER
# ============================================================================

def format_option_table(options: List[OptionData]) -> str:
    """
    Formate une liste d'options en tableau lisible
    
    Args:
        options: Liste d'OptionData
    
    Returns:
        String avec tableau formaté
    """
    if not options:
        return "Aucune donnée"
    
    lines = []
    lines.append("\n" + "="*130)
    lines.append(f"{'Type':<6} {'Strike':<8} {'Bid':<8} {'Ask':<8} {'Last':<8} "
                f"{'Delta':<8} {'Gamma':<8} {'Vega':<8} {'Theta':<8} {'IV%':<8}")
    lines.append("-"*130)
    
    for opt in options:
        lines.append(
            f"{opt.option_type:<6} "
            f"${opt.strike:<7.2f} "
            f"${opt.bid or 0:<7.2f} "
            f"${opt.ask or 0:<7.2f} "
            f"${opt.last or 0:<7.2f} "
            f"{opt.delta or 0:<8.4f} "
            f"{opt.gamma or 0:<8.4f} "
            f"{opt.vega or 0:<8.4f} "
            f"{opt.theta or 0:<8.4f} "
            f"{opt.implied_volatility or 0:<8.2f}"
        )
    
    lines.append("="*130 + "\n")
    return "\n".join(lines)


if __name__ == "__main__":
    print("📊 Module Bloomberg Option Data Fetcher")
    print("Utilisez option_data_fetcher_test.py pour tester le module")
