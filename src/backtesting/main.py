"""
Backtesting Pipeline — SFR Implied Distribution
=================================================
Point d'entrée principal du module de backtesting.

Ce pipeline:
1. Construit les tickers Bloomberg pour les options SFR (calls + puts, strikes 95-97)
2. Récupère l'historique des prix via BDH (30/07/2024 → 13/03/2025)
3. Extrait la distribution de probabilité implicite (Breeden-Litzenberger)
4. Analyse et visualise l'évolution de la densité

Usage:
    python -m backtesting.main                      # Mode Bloomberg live
    python -m backtesting.main --offline data.csv    # Mode offline (CSV)
    python -m backtesting.main --save output.csv     # Sauvegarder les données

Ticker Bloomberg SFR (SOFR Futures Options):
    =@BDH("SFRH5C 96.00 Comdty", "PX_LAST", "30/07/2024", "13/03/2025")
"""

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Optional

from backtesting.config import SFRConfig, DEFAULT_CONFIG
from backtesting.bloomberg.ticker_builder import SFRTickerBuilder
from backtesting.bloomberg.bdh_fetcher import BDHFetcher
from backtesting.distrib_proba.implied_distribution import ImpliedDistribution
from backtesting.distrib_proba.density_analysis import DensityAnalyzer


# ============================================================================
# PIPELINE
# ============================================================================

class BacktestingPipeline:
    """
    Pipeline de backtesting complet : Bloomberg → Distribution implicite.

    Attributes:
        config: Configuration SFR
        builder: Constructeur de tickers
        fetcher: Fetcher BDH Bloomberg
        implied_dist: Calculateur de distribution implicite
        analyzer: Analyseur de densité
    """

    def __init__(self, config: Optional[SFRConfig] = None):
        self.config = config or DEFAULT_CONFIG
        self.builder: Optional[SFRTickerBuilder] = None
        self.fetcher: Optional[BDHFetcher] = None
        self.implied_dist: Optional[ImpliedDistribution] = None
        self.analyzer: Optional[DensityAnalyzer] = None

    # -----------------------------------------------------------------
    # Étape 1 : Construction des tickers
    # -----------------------------------------------------------------

    def build_tickers(self) -> "BacktestingPipeline":
        """Construit tous les tickers SFR (calls + puts)."""
        print("=" * 60)
        print("ÉTAPE 1 — Construction des tickers")
        print("=" * 60)

        self.builder = SFRTickerBuilder(self.config).build()

        # Afficher un échantillon
        print(f"\n  Sous-jacent: {self.builder.underlying_ticker}")
        print(f"  Exemple call: {self.builder.call_tickers[0]}")
        print(f"  Exemple put:  {self.builder.put_tickers[0]}")
        print(f"  Strikes: {self.config.strikes[:3]} ... {self.config.strikes[-3:]}")

        return self

    # -----------------------------------------------------------------
    # Étape 2 : Fetch des données Bloomberg
    # -----------------------------------------------------------------

    def fetch_data(self, csv_path: Optional[str] = None) -> "BacktestingPipeline":
        """
        Récupère les données historiques.

        Args:
            csv_path: Si fourni, charge depuis un CSV (mode offline).
                      Sinon, fetch depuis Bloomberg.
        """
        if self.builder is None:
            self.build_tickers()

        print("\n" + "=" * 60)
        print("ÉTAPE 2 — Récupération des données")
        print("=" * 60)

        assert self.builder is not None, "Builder non initialisé. Appeler build_tickers()."

        if csv_path and Path(csv_path).exists():
            print(f"  Mode OFFLINE — chargement depuis {csv_path}")
            self.fetcher = BDHFetcher.load_from_csv(csv_path, self.config, self.builder)
        else:
            print(f"  Mode BLOOMBERG — BDH {self.config.start_date} → {self.config.end_date}")
            self.fetcher = BDHFetcher(self.config, self.builder)
            self.fetcher.fetch_all()

        # Résumé des données
        df = self.fetcher.to_dataframe()
        if not df.empty:
            print(f"\n  DataFrame: {df.shape[0]} dates × {df.shape[1]} tickers")
            print(f"  Période: {df.index[0].date()} → {df.index[-1].date()}")
            print(f"  Valeurs non-nulles: {df.notna().sum().sum()}")
        else:
            print("  ATTENTION: Aucune donnée récupérée!")

        return self

    # -----------------------------------------------------------------
    # Étape 3 : Distribution implicite
    # -----------------------------------------------------------------

    def compute_distribution(
        self,
        smooth_sigma: float = 0.5,
    ) -> "BacktestingPipeline":
        """
        Calcule la distribution de probabilité implicite pour chaque date.

        Args:
            smooth_sigma: Paramètre de lissage gaussien
        """
        if self.fetcher is None:
            raise RuntimeError("Données non chargées. Appeler fetch_data() d'abord.")

        print("\n" + "=" * 60)
        print("ÉTAPE 3 — Distribution de probabilité implicite")
        print("=" * 60)

        self.implied_dist = ImpliedDistribution(self.config, self.fetcher)
        densities = self.implied_dist.compute_all_dates(smooth_sigma=smooth_sigma)

        # Résumé
        if densities:
            first_date = min(densities.keys())
            last_date = max(densities.keys())
            moments = self.implied_dist.get_moments(last_date)

            print(f"\n  Densités calculées: {len(densities)} dates")
            print(f"  Période: {first_date} → {last_date}")
            if moments:
                print(f"  Dernière date ({last_date}):")
                print(f"    Moyenne:   {moments['mean']:.4f}")
                print(f"    Écart-type: {moments['std']:.4f}")
                print(f"    Skewness:  {moments['skewness']:.4f}")
                print(f"    Kurtosis:  {moments['kurtosis']:.4f}")
        else:
            print("  ATTENTION: Aucune densité calculée!")

        return self

    # -----------------------------------------------------------------
    # Étape 4 : Analyse
    # -----------------------------------------------------------------

    def analyze(self, show_plots: bool = True) -> "BacktestingPipeline":
        """
        Analyse la distribution et génère les visualisations.

        Args:
            show_plots: Si True, affiche les graphiques matplotlib
        """
        if self.implied_dist is None:
            raise RuntimeError("Distribution non calculée. Appeler compute_distribution().")

        print("\n" + "=" * 60)
        print("ÉTAPE 4 — Analyse et visualisation")
        print("=" * 60)

        self.analyzer = DensityAnalyzer(self.config, self.implied_dist)

        # Résumé
        df_summary = self.analyzer.export_summary()
        if not df_summary.empty:
            print(f"\n  Résumé exporté: {df_summary.shape}")
            print(df_summary.tail())

        if show_plots:
            try:
                import matplotlib.pyplot as plt

                # Plot 1 : Densité à la dernière date
                dates = self.implied_dist.get_available_dates()
                if dates:
                    self.analyzer.plot_density_at_date(dates[-1])

                # Plot 2 : Évolution de la densité
                self.analyzer.plot_density_evolution()

                # Plot 3 : Évolution des moments
                self.analyzer.plot_moments_evolution()

                # Plot 4 : Heatmap
                self.analyzer.plot_heatmap()

                plt.show()
            except ImportError:
                print("  matplotlib non disponible, pas de graphiques")

        return self

    # -----------------------------------------------------------------
    # Pipeline complet
    # -----------------------------------------------------------------

    def run(
        self,
        csv_path: Optional[str] = None,
        save_path: Optional[str] = None,
        smooth_sigma: float = 0.5,
        show_plots: bool = True,
    ) -> "BacktestingPipeline":
        """
        Exécute le pipeline complet.

        Args:
            csv_path: CSV à charger (mode offline)
            save_path: Chemin pour sauvegarder les données Bloomberg
            smooth_sigma: Lissage de la densité
            show_plots: Afficher les graphiques

        Returns:
            self (pour accéder aux résultats)
        """
        print("╔" + "═" * 58 + "╗")
        print("║  BACKTESTING SFR — Distribution de probabilité implicite  ║")
        print("╚" + "═" * 58 + "╝")
        print(f"\n  Sous-jacent: SFR (SOFR Futures)")
        print(f"  Expiration:  {self.config.expiry_month}{self.config.expiry_year} "
              f"({self.config.full_year})")
        print(f"  Strikes:     {self.config.strike_min} → {self.config.strike_max} "
              f"(step={self.config.strike_step})")
        print(f"  Période:     {self.config.start_date} → {self.config.end_date}")
        print()

        # Pipeline
        self.build_tickers()
        self.fetch_data(csv_path=csv_path)

        # Sauvegarder si demandé
        if save_path and self.fetcher:
            self.fetcher.save_to_csv(save_path)

        self.compute_distribution(smooth_sigma=smooth_sigma)
        self.analyze(show_plots=show_plots)

        print("\n" + "=" * 60)
        print("PIPELINE TERMINÉ")
        print("=" * 60)

        return self


