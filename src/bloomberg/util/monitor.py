"""
Options Monitor - Surveillance en temps réel de plusieurs options (Calls/Puts)
Permet de suivre les prix de plusieurs strikes simultanément
"""

import time
from argparse import ArgumentParser, RawTextHelpFormatter
from datetime import datetime

import blpapi

from bloomberg.util.ConnectionAndAuthOptions import (
    addConnectionAndAuthOptions,
    createSessionOptions,
)

# Champs à surveiller pour les options
DEFAULT_FIELDS = [
    "LAST_PRICE",
    "BID",
    "ASK",
    "VOLUME",
    "OPEN_INT",
    "IVOL_MID",
]

DEFAULT_SERVICE = "//blp/mktdata"


class OptionData:
    """Stocke les données d'une option"""
    def __init__(self, ticker):
        self.ticker = ticker
        self.last_price = None
        self.bid = None
        self.ask = None
        self.volume = None
        self.open_interest = None
        self.ivol = None
        self.last_update = None

    def update(self, msg):
        """Met à jour les données depuis un message Bloomberg"""
        if msg.hasElement("LAST_PRICE"):
            self.last_price = msg.getElementAsFloat("LAST_PRICE")
        if msg.hasElement("BID"):
            self.bid = msg.getElementAsFloat("BID")
        if msg.hasElement("ASK"):
            self.ask = msg.getElementAsFloat("ASK")
        if msg.hasElement("VOLUME"):
            self.volume = msg.getElementAsInteger("VOLUME")
        if msg.hasElement("OPEN_INT"):
            self.open_interest = msg.getElementAsInteger("OPEN_INT")
        if msg.hasElement("IVOL_MID"):
            self.ivol = msg.getElementAsFloat("IVOL_MID")
        self.last_update = datetime.now()

    def __str__(self):
        mid = None
        if self.bid and self.ask:
            mid = (self.bid + self.ask) / 2
        
        return (
            f"{self.ticker:<40} | "
            f"Last: {self.last_price or 'N/A':>8} | "
            f"Bid: {self.bid or 'N/A':>8} | "
            f"Ask: {self.ask or 'N/A':>8} | "
            f"Mid: {mid or 'N/A':>8} | "
            f"Vol: {self.volume or 'N/A':>8} | "
            f"OI: {self.open_interest or 'N/A':>8} | "
            f"IV: {f'{self.ivol*100:.2f}%' if self.ivol else 'N/A':>8}"
        )


