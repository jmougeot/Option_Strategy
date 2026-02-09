"""
Bloomberg BDH (Historical Data) Fetcher
=========================================
Récupère les données historiques d'options via l'API Bloomberg blpapi.

Équivalent de la formule Excel:
    =@BDH("SFRH5C 96.00 Comdty", "PX_LAST", "30/07/2024", "13/03/2025")

Utilise HistoricalDataRequest au lieu de ReferenceDataRequest.
"""

import blpapi  # type: ignore[import-untyped]
from blpapi.event import Event
from blpapi.session import Session
from blpapi.sessionoptions import SessionOptions
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from backtesting.config import SFRConfig
from backtesting.bloomberg.ticker_builder import SFRTickerBuilder


# ============================================================================
# CONNEXION BLOOMBERG (réutilise le pattern existant)
# ============================================================================

_session: Optional[Session] = None


def _get_session(host: str = "localhost", port: int = 8194) -> Session:
    """Retourne (ou crée) une session Bloomberg synchrone."""
    global _session
    if _session is None:
        opts = SessionOptions()
        opts.setServerHost(host)
        opts.setServerPort(port)
        opts.setAutoRestartOnDisconnection(True)
        opts.setNumStartAttempts(3)

        _session = Session(opts)
        if not _session.start():
            _session = None
            raise ConnectionError(
                f"Impossible de démarrer la session Bloomberg ({host}:{port})"
            )
        if not _session.openService("//blp/refdata"):
            raise ConnectionError("Impossible d'ouvrir le service //blp/refdata")
    return _session


def close_session():
    """Ferme proprement la session Bloomberg."""
    global _session
    if _session:
        _session.stop()
        _session = None


# ============================================================================
# BDH FETCHER
# ============================================================================

