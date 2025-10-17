"""
Bloomberg Integration Module
=============================
Module refactorisé pour récupérer les données d'options depuis Bloomberg Terminal.

Architecture modulaire:
- models.py: Dataclasses pour les données (OptionData, EuriborOptionData)
- connection.py: Gestion de la connexion Bloomberg
- ticker_builder.py: Construction des tickers Bloomberg (actions, indices, EURIBOR)
- fetcher.py: Client principal pour récupérer les données
- formatters.py: Fonctions d'affichage et formatage

Usage rapide:
    from bloomberg import BloombergOptionFetcher
    
    # Options sur actions/indices
    with BloombergOptionFetcher() as fetcher:
        option = fetcher.get_option_data('AAPL', date(2024, 12, 20), 'C', 150.0)
        print(f"Delta: {option.delta}, IV: {option.implied_volatility}%")
    
    # Options EURIBOR (taux)
    with BloombergOptionFetcher() as fetcher:
        euribor = fetcher.get_option_data('ER', date(2025, 3, 15), 'C', 97.50, is_euribor=True)
        print(f"Implied Rate: {euribor.implied_rate}%")

Auteur: BGC Trading Desk
Date: 2025-10-16
"""

# Imports principaux
try:
    from .models import OptionData
    from .connection import BloombergConnection, test_connection
    from .ticker_builder import (
        build_option_ticker,

    )
    from .fetcher import BloombergOptionFetcher, DEFAULT_OPTION_FIELDS
    from .formatters import (
        format_option_summary,
        format_option_table,
        format_greeks_summary,
        format_liquidity_check,
        format_term_structure
    )

except ImportError as e:
    # Fallback pour imports absolus
    print(f"Warning: Relative imports failed ({e}), trying absolute imports")
    from models import OptionData
    from connection import BloombergConnection, test_connection
    from ticker_builder import build_option_ticker
    from fetcher import BloombergOptionFetcher, DEFAULT_OPTION_FIELDS
    from formatters import (
        format_option_summary,
        format_option_table,
        format_greeks_summary,
        format_liquidity_check,
        format_term_structure
    )

__all__ = [
    # Models
    'OptionData',
    'EuriborOptionData',
    
    # Connection
    'BloombergConnection',
    'test_connection',
    
    # Ticker building
    'build_option_ticker',

    # Fetching
    'BloombergOptionFetcher',
    'DEFAULT_OPTION_FIELDS',
    
    # Formatters
    'format_option_summary',
    'format_option_table',
    'format_greeks_summary',
    'format_liquidity_check',
    'format_term_structure',
]

__version__ = '2.0.0'
