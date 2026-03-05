"""
Service Bloomberg pour la gestion des subscriptions en temps réel.
Utilise les signaux Qt pour communiquer avec l'interface graphique.
"""
import re
import blpapi
from PyQt6.QtCore import QObject, pyqtSignal as Signal, QThread, QMutex, QMutexLocker
from typing import Optional


DEFAULT_FIELDS = ["LAST_PRICE", "BID", "ASK"]
DEFAULT_SERVICE = "//blp/mktdata"


def normalize_ticker_bloomberg(ticker: str) -> str:
    """
    Normalise un ticker pour Bloomberg.
    - Majuscules
    - Corrige les fautes de frappe courantes
    - Supprime les espaces superflus
    """
    if not ticker:
        return ""
    
    ticker = ticker.strip().upper()
    
    # Corriger les variantes de "COMDTY"
    ticker = re.sub(r'\bCOMDITY\b', 'COMDTY', ticker, flags=re.IGNORECASE)
    ticker = re.sub(r'\bCOMODITY\b', 'COMDTY', ticker, flags=re.IGNORECASE)
    ticker = re.sub(r'\bCOMDTY\b', 'COMDTY', ticker, flags=re.IGNORECASE)
    
    # Normaliser les espaces multiples
    ticker = re.sub(r'\s+', ' ', ticker)
    
    return ticker


class BloombergEventHandler:
    """Handler d'événements Bloomberg - doit être callable"""
    
    def __init__(self, worker: 'BloombergWorker'):
        self.worker = worker
    
    def __call__(self, event, session):
        """Appelé par blpapi quand un événement arrive"""
        try:
            self.worker._process_event(event)
        except Exception as e:
            print(f"[Bloomberg] Erreur dans event handler: {e}")