class BDHFetcher:
    """
    Récupère les séries historiques (BDH) de prix d'options depuis Bloomberg.

    La requête HistoricalDataRequest est l'équivalent programmatique de
    =@BDH("SFRH5C 96.00 Comdty", "PX_LAST", "30/07/2024", "13/03/2025")

    Usage:
        fetcher = BDHFetcher(config, builder)
        fetcher.fetch_all()
        df = fetcher.to_dataframe()
    """

    def __init__(self, config: SFRConfig, builder: SFRTickerBuilder):
        self.config = config
        self.builder = builder

        # Résultats : {ticker -> {date -> price}}
        self.raw_data: Dict[str, Dict[date, float]] = {}

        # DataFrame consolidé (index=dates, columns=tickers)
        self._df: Optional[pd.DataFrame] = None

    # -----------------------------------------------------------------
    # Fetch principal
    # -----------------------------------------------------------------

    def fetch_all(self) -> "BDHFetcher":
        """
        Fetch l'historique PX_LAST de tous les tickers (calls + puts)
        et du sous-jacent, via Bloomberg HistoricalDataRequest.

        Retourne self pour chainage.
        """
        all_tickers = self.builder.all_tickers + [self.builder.underlying_ticker]
        print(f"[BDHFetcher] Fetching {len(all_tickers)} tickers "
              f"du {self.config.start_date} au {self.config.end_date} ...")

        # Séparer en batches pour éviter les limites Bloomberg
        batch_size = 25
        for i in range(0, len(all_tickers), batch_size):
            batch = all_tickers[i:i + batch_size]
            self._fetch_batch(batch)

        n_dates = len(set().union(*[d.keys() for d in self.raw_data.values()])) if self.raw_data else 0
        print(f"[BDHFetcher] Données reçues pour {len(self.raw_data)} tickers, "
              f"~{n_dates} dates")

        return self

    def _fetch_batch(self, tickers: List[str]):
        """Fetch un batch de tickers via HistoricalDataRequest."""
        try:
            session = _get_session()
            service = session.getService("//blp/refdata")

            request = service.createRequest("HistoricalDataRequest")

            # Ajouter les tickers
            for ticker in tickers:
                request.append("securities", ticker)

            # Champs
            request.append("fields", self.config.bbg_field)

            # Dates (format YYYYMMDD)
            request.set("startDate", self.config.start_date_str)
            request.set("endDate", self.config.end_date_str)

            # Options
            request.set("periodicitySelection", "DAILY")
            request.set("nonTradingDayFillOption", "NON_TRADING_WEEKDAYS")
            request.set("nonTradingDayFillMethod", "PREVIOUS_VALUE")

            session.sendRequest(request)

            # Lire les réponses
            while True:
                event = session.nextEvent(10_000)
                evt_type = event.eventType()

                if evt_type in (Event.RESPONSE, Event.PARTIAL_RESPONSE):
                    self._parse_historical_response(event)

                if evt_type == Event.RESPONSE:
                    break

        except Exception as e:
            print(f"[BDHFetcher] Erreur batch: {e}")
            import traceback
            traceback.print_exc()

    def _parse_historical_response(self, event: Event):
        """Parse une réponse HistoricalDataRequest."""
        for msg in event:
            if not msg.hasElement("securityData"):
                continue

            security_data = msg.getElement("securityData")

            # HistoricalDataRequest retourne un seul security par message
            ticker = security_data.getElementAsString("security")

            if security_data.hasElement("securityError"):
                err = security_data.getElement("securityError")
                err_msg = err.getElementAsString("message") if err.hasElement("message") else "?"
                print(f"  [WARN] {ticker}: {err_msg}")
                return

            if not security_data.hasElement("fieldData"):
                return

            field_data = security_data.getElement("fieldData")
            ticker_data: Dict[date, float] = {}

            for j in range(field_data.numValues()):
                row = field_data.getValueAsElement(j)
                try:
                    dt = row.getElementAsDatetime("date")
                    row_date = date(dt.year, dt.month, dt.day)

                    val = None
                    if row.hasElement(self.config.bbg_field):
                        val = row.getElementAsFloat(self.config.bbg_field)

                    if val is not None and val > 0:
                        ticker_data[row_date] = val
                except Exception:
                    continue

            if ticker_data:
                self.raw_data[ticker] = ticker_data

    # -----------------------------------------------------------------
    # Conversion en DataFrame
    # -----------------------------------------------------------------

    def to_dataframe(self) -> pd.DataFrame:
        """
        Convertit les données brutes en DataFrame pandas.

        Returns:
            DataFrame avec index=dates, columns=tickers, values=PX_LAST
        """
        if self._df is not None:
            return self._df

        if not self.raw_data:
            self._df = pd.DataFrame()
            return self._df

        # Construire le DataFrame
        series_dict = {}
        for ticker, date_prices in self.raw_data.items():
            series_dict[ticker] = pd.Series(date_prices, name=ticker)

        self._df = pd.DataFrame(series_dict)
        self._df.index = pd.DatetimeIndex(self._df.index)
        self._df.sort_index(inplace=True)

        # Forward-fill les trous (jours sans trading)
        self._df.ffill(inplace=True)

        return self._df

    def get_prices_at_date(self, target_date: date) -> Dict[str, float]:
        """
        Retourne les prix de tous les tickers pour une date donnée.

        Args:
            target_date: Date cible

        Returns:
            {ticker: price}
        """
        df = self.to_dataframe()
        if df.empty:
            return {}

        # Trouver la date la plus proche (en arrière)
        idx = df.index.searchsorted(pd.Timestamp(target_date), side="right") - 1
        if idx < 0:
            idx = 0

        row = df.iloc[idx]
        return {col: row[col] for col in df.columns if pd.notna(row[col])}

    def get_call_prices_at_date(self, target_date: date) -> Tuple[np.ndarray, np.ndarray]:
        """
        Retourne les arrays (strikes, call_prices) pour une date donnée.

        Returns:
            (strikes, call_prices) triés par strike croissant
        """
        prices = self.get_prices_at_date(target_date)
        strikes = []
        call_prices = []

        for ticker in self.builder.call_tickers:
            if ticker in prices:
                meta = self.builder.metadata[ticker]
                strikes.append(meta.strike)
                call_prices.append(prices[ticker])

        if not strikes:
            return np.array([]), np.array([])

        # Trier par strike
        order = np.argsort(strikes)
        return np.array(strikes)[order], np.array(call_prices)[order]

    def get_put_prices_at_date(self, target_date: date) -> Tuple[np.ndarray, np.ndarray]:
        """
        Retourne les arrays (strikes, put_prices) pour une date donnée.

        Returns:
            (strikes, put_prices) triés par strike croissant
        """
        prices = self.get_prices_at_date(target_date)
        strikes = []
        put_prices = []

        for ticker in self.builder.put_tickers:
            if ticker in prices:
                meta = self.builder.metadata[ticker]
                strikes.append(meta.strike)
                put_prices.append(prices[ticker])

        if not strikes:
            return np.array([]), np.array([])

        order = np.argsort(strikes)
        return np.array(strikes)[order], np.array(put_prices)[order]

    def get_underlying_at_date(self, target_date: date) -> Optional[float]:
        """Retourne le prix du sous-jacent pour une date donnée."""
        prices = self.get_prices_at_date(target_date)
        return prices.get(self.builder.underlying_ticker)

    def get_all_dates(self) -> List[date]:
        """Retourne la liste de toutes les dates disponibles."""
        df = self.to_dataframe()
        if df.empty:
            return []
        return [d.date() for d in df.index]

    # -----------------------------------------------------------------
    # Sauvegarde / Chargement CSV
    # -----------------------------------------------------------------

    def save_to_csv(self, filepath: str):
        """Sauvegarde les données en CSV pour usage offline."""
        df = self.to_dataframe()
        if not df.empty:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(filepath)
            print(f"[BDHFetcher] Données sauvegardées → {filepath}")

    @classmethod
    def load_from_csv(cls, filepath: str, config: SFRConfig,
                      builder: SFRTickerBuilder) -> "BDHFetcher":
        """
        Charge les données depuis un CSV (mode offline).

        Args:
            filepath: Chemin du CSV
            config: Configuration SFR
            builder: Ticker builder (doit être déjà build())

        Returns:
            BDHFetcher avec les données chargées
        """
        fetcher = cls(config, builder)
        df = pd.read_csv(filepath, index_col=0, parse_dates=True)
        fetcher._df = df

        # Reconstruire raw_data depuis le DataFrame
        for col in df.columns:
            date_prices = {}
            for idx, val in df[col].items():
                if pd.notna(val) and val > 0:
                    date_prices[idx.date()] = val
            if date_prices:
                fetcher.raw_data[col] = date_prices

        print(f"[BDHFetcher] Données chargées depuis {filepath}: "
              f"{len(df.columns)} tickers, {len(df)} dates")
        return fetcher
