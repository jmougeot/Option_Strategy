"""
Backtesting Results
====================
Agrège, analyse et exporte les résultats du backtesting de stratégies.

Fournit :
- ``TradeRecord``      : enregistrement unitaire d'un trade
- ``BacktestResults``  : collection de trades + métriques
- ``WeightGridResult`` : comparaison de plusieurs jeux de poids
"""

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


# ============================================================================
# TRADE RECORD
# ============================================================================

@dataclass
class TradeRecord:
    """Enregistrement complet d'un trade backtesté."""

    # --- Dates ---
    entry_date: date
    expiry_date: date

    # --- Stratégie ---
    strategy_name: str
    n_legs: int
    legs_detail: List[Dict[str, Any]] = field(default_factory=list)

    # --- Entrée ---
    entry_premium: float = 0.0
    predicted_avg_pnl: float = 0.0
    predicted_score: float = 0.0
    rank_at_entry: int = 1

    # --- Résultats ---
    realized_pnl: float = 0.0
    underlying_at_entry: Optional[float] = None
    underlying_at_expiry: Optional[float] = None

    # --- Bornes ---
    max_profit: float = 0.0
    max_loss: float = 0.0
    total_delta: float = 0.0

    # --- Mark-to-Market ---
    mtm_series: Dict[date, float] = field(default_factory=dict)


# ============================================================================
# BACKTEST RESULTS
# ============================================================================