class BloombergWorker(QThread):
    """Worker thread pour gérer la session Bloomberg"""
    
    price_updated = Signal(str, float, float, float)  # ticker, last, bid, ask
    subscription_started = Signal(str)  # ticker
    subscription_failed = Signal(str, str)  # ticker, error
    connection_status = Signal(bool, str)  # connected, message
    
    # Signal interne pour déclencher le traitement des subscriptions
    _process_subscriptions = Signal()
    
    def __init__(self, host: str = "localhost", port: int = 8194):
        super().__init__()
        self.host = host
        self.port = port
        self.session: Optional['blpapi.Session'] = None # type: ignore
        self.subscriptions: dict[str, 'blpapi.CorrelationId'] = {} # type: ignore
        self.is_running = False
        self.mutex = QMutex()
        self._pending_subscriptions: list[str] = []
        self._pending_unsubscriptions: list[str] = []
        
        # Connecter le signal interne
        self._process_subscriptions.connect(self._on_process_subscriptions_requested)
    
    def run(self):
        """Boucle principale du thread Bloomberg"""
        
        try:
            print("[Bloomberg] Configuration de la session...")
            # Configuration de la session
            session_options = blpapi.SessionOptions() # type: ignore
            session_options.setServerHost(self.host)
            session_options.setServerPort(self.port)
            session_options.setDefaultSubscriptionService(DEFAULT_SERVICE)
            
            # Créer la session avec un event handler
            print("[Bloomberg] Création de la session...")
            handler = BloombergEventHandler(self)
            self.session = blpapi.Session(session_options, handler) # type: ignore
            
            print("[Bloomberg] Démarrage de la session...")
            if not self.session.start(): # type: ignore
                self.connection_status.emit(False, "Impossible de démarrer la session Bloomberg")
                return
            
            print("[Bloomberg] Ouverture du service...")
            if not self.session.openService(DEFAULT_SERVICE):  # type: ignore
                self.connection_status.emit(False, f"Impossible d'ouvrir {DEFAULT_SERVICE}")
                return
            
            self.is_running = True
            print("[Bloomberg] Connecté!")
            self.connection_status.emit(True, "Connecté à Bloomberg")
            
            # Traiter les subscriptions initiales
            self._process_pending_operations()
            
            # La boucle principale - les événements Bloomberg sont traités via le handler (callback)
            # Les nouvelles subscriptions sont traitées via le signal _process_subscriptions
            while self.is_running:
                # Petit sleep pour éviter de consommer 100% CPU
                # Les subscriptions sont traitées immédiatement via le slot
                self.msleep(10)
            
            print("[Bloomberg] Arrêt du worker")
            
        except Exception as e:
            import traceback
            print(f"[Bloomberg] ERREUR: {e}")
            traceback.print_exc()
            self.connection_status.emit(False, f"Erreur Bloomberg: {str(e)}")
        finally:
            if self.session:
                try:
                    self.session.stop()
                except:
                    pass
    
    def _on_process_subscriptions_requested(self):
        """Slot appelé quand de nouvelles subscriptions sont demandées"""
        if self.is_running and self.session:
            self._process_pending_operations()
    
    def _process_pending_operations(self):
        """Traite les subscriptions/unsubscriptions en attente"""
        with QMutexLocker(self.mutex):
            # Nouvelles subscriptions
            if self._pending_subscriptions:
                sub_list = blpapi.SubscriptionList()  # type: ignore
                for ticker in self._pending_subscriptions:
                    corr_id = blpapi.CorrelationId(ticker)  # type: ignore
                    # Ajouter avec options pour recevoir les prix plus rapidement
                    sub_list.add(ticker, DEFAULT_FIELDS, [], corr_id)
                    self.subscriptions[ticker] = corr_id
                    print(f"[Bloomberg] Subscribing to: {ticker}")
                
                self.session.subscribe(sub_list)  # type: ignore
                print(f"[Bloomberg] Subscribed to {len(self._pending_subscriptions)} tickers")
                self._pending_subscriptions.clear()
            
            # Unsubscriptions
            if self._pending_unsubscriptions:
                unsub_list = blpapi.SubscriptionList()  # type: ignore
                for ticker in self._pending_unsubscriptions:
                    if ticker in self.subscriptions:
                        unsub_list.add(ticker, DEFAULT_FIELDS, [], self.subscriptions[ticker])
                        del self.subscriptions[ticker]
                
                self.session.unsubscribe(unsub_list)  # type: ignore
                self._pending_unsubscriptions.clear()
    
    def _process_event(self, event):
        """Traite un événement Bloomberg"""
        if event.eventType() == blpapi.Event.SUBSCRIPTION_DATA:  # type: ignore
            for msg in event:
                ticker = msg.correlationId().value()
                
                last_price = None
                bid = None
                ask = None
                
                if msg.hasElement("LAST_PRICE"):
                    try:
                        last_price = msg.getElementAsFloat("LAST_PRICE")
                    except:
                        pass
                
                if msg.hasElement("BID"):
                    try:
                        bid = msg.getElementAsFloat("BID")
                    except:
                        pass
                
                if msg.hasElement("ASK"):
                    try:
                        ask = msg.getElementAsFloat("ASK")
                    except:
                        pass
                
                # Émettre seulement si on a au moins une valeur
                if last_price is not None or bid is not None or ask is not None:
                    print(f"[Bloomberg] Price update for {ticker}: last={last_price}, bid={bid}, ask={ask}")
                    self.price_updated.emit(
                        ticker,
                        last_price if last_price is not None else -1.0,  # -1 = pas de valeur
                        bid if bid is not None else -1.0,
                        ask if ask is not None else -1.0
                    )
        
        elif event.eventType() == blpapi.Event.SUBSCRIPTION_STATUS:  # type: ignore
            for msg in event:
                ticker = msg.correlationId().value()
                if msg.messageType() == blpapi.Names.SUBSCRIPTION_STARTED:  # type: ignore
                    self.subscription_started.emit(ticker)
                elif msg.messageType() == blpapi.Names.SUBSCRIPTION_FAILURE:  # type: ignore
                    self.subscription_failed.emit(ticker, str(msg))
    
    def subscribe(self, ticker: str):
        """Ajoute une subscription (thread-safe)"""
        with QMutexLocker(self.mutex):
            if ticker not in self.subscriptions and ticker not in self._pending_subscriptions:
                self._pending_subscriptions.append(ticker)
        # Émettre le signal pour traiter immédiatement (hors du mutex)
        self._process_subscriptions.emit()
    
    def unsubscribe(self, ticker: str):
        """Supprime une subscription (thread-safe)"""
        with QMutexLocker(self.mutex):
            if ticker in self.subscriptions or ticker in self._pending_subscriptions:
                self._pending_unsubscriptions.append(ticker)
                if ticker in self._pending_subscriptions:
                    self._pending_subscriptions.remove(ticker)
        # Émettre le signal pour traiter immédiatement (hors du mutex)
        self._process_subscriptions.emit()
    
    def stop(self):
        """Arrête le worker"""
        self.is_running = False
        # Attendre max 2 secondes pour que le thread se termine
        if not self.wait(2000):
            self.terminate()  # Forcer l'arrêt si timeout
            self.wait(500)


