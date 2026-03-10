"""
Bloomberg Real-Time Service
=============================
Gestion des subscriptions en temps réel via blpapi.
Utilise les signaux Qt pour communiquer avec l'interface graphique.

Usage:
    from bloomberg.realtime import BloombergService

    bbg = BloombergService()
    bbg.price_updated.connect(my_slot)
    bbg.start()
    bbg.subscribe("SFRH6 COMDTY")
"""

import blpapi
from PyQt6.QtCore import QMutex, QMutexLocker, QObject, QThread
from PyQt6.QtCore import pyqtSignal as Signal
from typing import Optional

from bloomberg.config import (
    BloombergConfig, MKTDATA_SERVICE, SUBSCRIPTION_FIELDS, normalize_ticker,
)


class BloombergEventHandler:
    """Handler d'événements Bloomberg — doit être callable."""

    def __init__(self, worker: "BloombergWorker") -> None:
        self.worker = worker

    def __call__(self, event, session) -> None:
        try:
            self.worker._process_event(event)
        except Exception as e:
            print(f"[Bloomberg] Erreur dans event handler: {e}")


class BloombergWorker(QThread):
    """Worker thread qui gère la session Bloomberg et émet les mises à jour."""

    price_updated      = Signal(str, float, float, float)         # ticker, last, bid, ask
    subscription_started = Signal(str)                            # ticker
    subscription_failed  = Signal(str, str)                       # ticker, error
    connection_status    = Signal(bool, str)                      # connected, message

    _process_subscriptions = Signal()  # signal interne

    def __init__(self, cfg: "BloombergConfig | None" = None) -> None:
        super().__init__()
        self._cfg = cfg or BloombergConfig()
        self.session: Optional["blpapi.Session"] = None  # type: ignore
        self.subscriptions: dict[str, "blpapi.CorrelationId"] = {}  # type: ignore
        self.is_running = False
        self.mutex = QMutex()
        self._pending_subscriptions: list[str] = []
        self._pending_unsubscriptions: list[str] = []
        self._process_subscriptions.connect(self._on_process_subscriptions_requested)

    # ── thread main loop ──────────────────────────────────────────────────────
    def run(self) -> None:
        try:
            opts = blpapi.sessionoptions.SessionOptions()
            opts.setServerHost(self._cfg.host)
            opts.setServerPort(self._cfg.port)
            opts.setDefaultSubscriptionService(MKTDATA_SERVICE)

            handler = BloombergEventHandler(self)
            self.session = blpapi.Session(opts, handler)  # type: ignore

            if not self.session.start():  # type: ignore
                self.connection_status.emit(False, "Impossible de démarrer la session Bloomberg")
                return

            if not self.session.openService(MKTDATA_SERVICE):  # type: ignore
                self.connection_status.emit(False, f"Impossible d'ouvrir {MKTDATA_SERVICE}")
                return

            self.is_running = True
            self.connection_status.emit(True, "Connecté à Bloomberg")
            self._process_pending_operations()

            while self.is_running:
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
                except Exception:
                    pass

    # ── subscription management ───────────────────────────────────────────────
    def _on_process_subscriptions_requested(self) -> None:
        if self.is_running and self.session:
            self._process_pending_operations()

    def _process_pending_operations(self) -> None:
        with QMutexLocker(self.mutex):
            if self._pending_subscriptions:
                sub_list = blpapi.SubscriptionList()  # type: ignore
                for ticker in self._pending_subscriptions:
                    corr_id = blpapi.CorrelationId(ticker)  # type: ignore
                    sub_list.add(ticker, SUBSCRIPTION_FIELDS, [], corr_id)
                    self.subscriptions[ticker] = corr_id
                    print(f"[Bloomberg] Subscribing to: {ticker}")
                self.session.subscribe(sub_list)  # type: ignore
                print(f"[Bloomberg] Subscribed to {len(self._pending_subscriptions)} tickers")
                self._pending_subscriptions.clear()

            if self._pending_unsubscriptions:
                unsub_list = blpapi.SubscriptionList()  # type: ignore
                for ticker in self._pending_unsubscriptions:
                    if ticker in self.subscriptions:
                        unsub_list.add(ticker, SUBSCRIPTION_FIELDS, [], self.subscriptions[ticker])
                        del self.subscriptions[ticker]
                self.session.unsubscribe(unsub_list)  # type: ignore
                self._pending_unsubscriptions.clear()

    # ── event processing ──────────────────────────────────────────────────────
    def _process_event(self, event) -> None:
        if event.eventType() == blpapi.Event.SUBSCRIPTION_DATA:  # type: ignore
            for msg in event:
                ticker = msg.correlationId().value()
                self._handle_price(msg, ticker)

        elif event.eventType() == blpapi.event.Event.SUBSCRIPTION_STATUS:
            for msg in event:
                ticker = msg.correlationId().value()
                if msg.messageType() == blpapi.names.Names.SUBSCRIPTION_STARTED:
                    self.subscription_started.emit(ticker)
                elif msg.messageType() == blpapi.names.Names.SUBSCRIPTION_FAILURE:
                    self.subscription_failed.emit(ticker, str(msg))

    def _handle_price(self, msg, ticker: str) -> None:
        last = bid = ask = None
        if msg.hasElement("LAST_PRICE"):
            try:
                last = msg.getElementAsFloat("LAST_PRICE")
            except Exception:
                pass
        if msg.hasElement("BID"):
            try:
                bid = msg.getElementAsFloat("BID")
            except Exception:
                pass
        if msg.hasElement("ASK"):
            try:
                ask = msg.getElementAsFloat("ASK")
            except Exception:
                pass
        if last is not None or bid is not None or ask is not None:
            print(f"[Bloomberg] Price update {ticker}: last={last}, bid={bid}, ask={ask}")
            self.price_updated.emit(
                ticker,
                last if last is not None else -1.0,
                bid  if bid  is not None else -1.0,
                ask  if ask  is not None else -1.0,
            )

    # ── public API ────────────────────────────────────────────────────────────
    def subscribe(self, ticker: str) -> None:
        with QMutexLocker(self.mutex):
            if ticker not in self.subscriptions and ticker not in self._pending_subscriptions:
                self._pending_subscriptions.append(ticker)
        self._process_subscriptions.emit()

    def unsubscribe(self, ticker: str) -> None:
        with QMutexLocker(self.mutex):
            if ticker in self.subscriptions or ticker in self._pending_subscriptions:
                self._pending_unsubscriptions.append(ticker)
                if ticker in self._pending_subscriptions:
                    self._pending_subscriptions.remove(ticker)
        self._process_subscriptions.emit()

    def stop(self) -> None:
        self.is_running = False
        if not self.wait(2000):
            self.terminate()
            self.wait(500)