class OptionsMonitorHandler:
    """Handler pour les événements de subscription"""
    
    def __init__(self):
        self.options_data = {}  # ticker -> OptionData
        self.is_running = True

    def register_option(self, ticker):
        """Enregistre une nouvelle option à surveiller"""
        self.options_data[ticker] = OptionData(ticker)

    def print_header(self):
        """Affiche l'en-tête du tableau"""
        print("\n" + "=" * 140)
        print(f"{'OPTION':<40} | {'Last':>8} | {'Bid':>8} | {'Ask':>8} | {'Mid':>8} | {'Vol':>8} | {'OI':>8} | {'IV':>8}")
        print("=" * 140)

    def print_all_options(self):
        """Affiche toutes les options"""
        self.print_header()
        for ticker in sorted(self.options_data.keys()):
            print(self.options_data[ticker])
        print("=" * 140)
        print(f"Dernière mise à jour: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def processSubscriptionStatus(self, event):
        """Traite les événements de statut de subscription"""
        for msg in event:
            topic = msg.correlationId().value()
            if msg.messageType() == blpapi.Names.SUBSCRIPTION_FAILURE:
                print(f"[ERREUR] Subscription échouée pour: {topic}")
                print(f"         {msg}")
            elif msg.messageType() == blpapi.Names.SUBSCRIPTION_TERMINATED:
                print(f"[INFO] Subscription terminée pour: {topic}")
            elif msg.messageType() == blpapi.Names.SUBSCRIPTION_STARTED:
                print(f"[OK] Subscription démarrée pour: {topic}")

    def processSubscriptionDataEvent(self, event):
        """Traite les données reçues"""
        for msg in event:
            topic = msg.correlationId().value()
            if topic in self.options_data:
                self.options_data[topic].update(msg)
        
        # Afficher le tableau mis à jour
        self.print_all_options()

    def processMiscEvents(self, event):
        """Traite les autres événements"""
        for msg in event:
            if msg.messageType() == blpapi.Names.SESSION_TERMINATED:
                print("[INFO] Session terminée")
                self.is_running = False
            elif msg.messageType() == blpapi.Names.SLOW_CONSUMER_WARNING:
                print("[WARNING] Slow consumer - données potentiellement perdues")

    def processEvent(self, event, _session) -> None:
        """Point d'entrée principal pour le traitement des événements"""
        try:
            if event.eventType() == blpapi.Event.SUBSCRIPTION_DATA:  # type: ignore
                self.processSubscriptionDataEvent(event)
            elif event.eventType() == blpapi.Event.SUBSCRIPTION_STATUS:  # type: ignore
                self.processSubscriptionStatus(event)
            else:
                self.processMiscEvents(event)
        except blpapi.Exception as exception:
            print(f"[ERREUR] Échec du traitement: {exception}")


def build_option_ticker(underlying, expiry, strike, option_type):
    """
    Construit le ticker Bloomberg pour une option.
    
    Args:
        underlying: "SPY US", "AAPL US", etc.
        expiry: "12/20/25" (MM/DD/YY)
        strike: 590, 600, etc.
        option_type: "C" pour Call, "P" pour Put
    
    Returns:
        Ticker Bloomberg: "SPY US 12/20/25 C590 Equity"
    """
    return f"{underlying} {expiry} {option_type}{strike} Equity"


def parseCmdLine():
    """Parse les arguments de la ligne de commande"""
    parser = ArgumentParser(
        formatter_class=RawTextHelpFormatter,
        description="Moniteur d'options en temps réel - Surveillez plusieurs strikes/types simultanément",
    )
    
    addConnectionAndAuthOptions(parser)
    
    # Option 1: Construire les tickers automatiquement
    parser.add_argument(
        "--underlying",
        dest="underlying",
        help="Sous-jacent (ex: 'SPY US', 'AAPL US')",
        metavar="underlying",
    )
    parser.add_argument(
        "--expiry",
        dest="expiry",
        help="Date d'expiration (format: MM/DD/YY, ex: '12/20/25')",
        metavar="expiry",
    )
    parser.add_argument(
        "--strikes",
        dest="strikes",
        nargs="+",
        type=float,
        help="Liste des strikes à surveiller (ex: 580 585 590 595 600)",
        metavar="strike",
    )
    parser.add_argument(
        "--types",
        dest="option_types",
        nargs="+",
        choices=["C", "P"],
        default=["C", "P"],
        help="Types d'options: C (Call), P (Put). Par défaut: C P",
        metavar="type",
    )
    
    # Option 2: Spécifier les tickers directement
    parser.add_argument(
        "--tickers",
        dest="tickers",
        nargs="+",
        help="Tickers Bloomberg complets (ex: 'SPY US 12/20/25 C590 Equity')",
        metavar="ticker",
    )
    
    # Champs à surveiller
    parser.add_argument(
        "-f", "--field",
        dest="fields",
        action="append",
        default=[],
        help="Champs à surveiller. Par défaut: LAST_PRICE, BID, ASK, VOLUME, OPEN_INT, IVOL_MID",
        metavar="field",
    )
    
    # Intervalle de rafraîchissement
    parser.add_argument(
        "-i", "--interval",
        dest="interval",
        type=float,
        help="Intervalle de mise à jour en secondes (optionnel)",
        metavar="interval",
    )

    options = parser.parse_args()
    return options


def main():
    options = parseCmdLine()
    
    # Construire la liste des tickers
    tickers = []
    
    if options.tickers:
        # Utiliser les tickers fournis directement
        tickers = options.tickers
    elif options.underlying and options.expiry and options.strikes:
        # Construire les tickers à partir des paramètres
        for strike in options.strikes:
            for opt_type in options.option_types:
                ticker = build_option_ticker(
                    options.underlying,
                    options.expiry,
                    int(strike) if strike == int(strike) else strike,
                    opt_type
                )
                tickers.append(ticker)
    else:
        print("Erreur: Vous devez spécifier soit --tickers, soit --underlying + --expiry + --strikes")
        print("\nExemples:")
        print('  python OptionsMonitor.py --underlying "SPY US" --expiry "12/20/25" --strikes 580 590 600 --types C P')
        print('  python OptionsMonitor.py --tickers "SPY US 12/20/25 C590 Equity" "SPY US 12/20/25 P590 Equity"')
        return

    # Champs à surveiller
    fields = options.fields if options.fields else DEFAULT_FIELDS
    
    print("\n" + "=" * 60)
    print("OPTIONS MONITOR - Surveillance en temps réel")
    print("=" * 60)
    print(f"Nombre d'options: {len(tickers)}")
    print(f"Champs surveillés: {', '.join(fields)}")
    print("\nOptions à surveiller:")
    for t in tickers:
        print(f"  - {t}")
    print("=" * 60 + "\n")

    # Configuration de la session
    sessionOptions = createSessionOptions(options)
    sessionOptions.setDefaultSubscriptionService(DEFAULT_SERVICE)
    sessionOptions.setSessionName("options-monitor")
    
    # Créer le handler
    handler = OptionsMonitorHandler()
    for ticker in tickers:
        handler.register_option(ticker)
    
    # Créer la session
    session = blpapi.Session(sessionOptions, handler.processEvent)

    try:
        if not session.start():
            print("[ERREUR] Impossible de démarrer la session")
            return

        if not session.openService(DEFAULT_SERVICE):
            print(f"[ERREUR] Impossible d'ouvrir le service {DEFAULT_SERVICE}")
            return

        # Créer les subscriptions
        subscriptions = blpapi.SubscriptionList()
        sub_options = []
        
        if options.interval:
            sub_options.append(f"interval={options.interval}")
        
        for ticker in tickers:
            subscriptions.add(
                ticker,
                fields,
                sub_options,
                blpapi.CorrelationId(ticker)
            )

        # Démarrer les subscriptions
        session.subscribe(subscriptions)
        
        print("\nSurveillance active. Appuyez sur ENTER pour quitter...\n")
        input()

    except KeyboardInterrupt:
        print("\nArrêt demandé par l'utilisateur...")
    finally:
        session.stop()
        print("Session terminée.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[ERREUR] {e}")


__copyright__ = """
Copyright 2024. Options Monitor for Bloomberg API.
Based on Bloomberg API examples.
"""
