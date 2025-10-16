"""
Bloomberg Option Data Fetcher (clean version)
=============================================
Client léger pour récupérer les prix et Greeks des options via Bloomberg API
avec une API claire et des helpers dédiés (expirations, chain par strike).

Auteur: BGC Trading Desk
Date: 2025-10-16
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date
from typing import List, Optional, Dict, Any
import logging

# --- Import blpapi (on suppose que l'environnement Bloomberg est en place) ---
import blpapi  # si besoin d'un import plus robuste, utiliser le connector dédié

# ----------------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# Modèle de données
# ----------------------------------------------------------------------------
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

    def __repr__(self) -> str:
        return (
            f"OptionData({self.ticker} | Strike={self.strike} | "
            f"Last={self.last} | Delta={self.delta} | IV={self.implied_volatility})"
        )


# ----------------------------------------------------------------------------
# Fetcher principal
# ----------------------------------------------------------------------------
class BloombergOptionFetcher:
    """
    Client Bloomberg pour récupérer les données d'options.

    Usage basique:
        fetcher = BloombergOptionFetcher()
        fetcher.connect()
        opt = fetcher.get_option_data('AAPL', 'CALL', 150.0, '2024-12-20')
        fetcher.disconnect()

    Helpers:
        - list_expirations('AAPL US Equity') -> List[date]
        - get_options_by_strike('AAPL', 'AAPL US Equity', 'CALL', 150.0)
    """

    # Champs par défaut (modifiable à l'appel)
    DEFAULT_OPTION_FIELDS: List[str] = [
        # Prix & liquidité
        'PX_BID', 'PX_ASK', 'PX_LAST', 'PX_MID', 'PX_VOLUME', 'OPEN_INT', 'BID_SIZE', 'ASK_SIZE',
        # Greeks & vol
        'DELTA', 'GAMMA', 'VEGA', 'THETA', 'RHO', 'IVOL_MID', 'IMPL_VOL_BID', 'IMPL_VOL_ASK',
        # Caractéristiques du contrat
        'OPT_STRIKE_PX', 'OPT_EXPIRE_DT', 'OPT_PUT_CALL', 'OPT_STYLE', 'OPT_MULTIPLIER', 'OPT_UNDL_TICKER',
        # Dérivés
        'OPT_INTRINSIC_VAL', 'OPT_TIME_VAL', 'OPT_THEO_PRICE'
    ]

    # Sous-jacents traités comme Index pour le suffixe option
    INDEX_LIKE = {'SPX', 'SPY', 'QQQ', 'IWM'}

    def __init__(self, host: str = 'localhost', port: int = 8194) -> None:
        self.host = host
        self.port = port
        self.session: Optional[blpapi.Session] = None
        self.refdata_service: Optional[blpapi.Service] = None

    # ---------------------------- Connexion ---------------------------------
    def connect(self) -> bool:
        """Établit la connexion avec Bloomberg Terminal."""
        try:
            logger.info(f"🔌 Connexion à Bloomberg sur {self.host}:{self.port} …")
            opts = blpapi.SessionOptions()
            opts.setServerHost(self.host)
            opts.setServerPort(int(self.port))
            self.session = blpapi.Session(opts)

            if not self.session.start():
                logger.error("❌ Échec du démarrage de la session Bloomberg")
                return False
            if not self.session.openService("//blp/refdata"):
                logger.error("❌ Échec de l'ouverture du service //blp/refdata")
                self.session.stop()
                return False

            self.refdata_service = self.session.getService("//blp/refdata")
            logger.info("✅ Session Bloomberg démarrée et service refdata ouvert")
            return True
        except Exception as e:
            logger.exception("❌ Erreur lors de la connexion: %s", e)
            return False

    def disconnect(self) -> None:
        """Ferme proprement la session Bloomberg."""
        if self.session:
            try:
                self.session.stop()
            finally:
                self.session = None
                self.refdata_service = None
                logger.info("🔌 Connexion Bloomberg fermée")

    # ---------------------------- Helpers -----------------------------------
    @staticmethod
    def _suffix_for(underlying_symbol: str, force_suffix: Optional[str] = None) -> str:
        """Détermine le suffixe Bloomberg (Equity/Index)."""
        if force_suffix:
            return force_suffix
        return "Index" if underlying_symbol.upper() in BloombergOptionFetcher.INDEX_LIKE else "Equity"

    @staticmethod
    def _parse_field(fd: blpapi.Element, field: str) -> Any:
        """Essaye successivement float, int, string; None si absent."""
        if not fd.hasElement(field):
            return None
        try:
            return fd.getElementAsFloat(field)
        except Exception:
            try:
                return fd.getElementAsInteger(field)
            except Exception:
                try:
                    return fd.getElementAsString(field)
                except Exception:
                    return None

    def _build_option_ticker(self,
                             underlying: str,
                             option_type: str,
                             strike: float,
                             expiration: str,
                             force_suffix: Optional[str] = None) -> str:
        """
        Construit le ticker Bloomberg pour une option.
        Format: UNDERLYING MM/DD/YY C/P STRIKE Equity|Index
        Exemple: SPY 12/20/24 C450 Index
        """
        exp_date = datetime.strptime(expiration, "%Y-%m-%d")
        date_str = exp_date.strftime("%m/%d/%y")
        opt_char = 'C' if option_type.upper() == 'CALL' else 'P'
        strike_str = str(int(strike)) if strike == int(strike) else str(strike)
        suffix = self._suffix_for(underlying, force_suffix)
        return f"{underlying} {date_str} {opt_char}{strike_str} {suffix}"

    # ------------------------- API publique ---------------------------------
    def list_expirations(self, underlying_equity: str) -> List[date]:
        """Retourne la liste triée des dates d'expiration via OPT_EXPIRE_DT_LIST."""
        if not (self.session and self.refdata_service):
            raise RuntimeError("Session Bloomberg non connectée. Appelez connect() d'abord.")

        req = self.refdata_service.createRequest("ReferenceDataRequest")
        req.append("securities", underlying_equity)  # ex: "AAPL US Equity"
        req.append("fields", "OPT_EXPIRE_DT_LIST")
        self.session.sendRequest(req)

        expirations: set[date] = set()
        while True:
            ev = self.session.nextEvent(500)
            for msg in ev:
                if msg.hasElement("securityData"):
                    sec_data = msg.getElement("securityData")
                    for i in range(sec_data.numValues()):
                        sec = sec_data.getValueAsElement(i)
                        if sec.hasElement("fieldData"):
                            fd = sec.getElement("fieldData")
                            if fd.hasElement("OPT_EXPIRE_DT_LIST"):
                                bulk = fd.getElement("OPT_EXPIRE_DT_LIST")
                                for j in range(bulk.numValues()):
                                    row = bulk.getValueAsElement(j)
                                    if row.hasElement("Date"):
                                        expirations.add(row.getElementAsDatetime("Date").date())
            if ev.eventType() == blpapi.Event.RESPONSE:
                break

        return sorted(expirations)

    def get_option_data(self,
                        underlying: str,
                        option_type: str,
                        strike: float,
                        expiration: str,
                        fields: Optional[List[str]] = None,
                        force_suffix: Optional[str] = None) -> Optional[OptionData]:
        """Récupère les données d'une option spécifique (snapshot)."""
        if not (self.session and self.refdata_service):
            logger.error("❌ Session Bloomberg non connectée. Appelez connect() d'abord.")
            return None

        ticker = self._build_option_ticker(underlying, option_type, strike, expiration, force_suffix)
        if fields is None:
            fields = self.DEFAULT_OPTION_FIELDS

        logger.info(f"🔍 Récupération des données pour {ticker} …")
        request = self.refdata_service.createRequest("ReferenceDataRequest")
        request.append("securities", ticker)
        for f in fields:
            request.append("fields", f)

        self.session.sendRequest(request)

        data: Dict[str, Any] = {}
        while True:
            event = self.session.nextEvent(500)
            if event.eventType() in (blpapi.Event.PARTIAL_RESPONSE, blpapi.Event.RESPONSE):
                for msg in event:
                    if msg.hasElement("securityData"):
                        sec_data = msg.getElement("securityData")
                        for i in range(sec_data.numValues()):
                            sec = sec_data.getValueAsElement(i)
                            if sec.hasElement("fieldData"):
                                fd = sec.getElement("fieldData")
                                for f in fields:
                                    data[f] = self._parse_field(fd, f)
            if event.eventType() == blpapi.Event.RESPONSE:
                break

        exp_date = datetime.strptime(expiration, "%Y-%m-%d").date()
        opt = OptionData(
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
            implied_volatility=data.get('IVOL_MID') or data.get('IMPL_VOL_MID'),
            open_interest=data.get('OPEN_INT'),
            volume=data.get('PX_VOLUME'),
        )
        logger.info(f"✅ Données récupérées: {opt}")
        return opt

    def get_options_by_strike(self,
                              underlying_symbol: str,
                              underlying_equity: str,
                              option_type: str,
                              strike: float,
                              fields: Optional[List[str]] = None,
                              force_suffix: Optional[str] = None) -> List[OptionData]:
        """
        Récupère toutes les options d'un strike donné (CALL/PUT) pour *toutes* les expirations.
        - underlying_symbol: ex. "AAPL" (construction du ticker d'option)
        - underlying_equity: ex. "AAPL US Equity" (pour lister les expirations)
        """
        results: List[OptionData] = []
        expirations = self.list_expirations(underlying_equity)
        if not expirations:
            logger.warning("⚠️ Aucune expiration trouvée pour %s", underlying_equity)
            return results

        for exp in expirations:
            iso = exp.strftime("%Y-%m-%d")
            opt = self.get_option_data(
                underlying=underlying_symbol,
                option_type=option_type,
                strike=strike,
                expiration=iso,
                fields=fields or self.DEFAULT_OPTION_FIELDS,
                force_suffix=force_suffix,
            )
            if opt:
                results.append(opt)
        logger.info("✅ %d options récupérées pour %s %s @ %s", len(results), underlying_symbol, option_type, strike)
        return results

    # Context manager
    def __enter__(self) -> "BloombergOptionFetcher":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.disconnect()