# ============================================================================
# POINT D'ENTRÉE CLI
# ============================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Backtesting SFR — Distribution de probabilité implicite"
    )
    parser.add_argument(
        "--offline", type=str, default=None,
        help="Chemin du CSV pour mode offline (sans Bloomberg)"
    )
    parser.add_argument(
        "--save", type=str, default=None,
        help="Chemin pour sauvegarder les données Bloomberg en CSV"
    )
    parser.add_argument(
        "--strike-min", type=float, default=95.0,
        help="Strike minimum (défaut: 95.0)"
    )
    parser.add_argument(
        "--strike-max", type=float, default=97.0,
        help="Strike maximum (défaut: 97.0)"
    )
    parser.add_argument(
        "--strike-step", type=float, default=0.125,
        help="Pas des strikes (défaut: 0.125)"
    )
    parser.add_argument(
        "--smooth", type=float, default=0.5,
        help="Paramètre de lissage gaussien (défaut: 0.5)"
    )
    parser.add_argument(
        "--no-plots", action="store_true",
        help="Ne pas afficher les graphiques"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    config = SFRConfig(
        strike_min=args.strike_min,
        strike_max=args.strike_max,
        strike_step=args.strike_step,
    )

    pipeline = BacktestingPipeline(config)
    pipeline.run(
        csv_path=args.offline,
        save_path=args.save,
        smooth_sigma=args.smooth,
        show_plots=not args.no_plots,
    )


if __name__ == "__main__":
    main()
