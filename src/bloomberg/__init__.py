"""
Package Bloomberg
=================
Outils pour interagir avec Bloomberg Terminal API

Modules:
- option_data_fetcher: Récupération de prix et Greeks d'options
- bloomberg_connector: Connecteur de base Bloomberg

Usage rapide:
    from bloomberg import BloombergOptionFetcher
    
    with BloombergOptionFetcher() as fetcher:
        option = fetcher.get_option_data('SPY', 'CALL', 450.0, '2024-12-20')
        print(f"Delta: {option.delta}")
"""

try:
    from .option_data_fetcher import (
        BloombergOptionFetcher,
        OptionData,
        format_option_table
    )
except ImportError:
    # Fallback si import relatif échoue
    from option_data_fetcher import (
        BloombergOptionFetcher,
        OptionData,
        format_option_table
    )

__all__ = [
    'BloombergOptionFetcher',
    'OptionData',
    'format_option_table',
]

__version__ = '1.0.0'