# ----------------------------------------------------------------------------
# Helpers d'affichage (inchangés)
# ----------------------------------------------------------------------------

def format_option_table(options: List[OptionData]) -> str:
    if not options:
        return "Aucune donnée"

    lines: List[str] = []
    lines.append("\n" + "=" * 130)
    lines.append(
        f"{'Type':<6} {'Strike':<8} {'Bid':<8} {'Ask':<8} {'Last':<8} "
        f"{'Delta':<8} {'Gamma':<8} {'Vega':<8} {'Theta':<8} {'IV%':<8}"
    )
    lines.append("-" * 130)

    for opt in options:
        lines.append(
            f"{opt.option_type:<6} "
            f"${opt.strike:<7.2f} "
            f"${(opt.bid or 0):<7.2f} "
            f"${(opt.ask or 0):<7.2f} "
            f"${(opt.last or 0):<7.2f} "
            f"{(opt.delta or 0):<8.4f} "
            f"{(opt.gamma or 0):<8.4f} "
            f"{(opt.vega or 0):<8.4f} "
            f"{(opt.theta or 0):<8.4f} "
            f"{(opt.implied_volatility or 0):<8.2f}"
        )

    lines.append("=" * 130 + "\n")
    return "\n".join(lines)


if __name__ == "__main__":
    print("Module Bloomberg Option Data Fetcher (clean)")
    print("Exemple rapide :\n"
          "with BloombergOptionFetcher() as f:\n"
          "    data = f.get_options_by_strike('AAPL', 'AAPL US Equity', 'CALL', 150.0)\n"
          "    print(format_option_table(data))")