class BloombergService(QObject):
    """
    Service principal pour interagir avec Bloomberg.
    Gère les subscriptions et émet des signaux pour les mises à jour de prix.
    """
    
    # Signaux
    price_updated = Signal(str, float, float, float)  # ticker, last, bid, ask
    subscription_started = Signal(str)
    subscription_failed = Signal(str, str)
    connection_status = Signal(bool, str)
    
    def __init__(self, host: str = "localhost", port: int = 8194):
        super().__init__()
        self.worker: Optional[BloombergWorker] = None
        self.host = host
        self.port = port
        self._active_subscriptions: set[str] = set()
    
    def start(self):
        """Démarre le service Bloomberg"""
        if self.worker and self.worker.isRunning():
            return
        
        self.worker = BloombergWorker(self.host, self.port)
        
        # Connecter les signaux
        self.worker.price_updated.connect(self._on_price_updated)
        self.worker.subscription_started.connect(self._on_subscription_started)
        self.worker.subscription_failed.connect(self._on_subscription_failed)
        self.worker.connection_status.connect(self._on_connection_status)
        
        self.worker.start()
    
    def stop(self):
        """Arrête le service Bloomberg"""
        if self.worker:
            self.worker.stop()
            self.worker = None
        self._active_subscriptions.clear()
    
    def subscribe(self, ticker: str):
        """Subscribe à un ticker"""
        ticker = normalize_ticker_bloomberg(ticker)
        if not ticker or ticker in self._active_subscriptions:
            return
        
        self._active_subscriptions.add(ticker)
        if self.worker:
            self.worker.subscribe(ticker)
    
    def unsubscribe(self, ticker: str):
        """Unsubscribe d'un ticker"""
        ticker = normalize_ticker_bloomberg(ticker)
        if ticker not in self._active_subscriptions:
            return
        
        self._active_subscriptions.discard(ticker)
        if self.worker:
            self.worker.unsubscribe(ticker)
    
    def subscribe_multiple(self, tickers: list[str]):
        """Subscribe à plusieurs tickers"""
        for ticker in tickers:
            self.subscribe(ticker)
    
    def unsubscribe_all(self):
        """Unsubscribe de tous les tickers"""
        for ticker in list(self._active_subscriptions):
            self.unsubscribe(ticker)
    
    def _on_price_updated(self, ticker: str, last: float, bid: float, ask: float):
        """Relaye le signal de mise à jour de prix"""
        self.price_updated.emit(ticker, last, bid, ask)
    
    def _on_subscription_started(self, ticker: str):
        """Relaye le signal de subscription réussie"""
        self.subscription_started.emit(ticker)
    
    def _on_subscription_failed(self, ticker: str, error: str):
        """Relaye le signal d'erreur de subscription"""
        self._active_subscriptions.discard(ticker)
        self.subscription_failed.emit(ticker, error)
    
    def _on_connection_status(self, connected: bool, message: str):
        """Relaye le signal de status de connexion"""
        self.connection_status.emit(connected, message)
    
    @property
    def is_connected(self) -> bool:
        """Retourne True si le service est connecté"""
        return self.worker is not None and self.worker.isRunning()
    
    @property
    def active_subscriptions(self) -> set[str]:
        """Retourne les subscriptions actives"""
        return self._active_subscriptions.copy()