class BacktestResults:
    """
    Résultats complets du backtesting.

    Fournit :
    - DataFrame détaillé de tous les trades
    - Métriques agrégées (hit rate, Sharpe, max drawdown, etc.)
    - Corrélation prédiction vs réalité
    - Mark-to-market par trade
    - P&L cumulé
    - Export CSV

    Usage::

        results = engine.run(csv_path="data.csv")
        df = results.to_dataframe()
        metrics = results.summary_metrics()
        results.print_summary()
        results.save_to_csv("output/backtest.csv")
    """

    def __init__(self, trades: List[TradeRecord], config: Any,
                 scoring_weights: Optional[Dict[str, float]] = None):
        self.trades = trades
        self.config = config
        self.scoring_weights = scoring_weights or {}
        self._df: Optional[pd.DataFrame] = None

    # -----------------------------------------------------------------
    # DataFrame
    # -----------------------------------------------------------------

    def to_dataframe(self) -> pd.DataFrame:
        """Convertit tous les trades en DataFrame pandas."""
        if self._df is not None:
            return self._df

        records = []
        for t in self.trades:
            records.append({
                "entry_date": t.entry_date,
                "expiry_date": t.expiry_date,
                "strategy_name": t.strategy_name,
                "n_legs": t.n_legs,
                "entry_premium": t.entry_premium,
                "predicted_avg_pnl": t.predicted_avg_pnl,
                "predicted_score": t.predicted_score,
                "realized_pnl": t.realized_pnl,
                "underlying_at_entry": t.underlying_at_entry,
                "underlying_at_expiry": t.underlying_at_expiry,
                "rank_at_entry": t.rank_at_entry,
                "max_profit": t.max_profit,
                "max_loss": t.max_loss,
                "total_delta": t.total_delta,
                "prediction_error": t.realized_pnl - t.predicted_avg_pnl,
                "hit": 1 if t.realized_pnl > 0 else 0,
            })

        self._df = pd.DataFrame(records)
        if not self._df.empty:
            self._df.set_index("entry_date", inplace=True)
        return self._df

    # -----------------------------------------------------------------
    # Métriques agrégées
    # -----------------------------------------------------------------

    def summary_metrics(self) -> Dict[str, float]:
        """
        Calcule les métriques agrégées du backtesting.

        Returns:
            Dict avec n_trades, total_pnl, avg_pnl, std_pnl,
            sharpe_ratio, hit_rate, avg_win, avg_loss, profit_factor,
            max_drawdown, best_trade, worst_trade, prediction_correlation
        """
        df = self.to_dataframe()
        if df.empty:
            return {}

        pnls = df["realized_pnl"].dropna()
        if pnls.empty:
            return {}

        n = len(pnls)
        avg = float(pnls.mean())
        std = float(pnls.std()) if n > 1 else 0.0
        sharpe = avg / std if std > 0 else 0.0

        # Max drawdown
        cumulative = pnls.cumsum()
        running_max = cumulative.cummax()
        drawdowns = cumulative - running_max
        max_dd = float(drawdowns.min())

        # Hit rate
        hits = pnls > 0
        hit_rate = float(hits.mean())

        # Gains / pertes moyens
        avg_win = float(pnls[hits].mean()) if hits.any() else 0.0
        avg_loss = float(pnls[~hits].mean()) if (~hits).any() else 0.0
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float("inf")

        # Corrélation prédiction vs réalité
        corr = np.nan
        if "predicted_avg_pnl" in df.columns:
            pred = df["predicted_avg_pnl"].dropna()
            real = df["realized_pnl"].dropna()
            common = pred.index.intersection(real.index)
            if len(common) > 2:
                corr = float(pred.loc[common].corr(real.loc[common]))

        return {
            "n_trades": n,
            "total_pnl": float(pnls.sum()),
            "avg_pnl": avg,
            "std_pnl": std,
            "sharpe_ratio": sharpe,
            "hit_rate": hit_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "max_drawdown": max_dd,
            "best_trade": float(pnls.max()),
            "worst_trade": float(pnls.min()),
            "prediction_correlation": corr,
        }

    # -----------------------------------------------------------------
    # Mark-to-Market
    # -----------------------------------------------------------------



    # -----------------------------------------------------------------
    # Export
    # -----------------------------------------------------------------

    def save_to_csv(self, filepath: str):
        """Sauvegarde les résultats en CSV."""
        df = self.to_dataframe()
        if not df.empty:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(filepath)
            print(f"[Results] Résultats sauvegardés → {filepath}")

    # -----------------------------------------------------------------
    # Affichage
    # -----------------------------------------------------------------

    def print_summary(self):
        """Affiche un résumé formaté des résultats."""
        metrics = self.summary_metrics()
        if not metrics:
            print("\n  Aucun trade effectué.")
            return

        print("\n" + "=" * 60)
        print("  RÉSULTATS DU BACKTESTING")
        print("=" * 60)
        print(f"  Nombre de trades       : {metrics['n_trades']}")
        print(f"  P&L total              : {metrics['total_pnl']:.4f}")
        print(f"  P&L moyen              : {metrics['avg_pnl']:.4f}")
        print(f"  Écart-type P&L         : {metrics['std_pnl']:.4f}")
        print(f"  Sharpe Ratio           : {metrics['sharpe_ratio']:.2f}")
        print(f"  Hit Rate               : {metrics['hit_rate']:.1%}")
        print(f"  Gain moyen (wins)      : {metrics['avg_win']:.4f}")
        print(f"  Perte moyenne (losses) : {metrics['avg_loss']:.4f}")
        print(f"  Profit Factor          : {metrics['profit_factor']:.2f}")
        print(f"  Max Drawdown           : {metrics['max_drawdown']:.4f}")
        print(f"  Meilleur trade         : {metrics['best_trade']:.4f}")
        print(f"  Pire trade             : {metrics['worst_trade']:.4f}")

        corr = metrics.get("prediction_correlation", np.nan)
        if not np.isnan(corr):
            print(f"  Corr(prédit, réalisé)  : {corr:.3f}")

        print("=" * 60)

        # Top 5 trades
        df = self.to_dataframe()
        if not df.empty and len(df) >= 3:
            print("\n  ─── Top 5 meilleurs trades ───")
            top = df.nlargest(5, "realized_pnl")[
                ["strategy_name", "realized_pnl", "predicted_avg_pnl"]
            ]
            for idx, row in top.iterrows():
                print(f"  {idx} │ {row['strategy_name']:<30} │ "
                      f"réel={row['realized_pnl']:+.4f}  prédit={row['predicted_avg_pnl']:+.4f}")

            print("\n  ─── Top 5 pires trades ───")
            worst = df.nsmallest(5, "realized_pnl")[
                ["strategy_name", "realized_pnl", "predicted_avg_pnl"]
            ]
            for idx, row in worst.iterrows():
                print(f"  {idx} │ {row['strategy_name']:<30} │ "
                      f"réel={row['realized_pnl']:+.4f}  prédit={row['predicted_avg_pnl']:+.4f}")


# ============================================================================
# WEIGHT GRID RESULT
# ============================================================================

