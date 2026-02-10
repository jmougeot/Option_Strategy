"""
Density Analysis & Visualization
==================================
Analyse et visualisation de la distribution de probabilité implicite
extraite des prix d'options SFR.

Fournit:
- Évolution temporelle de la densité 
- Comparaison entre dates
- Export des métriques en DataFrame
- Graphiques de diagnostic
"""

from datetime import date
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.backtesting.config import SFRConfig
from src.backtesting.distrib_proba.implied_distribution import ImpliedDistribution


class DensityAnalyzer:
    """
    Analyse la distribution de probabilité implicite extraite des options.

    Usage:
        analyzer = DensityAnalyzer(config, implied_dist)
        df_moments = analyzer.moments_timeseries()
        analyzer.plot_density_evolution()
    """

    def __init__(self, config: SFRConfig, implied_dist: ImpliedDistribution):
        self.config = config
        self.implied_dist = implied_dist

    # -----------------------------------------------------------------
    # Séries temporelles des moments
    # -----------------------------------------------------------------

    def moments_timeseries(self) -> pd.DataFrame:
        """
        Construit une série temporelle des moments de la distribution.

        Returns:
            DataFrame avec colonnes: date, mean, std, skewness, kurtosis
        """
        records = []
        for d in self.implied_dist.get_available_dates():
            moments = self.implied_dist.get_moments(d)
            if moments is not None:
                records.append({"date": d, **moments})

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        df.set_index("date", inplace=True)
        return df

    def quantiles_timeseries(
        self,
        quantiles: List[float] = [0.05, 0.25, 0.50, 0.75, 0.95],
    ) -> pd.DataFrame:
        """
        Construit une série temporelle des quantiles.

        Returns:
            DataFrame avec colonnes: date, q05, q25, q50, q75, q95
        """
        records = []
        for d in self.implied_dist.get_available_dates():
            q = self.implied_dist.get_quantiles(d, quantiles)
            if q is not None:
                row: Dict[str, object] = {"date": d}
                for qval, xval in q.items():
                    row[f"q{int(qval*100):02d}"] = xval
                records.append(row)

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        df.set_index("date", inplace=True)
        return df

    # -----------------------------------------------------------------
    # Densité matricielle (heatmap)
    # -----------------------------------------------------------------

    def density_matrix(self) -> Tuple[np.ndarray, List[date], np.ndarray]:
        """
        Construit la matrice (n_dates × n_prix) des densités.

        Returns:
            (matrix, dates, price_grid)
        """
        dates = self.implied_dist.get_available_dates()
        grid = self.implied_dist.price_grid
        n_dates = len(dates)
        n_prices = len(grid)

        matrix = np.zeros((n_dates, n_prices))
        for i, d in enumerate(dates):
            q_T = self.implied_dist.get_density(d)
            if q_T is not None:
                matrix[i, :] = q_T

        return matrix, dates, grid

    # -----------------------------------------------------------------
    # Visualisation (matplotlib)
    # -----------------------------------------------------------------

    def plot_density_at_date(
        self,
        target_date: date,
        ax=None,
        title: Optional[str] = None,
        show_moments: bool = True,
    ):
        """
        Trace la densité implicite pour une date donnée.

        Args:
            target_date: Date cible
            ax: Axes matplotlib (crée une figure si None)
            title: Titre personnalisé
            show_moments: Afficher les moments sur le graphique
        """
        import matplotlib.pyplot as plt

        q_T = self.implied_dist.get_density(target_date)
        if q_T is None:
            print(f"Pas de densité disponible pour {target_date}")
            return

        if ax is None:
            fig, ax = plt.subplots(figsize=(12, 6))

        x = self.implied_dist.price_grid
        ax.plot(x, q_T, "b-", linewidth=2, label="Densité implicite")
        ax.fill_between(x, q_T, alpha=0.2, color="blue")

        # Moments
        if show_moments:
            moments = self.implied_dist.get_moments(target_date)
            if moments:
                ax.axvline(moments["mean"], color="red", linestyle="--",
                           label=f"Moyenne: {moments['mean']:.3f}")
                ax.axvline(moments["mean"] - moments["std"], color="orange",
                           linestyle=":", alpha=0.7, label=f"±1σ: {moments['std']:.3f}")
                ax.axvline(moments["mean"] + moments["std"], color="orange",
                           linestyle=":", alpha=0.7)

        ax.set_xlabel("Prix du sous-jacent (SOFR Future)")
        ax.set_ylabel("Densité de probabilité")
        ax.set_title(title or f"Distribution implicite — {target_date}")
        ax.legend()
        ax.grid(True, alpha=0.3)

        return ax

    def plot_density_evolution(
        self,
        dates: Optional[List[date]] = None,
        n_dates: int = 10,
        figsize: Tuple[int, int] = (14, 8),
    ):
        """
        Trace l'évolution de la densité sur plusieurs dates.

        Args:
            dates: Dates spécifiques (ou None pour échantillonner)
            n_dates: Nombre de dates si dates=None
            figsize: Taille de la figure
        """
        import matplotlib.pyplot as plt
        import matplotlib.cm as cm
        viridis = cm.get_cmap("viridis")

        if dates is None:
            all_dates = self.implied_dist.get_available_dates()
            if len(all_dates) <= n_dates:
                dates = all_dates
            else:
                step = len(all_dates) // n_dates
                dates = all_dates[::step][:n_dates]

        fig, ax = plt.subplots(figsize=figsize)
        colors = viridis(np.linspace(0, 1, len(dates)))

        x = self.implied_dist.price_grid
        for d, color in zip(dates, colors):
            q_T = self.implied_dist.get_density(d)
            if q_T is not None:
                ax.plot(x, q_T, color=color, linewidth=1.5, label=str(d))

        ax.set_xlabel("Prix du sous-jacent (SOFR Future)")
        ax.set_ylabel("Densité de probabilité")
        ax.set_title("Évolution de la distribution implicite SFR")
        ax.legend(fontsize=8, loc="upper left", bbox_to_anchor=(1.02, 1))
        ax.grid(True, alpha=0.3)
        plt.tight_layout()

        return fig, ax

    def plot_moments_evolution(self, figsize: Tuple[int, int] = (14, 10)):
        """
        Trace l'évolution des moments de la distribution dans le temps.
        """
        import matplotlib.pyplot as plt

        df_moments = self.moments_timeseries()
        if df_moments.empty:
            print("Pas de moments disponibles")
            return

        fig, axes = plt.subplots(2, 2, figsize=figsize, sharex=True)

        # Moyenne
        axes[0, 0].plot(df_moments.index, df_moments["mean"], "b-", linewidth=1.5)
        axes[0, 0].set_title("Moyenne (Expected SOFR)")
        axes[0, 0].set_ylabel("Prix")
        axes[0, 0].grid(True, alpha=0.3)

        # Écart-type
        axes[0, 1].plot(df_moments.index, df_moments["std"], "r-", linewidth=1.5)
        axes[0, 1].set_title("Écart-type (Incertitude)")
        axes[0, 1].set_ylabel("σ")
        axes[0, 1].grid(True, alpha=0.3)

        # Skewness
        axes[1, 0].plot(df_moments.index, df_moments["skewness"], "g-", linewidth=1.5)
        axes[1, 0].axhline(0, color="gray", linestyle="--", alpha=0.5)
        axes[1, 0].set_title("Asymétrie (Skewness)")
        axes[1, 0].set_ylabel("Skew")
        axes[1, 0].grid(True, alpha=0.3)

        # Kurtosis
        axes[1, 1].plot(df_moments.index, df_moments["kurtosis"], "m-", linewidth=1.5)
        axes[1, 1].axhline(0, color="gray", linestyle="--", alpha=0.5)
        axes[1, 1].set_title("Kurtosis (Queue épaisse)")
        axes[1, 1].set_ylabel("Kurt (excess)")
        axes[1, 1].grid(True, alpha=0.3)

        for ax in axes.flat:
            ax.tick_params(axis="x", rotation=45)

        fig.suptitle("Évolution des moments — Distribution implicite SFR",
                     fontsize=14, fontweight="bold")
        plt.tight_layout()

        return fig, axes

    def plot_heatmap(self, figsize: Tuple[int, int] = (16, 8)):
        """
        Trace une heatmap de la densité (dates × prix).
        """
        import matplotlib.pyplot as plt

        matrix, dates, grid = self.density_matrix()
        if matrix.size == 0:
            print("Pas de données pour la heatmap")
            return

        fig, ax = plt.subplots(figsize=figsize)
        extent = (float(grid[0]), float(grid[-1]), 0.0, float(len(dates) - 1))

        im = ax.imshow(
            matrix, aspect="auto", origin="lower",
            extent=extent, cmap="hot", interpolation="bilinear"
        )

        # Y-axis labels (dates)
        n_labels = min(10, len(dates))
        step = max(1, len(dates) // n_labels)
        y_ticks = list(range(0, len(dates), step))
        y_labels = [str(dates[i]) for i in y_ticks]
        ax.set_yticks(y_ticks)
        ax.set_yticklabels(y_labels, fontsize=8)

        ax.set_xlabel("Prix du sous-jacent")
        ax.set_ylabel("Date")
        ax.set_title("Heatmap — Densité implicite SFR")

        plt.colorbar(im, ax=ax, label="Densité")
        plt.tight_layout()

        return fig, ax

    # -----------------------------------------------------------------
    # Export
    # -----------------------------------------------------------------

    def export_summary(self) -> pd.DataFrame:
        """
        Exporte un résumé complet: moments + quantiles pour chaque date.
        """
        df_m = self.moments_timeseries()
        df_q = self.quantiles_timeseries()

        if df_m.empty and df_q.empty:
            return pd.DataFrame()

        if df_m.empty:
            return df_q
        if df_q.empty:
            return df_m

        return df_m.join(df_q, how="outer")
