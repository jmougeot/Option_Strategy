"""
Backtesting Pipeline — SFR Options
=====================================
Point d'entrée principal du module de backtesting.

Deux modes :
  A) **Distribution** : analyse de la densité implicite (Breeden-Litzenberger)
  B) **Stratégie**    : backtesting de stratégies d'options générées/scorées

Usage :
    # Mode distribution (densité implicite)
    python -m backtesting.main distribution --offline data.csv

    # Mode stratégie (backtesting complet)
    python -m backtesting.main strategy --offline data.csv --freq 5 --max-legs 4

    # Raccourci (défaut = stratégie)
    python -m backtesting.main --offline data.csv
"""

import argparse
from pathlib import Path
from typing import Optional

from src.backtesting.config import SFRConfig, DEFAULT_CONFIG
from src.backtesting.bloomberg.ticker_builder import SFRTickerBuilder
from src.backtesting.bloomberg.bdh_fetcher import BDHFetcher
from src.backtesting.distrib_proba.implied_distribution import ImpliedDistribution
from src.backtesting.distrib_proba.density_analysis import DensityAnalyzer


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
# MODE STRATÉGIE — Backtesting via OptionStrategyGeneratorV2
# ============================================================================

def run_strategy_backtest(args):
    """Lance le backtesting de stratégies d'options."""
    from src.backtesting.strategy.backtest_engine import BacktestEngine, BacktestConfig
    from myproject.app.data_types import FilterData

    sfr = SFRConfig(
        strike_min=args.strike_min,
        strike_max=args.strike_max,
        strike_step=args.strike_step,
    )

    # Filtre par défaut (peu restrictif)
    filt = FilterData(
        max_loss_left=args.max_loss,
        max_loss_right=args.max_loss,
        max_premium=999.0,
        ouvert_gauche=99,
        ouvert_droite=99,
        min_premium_sell=0.0,
        filter_type=False,
        strategies_include=None,
        delta_min=-10.0,
        delta_max=10.0,
        limit_left=0.0,
        limit_right=0.0,
    )

    # Scoring par défaut
    weights = {"average_pnl": 1.0}

    bt_config = BacktestConfig(
        sfr_config=sfr,
        filter=filt,
        scoring_weights=weights,
        max_legs=args.max_legs,
        top_n=args.top_n,
        select_top_k=args.top_k,
        entry_frequency_days=args.freq,
        min_days_before_expiry=args.min_dte,
        smooth_sigma=args.smooth,
    )

    engine = BacktestEngine(bt_config)

    if getattr(args, "grid", False):
        # Mode grid search — compare plusieurs jeux de poids
        grid_result = engine.run_weight_grid(
            csv_path=args.offline,
            save_csv=args.save,
            verbose=True,
        )
        if args.output:
            grid_result.save_comparison_csv(args.output)
        return grid_result

    # Mode normal — un seul jeu de poids
    results = engine.run(
        csv_path=args.offline,
        save_csv=args.save,
        verbose=True,
    )

    # Export CSV si demandé
    if args.output:
        results.save_to_csv(args.output)

    return results


# ============================================================================
# POINT D'ENTRÉE CLI
# ============================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Backtesting SFR — Distribution implicite & Stratégies"
    )
    subparsers = parser.add_subparsers(dest="mode", help="Mode de backtesting")

    # ---- Paramètres communs ----
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--offline", type=str, default=None,
        help="Chemin du CSV pour mode offline (sans Bloomberg)")
    common.add_argument(
        "--save", type=str, default=None,
        help="Chemin pour sauvegarder les données Bloomberg en CSV")
    common.add_argument(
        "--strike-min", type=float, default=95.0,
        help="Strike minimum (défaut: 95.0)")
    common.add_argument(
        "--strike-max", type=float, default=97.0,
        help="Strike maximum (défaut: 97.0)")
    common.add_argument(
        "--strike-step", type=float, default=0.125,
        help="Pas des strikes (défaut: 0.125)")
    common.add_argument(
        "--smooth", type=float, default=0.5,
        help="Paramètre de lissage gaussien (défaut: 0.5)")

    # ---- Sous-commande : distribution ----
    dist_parser = subparsers.add_parser(
        "distribution", parents=[common],
        help="Analyse de la distribution de probabilité implicite")
    dist_parser.add_argument(
        "--no-plots", action="store_true",
        help="Ne pas afficher les graphiques")

    # ---- Sous-commande : strategy ----
    strat_parser = subparsers.add_parser(
        "strategy", parents=[common],
        help="Backtesting de stratégies d'options")
    strat_parser.add_argument(
        "--max-legs", type=int, default=4,
        help="Nombre max de legs (défaut: 4)")
    strat_parser.add_argument(
        "--top-n", type=int, default=10,
        help="Nombre de stratégies à générer par date (défaut: 10)")
    strat_parser.add_argument(
        "--top-k", type=int, default=1,
        help="Nombre de stratégies à suivre par date (défaut: 1)")
    strat_parser.add_argument(
        "--freq", type=int, default=5,
        help="Fréquence d'entrée en jours (défaut: 5)")
    strat_parser.add_argument(
        "--min-dte", type=int, default=5,
        help="Jours min avant expiry pour entrer (défaut: 5)")
    strat_parser.add_argument(
        "--max-loss", type=float, default=-999.0,
        help="Perte max autorisée (défaut: -999 = pas de filtre)")
    strat_parser.add_argument(
        "--output", type=str, default=None,
        help="Chemin CSV pour exporter les résultats")
    strat_parser.add_argument(
        "--grid", action="store_true",
        help="Lancer un grid search sur les poids de scoring")

    return parser.parse_args()


def main():
    args = parse_args()

    # Défaut : mode strategy si aucun sous-commande
    if args.mode is None:
        args.mode = "strategy"
        # Ajouter les attributs manquants avec défauts
        for attr, val in [
            ("max_legs", 4), ("top_n", 10), ("top_k", 1),
            ("freq", 5), ("min_dte", 5), ("max_loss", -999.0),
            ("output", None), ("no_plots", False), ("grid", False),
        ]:
            if not hasattr(args, attr):
                setattr(args, attr, val)

    if args.mode == "distribution":
        # Pipeline d'analyse de densité (existant)
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

    elif args.mode == "strategy":
        run_strategy_backtest(args)

    else:
        print(f"Mode inconnu: {args.mode}")


if __name__ == "__main__":
    main()