class WeightGridResult:
    """
    Comparaison de plusieurs jeux de poids de scoring.

    Stocke un ``BacktestResults`` par jeu de poids et fournit des
    méthodes pour comparer les performances, identifier les meilleurs
    poids et exporter un tableau synthétique.
    """

    def __init__(
        self,
        all_results: List[BacktestResults],
        weight_grid: List[Dict[str, float]],
    ):
        self.all_results = all_results
        self.weight_grid = weight_grid

    # -----------------------------------------------------------------
    # Tableau de comparaison
    # -----------------------------------------------------------------

    def to_comparison_dataframe(self) -> pd.DataFrame:
        """
        Construit un DataFrame avec une ligne par jeu de poids.

        Colonnes : poids (en str), n_trades, hit_rate, sharpe_ratio,
        total_pnl, avg_pnl, max_drawdown, prediction_correlation.
        """
        rows: List[Dict[str, Any]] = []

        for weights, result in zip(self.weight_grid, self.all_results):
            m = result.summary_metrics()
            row: Dict[str, Any] = {
                "weights": str(weights),
                "n_trades": m.get("n_trades", 0),
                "hit_rate": m.get("hit_rate", 0.0),
                "sharpe_ratio": m.get("sharpe_ratio", 0.0),
                "total_pnl": m.get("total_pnl", 0.0),
                "avg_pnl": m.get("avg_pnl", 0.0),
                "max_drawdown": m.get("max_drawdown", 0.0),
                "prediction_correlation": m.get("prediction_correlation", np.nan),
            }
            rows.append(row)

        return pd.DataFrame(rows)

    # -----------------------------------------------------------------
    # Meilleur jeu de poids
    # -----------------------------------------------------------------

    def best_weights(
        self,
        criterion: str = "sharpe_ratio",
    ) -> Dict[str, Any]:
        """
        Retourne le jeu de poids qui maximise un critère donné.

        Args:
            criterion: Colonne du DataFrame de comparaison à maximiser.
                       Défaut: ``sharpe_ratio``.

        Returns:
            Dict avec "weights", "index", et la valeur du critère.
        """
        df = self.to_comparison_dataframe()
        if df.empty:
            return {"weights": {}, "index": -1, criterion: np.nan}

        best_idx = int(df[criterion].idxmax())
        return {
            "weights": self.weight_grid[best_idx],
            "index": best_idx,
            criterion: df.loc[best_idx, criterion],
        }

    # -----------------------------------------------------------------
    # Affichage
    # -----------------------------------------------------------------

    def print_comparison(self) -> None:
        """Affiche un tableau comparatif lisible."""
        df = self.to_comparison_dataframe()
        if df.empty:
            print("\n  Aucun résultat à comparer.")
            return

        print("\n" + "=" * 90)
        print("  COMPARAISON DES JEUX DE POIDS")
        print("=" * 90)

        # En-tête
        print(f"  {'#':<3} {'Hit%':>6} {'Sharpe':>8} {'P&L':>10} "
              f"{'AvgP&L':>10} {'MaxDD':>10} {'Corr':>6} {'Trades':>6}")
        print("  " + "─" * 84)

        for i, row in df.iterrows():
            corr_str = (f"{row['prediction_correlation']:.3f}"
                        if not np.isnan(row['prediction_correlation']) else "  n/a")
            print(f"  {i:<3} {row['hit_rate']:>5.0%} "
                  f"{row['sharpe_ratio']:>8.3f} "
                  f"{row['total_pnl']:>+10.4f} "
                  f"{row['avg_pnl']:>+10.4f} "
                  f"{row['max_drawdown']:>10.4f} "
                  f"{corr_str:>6} "
                  f"{int(row['n_trades']):>6}")

        # Best
        best = self.best_weights("sharpe_ratio")
        bi = best["index"]
        print("  " + "─" * 84)
        print(f"  ★ Meilleur Sharpe : jeu #{bi}  "
              f"(Sharpe={best['sharpe_ratio']:.3f})")
        print(f"    Poids : {self.weight_grid[bi]}")
        print("=" * 90)

    # -----------------------------------------------------------------
    # Export
    # -----------------------------------------------------------------

    def save_comparison_csv(self, path: str) -> None:
        """Exporte le tableau de comparaison en CSV."""
        df = self.to_comparison_dataframe()
        df.to_csv(path, index=True)
        print(f"  Comparaison sauvegardée → {path}")
