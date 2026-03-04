"""
Strategy backtesting sub-module.
Construit des Options à partir de données historiques BDH,
génère/score les stratégies, et mesure les performances réalisées.
"""

from src.backtesting.strategy.option_builder import OptionBuilder
from src.backtesting.strategy.backtest_engine import BacktestEngine, BacktestConfig
from src.backtesting.strategy.results import BacktestResults, TradeRecord, WeightGridResult

__all__ = [
    "OptionBuilder",
    "BacktestEngine",
    "BacktestConfig",
    "BacktestResults",
    "TradeRecord",
    "WeightGridResult",
]
