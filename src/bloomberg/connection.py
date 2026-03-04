"""
Bloomberg Connection - Version Simplifiée
==========================================
Connexion au Bloomberg Terminal API (blpapi).
Supporte les modes synchrone et asynchrone.
"""

import blpapi
from blpapi.session import Session
from blpapi.sessionoptions import SessionOptions
from blpapi.event import Event
from blpapi.name import Name
from blpapi.subscriptionlist import SubscriptionList
from dataclasses import dataclass
from typing import Optional, Callable


@dataclass
class BloombergConfig:
    """Configuration de connexion Bloomberg."""
    host: str = "localhost"
    port: int = 8194


# Configuration globale
config = BloombergConfig()

# Session et service globaux (mode synchrone)
_session: Optional[Session] = None
_service: Optional[blpapi.service.Service] = None


# =============================================================================
# MODE SYNCHRONE (pour ReferenceDataRequest)
# =============================================================================

def get_session() -> Session:
    """
    Retourne la session Bloomberg synchrone (la crée si nécessaire).
    """
    global _session
    
    if _session is None:
        opts = SessionOptions()
        opts.setServerHost(config.host)
        opts.setServerPort(config.port)
        opts.setAutoRestartOnDisconnection(True)
        opts.setNumStartAttempts(3)
        
        _session = Session(opts)
        
        if not _session.start():
            _session = None
            raise ConnectionError(
                f"Impossible de démarrer la session Bloomberg sur {config.host}:{config.port}"
            )
    
    return _session


def get_service(service_name: str = "//blp/refdata") -> blpapi.service.Service:
    """
    Retourne le service Bloomberg (l'ouvre si nécessaire).
    """
    global _service
    
    session = get_session()
    
    if _service is None:
        if not session.openService(service_name):
            raise ConnectionError(f"Impossible d'ouvrir le service {service_name}")
        _service = session.getService(service_name)
    
    return _service


def close_session():
    """Ferme la session Bloomberg."""
    global _session, _service
    
    if _session:
        _session.stop()
        _session = None
        _service = None


def is_connected() -> bool:
    """Vérifie si la connexion est active."""
    return _session is not None


# =============================================================================
# MODE ASYNCHRONE (pour Market Data / Subscriptions)
# =============================================================================

def default_event_handler(event: Event, session: Session):
    """Handler d'événements par défaut."""
    for msg in event:
        cid = msg.correlationId().value() if msg.correlationId() else None
        et = event.eventType()
        
        if et == Event.SUBSCRIPTION_DATA:
            print(f"[DATA] cid={cid} {msg.topicName()}")
            if msg.hasElement("LAST_PRICE"):
                last = msg.getElementAsFloat64("LAST_PRICE")
                print(f"  LAST_PRICE={last}")
                
        elif et == Event.SUBSCRIPTION_STATUS:
            print(f"[SUB_STATUS] {msg.messageType()} cid={cid}")
            
        elif et == Event.SESSION_STATUS:
            print(f"[SESSION] {msg.messageType()}")
            if msg.messageType() in [Name("SessionTerminated"), Name("SessionStartupFailure")]:
                if session:
                    session.stop()


def create_async_session(
    event_handler: Optional[Callable[[Event, Session], None]] = None
) -> Session:
    """
    Crée une session Bloomberg asynchrone avec un event handler.
    
    Args:
        event_handler: Fonction callback (event, session) -> None
    
    Returns:
        Session Bloomberg asynchrone
    """
    opts = SessionOptions()
    opts.setServerHost(config.host)
    opts.setServerPort(config.port)
    
    handler = event_handler or default_event_handler
    session = Session(opts, eventHandler=handler)
    
    if not session.startAsync():
        raise ConnectionError("Impossible de démarrer la session async")
    
    return session


def subscribe_market_data(
    session: Session,
    tickers: list[str],
    fields: str = "BID,ASK,LAST_PRICE"
) -> SubscriptionList:
    """
    Souscrit aux données de marché pour une liste de tickers.
    
    Args:
        session: Session Bloomberg async
        tickers: Liste des tickers (ex: ["IBM US Equity", "MSFT US Equity"])
        fields: Champs à souscrire (séparés par virgules)
    
    Returns:
        SubscriptionList
    """
    subs = SubscriptionList()
    for i, ticker in enumerate(tickers, start=1):
        subs.add(ticker, fields)
    
    session.subscribe(subs)
    return subs


# =============================================================================
# CONTEXT MANAGER (compatibilité avec l'ancien code)
# =============================================================================

class BloombergConnection:
    """Context manager pour connexion Bloomberg."""
    
    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        if host:
            config.host = host
        if port:
            config.port = port
        self.session = None
        self.service = None
    
    def connect(self):
        self.session = get_session()
        self.service = get_service()
        return True
    
    def disconnect(self):
        pass  # On garde la session ouverte pour réutilisation
    
    def is_connected(self) -> bool:
        return is_connected()
    
    def create_request(self, request_type: str = "ReferenceDataRequest"):
        return get_service().createRequest(request_type)
    
    def send_request(self, request):
        get_session().sendRequest(request)
    
    def next_event(self, timeout_ms: int = 500):
        return get_session().nextEvent(timeout_ms)
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False