class BloombergService(QObject):
    """Service principal Bloomberg — gère les subscriptions et relaye les signaux Qt."""

    price_updated        = Signal(str, float, float, float)
    subscription_started = Signal(str)
    subscription_failed  = Signal(str, str)
    connection_status    = Signal(bool, str)

    def __init__(self, cfg: "BloombergConfig | None" = None) -> None:
        super().__init__()
        self._cfg = cfg or BloombergConfig()
        self.worker: Optional[BloombergWorker] = None
        self._active_subscriptions: set[str] = set()

    # ── lifecycle ─────────────────────────────────────────────────────────────
    def start(self) -> None:
        if self.worker and self.worker.isRunning():
            return
        self.worker = BloombergWorker(self._cfg)
        self.worker.price_updated.connect(self.price_updated)
        self.worker.subscription_started.connect(self._on_subscription_started)
        self.worker.subscription_failed.connect(self._on_subscription_failed)
        self.worker.connection_status.connect(self.connection_status)
        self.worker.start()

    def stop(self) -> None:
        if self.worker:
            self.worker.stop()
            self.worker = None
        self._active_subscriptions.clear()

    # ── subscriptions ─────────────────────────────────────────────────────────
    def subscribe(self, ticker: str) -> None:
        ticker = normalize_ticker(ticker)
        if not ticker or ticker in self._active_subscriptions:
            return
        self._active_subscriptions.add(ticker)
        if self.worker:
            self.worker.subscribe(ticker)

    def unsubscribe(self, ticker: str) -> None:
        ticker = normalize_ticker(ticker)
        if ticker not in self._active_subscriptions:
            return
        self._active_subscriptions.discard(ticker)
        if self.worker:
            self.worker.unsubscribe(ticker)

    def subscribe_multiple(self, tickers: list[str]) -> None:
        for t in tickers:
            self.subscribe(t)

    def unsubscribe_all(self) -> None:
        for t in list(self._active_subscriptions):
            self.unsubscribe(t)

    def resubscribe_all(self) -> None:
        """Force re-subscription of all active tickers to the worker."""
        if not self.worker:
            return
        for t in self._active_subscriptions:
            self.worker.subscribe(t)

    # ── private callbacks ─────────────────────────────────────────────────────
    def _on_subscription_started(self, ticker: str) -> None:
        self.subscription_started.emit(ticker)

    def _on_subscription_failed(self, ticker: str, error: str) -> None:
        self._active_subscriptions.discard(ticker)
        self.subscription_failed.emit(ticker, error)

    # ── properties ────────────────────────────────────────────────────────────
    @property
    def is_connected(self) -> bool:
        return self.worker is not None and self.worker.isRunning()

    @property
    def active_subscriptions(self) -> set[str]:
        return self._active_subscriptions.copy()
