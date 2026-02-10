"""
Backtest Engine
================
Moteur principal du backtesting de stratégies d'options.

Deux usages principaux :

A) **Single-run** : backtest avec un jeu de poids fixe
   → ``engine.run()``

B) **Grid-search** : itère sur une grille de poids de scoring,
   compare les résultats, et identifie les meilleurs poids.
   → ``engine.run_weight_grid()``

Optimisations de coût :
- Les données BDH et les distributions sont chargées **une seule fois**
- Les ``Option`` sont **cachées** par date (pas de reconstruction si
  seuls les poids changent)
- Le mark-to-market est **optionnel** (``compute_mtm=False`` par défaut)
- La fréquence d'entrée est paramétrable (défaut : 10 jours ouverts)
"""

import sys
import traceback
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# --- Assurer que myproject est importable ---
_src_dir = str(Path(__file__).resolve().parent.parent.parent)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from src.backtesting.config import SFRConfig
from src.backtesting.bloomberg.bdh_fetcher import BDHFetcher
from src.backtesting.bloomberg.ticker_builder import SFRTickerBuilder
from src.backtesting.distrib_proba.implied_distribution import ImpliedDistribution
from src.backtesting.strategy.option_builder import OptionBuilder
from src.backtesting.strategy.results import BacktestResults, TradeRecord, WeightGridResult
from myproject.app.data_types import FilterData
from myproject.option.option_class import Option
from myproject.strategy.strategy_class import StrategyComparison

# ============================================================================
# SCORING WEIGHT PRESETS (grilles prédéfinies)
# ============================================================================

DEFAULT_WEIGHT_GRID: List[Dict[str, float]] = [
    # 1) Pure average PnL
    {"average_pnl": 1.0},
    # 2) Average PnL + tail risk
    {"average_pnl": 0.7, "max_loss": 0.3},
    # 3) Average PnL + intra-life
    {"average_pnl": 0.6, "avg_intra_life_pnl": 0.4},
    # 4) Balanced
    {"average_pnl": 0.5, "max_loss": 0.2, "avg_intra_life_pnl": 0.3},
    # 5) Leverage-focused
    {"avg_pnl_levrage": 0.6, "average_pnl": 0.4},
    # 6) Premium income
    {"premium": 0.5, "average_pnl": 0.3, "max_loss": 0.2},
    # 7) Roll + average PnL
    {"roll_quarterly": 0.4, "average_pnl": 0.6},
    # 8) Conservative
    {"average_pnl": 0.4, "max_loss": 0.4, "sigma_pnl": 0.2},
]


# ============================================================================
# CONFIGURATION
# ============================================================================

def _default_filter() -> FilterData:
    """Filtre par défaut : peu restrictif pour le backtesting."""
    return FilterData(
        max_loss_left=-999.0,
        max_loss_right=-999.0,
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


def _default_scoring() -> Dict[str, float]:
    """Scoring par défaut : 100 % average_pnl."""
    return {"average_pnl": 1.0}


@dataclass
class BacktestConfig:
    """
    Configuration complète du backtesting.

    Attributes:
        sfr_config: Configuration SFR (strikes, dates, etc.)
        filter: Filtres de stratégies
        scoring_weights: Poids de scoring (clé → poids normalisé)
        max_legs: Nombre max de legs par stratégie
        top_n: Nombre de stratégies à générer par date (C++)
        select_top_k: Nombre de stratégies à suivre par date
        entry_frequency_days: Fréquence d'entrée en jours (défaut 10)
        min_days_before_expiry: Pas d'entrée trop proche de l'expiry
        smooth_sigma: Lissage densité Breeden-Litzenberger
        compute_mtm: Calculer le mark-to-market quotidien (coûteux)
    """
    sfr_config: SFRConfig = field(default_factory=SFRConfig)

    # Stratégies
    filter: FilterData = field(default_factory=_default_filter)
    scoring_weights: Dict[str, float] = field(default_factory=_default_scoring)
    max_legs: int = 4
    top_n: int = 10
    select_top_k: int = 1

    # Timing — défaut 10 jours (≈ 2 semaines ouverts)
    entry_frequency_days: int = 10
    min_days_before_expiry: int = 5

    # Distribution
    smooth_sigma: float = 0.5

    # Performance
    compute_mtm: bool = False


# ============================================================================
# ENGINE
# ============================================================================

class BacktestEngine:
    """
    Moteur de backtesting pour stratégies d'options SFR.

    **Optimisations** :
    - Données BDH et distributions chargées une seule fois
    - Cache d'options par date (évite de reconstruire quand seuls
      les poids changent pour le grid-search)
    - MtM optionnel (``compute_mtm=False`` par défaut)
    - Fréquence d'entrée par défaut : 10 jours
    """

    def __init__(self, config: BacktestConfig):
        self.config = config
        self.builder: Optional[SFRTickerBuilder] = None
        self.fetcher: Optional[BDHFetcher] = None
        self.implied_dist: Optional[ImpliedDistribution] = None
        self.option_builder: Optional[OptionBuilder] = None

        # Cache : {date → List[Option]}
        self._options_cache: Dict[date, List[Option]] = {}
        self._data_initialized: bool = False

    # -----------------------------------------------------------------
    # Initialisation (une seule fois)
    # -----------------------------------------------------------------

    def _init_data(self, csv_path: Optional[str] = None):
        """
        Charge les données BDH + distributions.
        Ne fait rien si déjà initialisé.
        """
        if self._data_initialized:
            return

        sfr = self.config.sfr_config

        # 1. Tickers Bloomberg
        self.builder = SFRTickerBuilder(sfr).build()

        # 2. Données historiques
        if csv_path and Path(csv_path).exists():
            self.fetcher = BDHFetcher.load_from_csv(csv_path, sfr, self.builder)
        else:
            self.fetcher = BDHFetcher(sfr, self.builder)
            self.fetcher.fetch_all()

        # 3. Distribution implicite
        self.implied_dist = ImpliedDistribution(sfr, self.fetcher)
        self.implied_dist.compute_all_dates(smooth_sigma=self.config.smooth_sigma)

        # 4. Option builder
        self.option_builder = OptionBuilder(sfr, self.fetcher, self.implied_dist)

        self._data_initialized = True

    # -----------------------------------------------------------------
    # Cache d'options
    # -----------------------------------------------------------------

    def _get_options_at_date(self, target_date: date) -> List[Option]:
        """
        Retourne les options pour une date, avec cache.

        La construction des Option (vol implicite, Greeks, surfaces
        de P&L) est le calcul le plus coûteux. On le fait une seule
        fois par date et on réutilise pour chaque jeu de poids.
        """
        if target_date in self._options_cache:
            return self._options_cache[target_date]

        assert self.option_builder is not None
        options = self.option_builder.build_at_date(target_date)
        self._options_cache[target_date] = options
        return options

    # -----------------------------------------------------------------
    # Sélection des dates d'entrée
    # -----------------------------------------------------------------

    def _get_entry_dates(self) -> List[date]:
        """
        Sélectionne les dates d'entrée.

        Filtre :
        - Espacement >= ``entry_frequency_days``
        - Pas trop proche de l'expiration
        - Au moins 4 options disponibles (sinon pas de stratégie)
        """
        assert self.fetcher is not None
        all_dates = self.fetcher.get_all_dates()
        if not all_dates:
            return []

        freq = self.config.entry_frequency_days
        expiry = self.config.sfr_config.end_date
        cutoff = expiry - timedelta(days=self.config.min_days_before_expiry)

        entries: List[date] = []
        last_entry: Optional[date] = None

        for d in all_dates:
            if d > cutoff:
                break
            if last_entry is None or (d - last_entry).days >= freq:
                entries.append(d)
                last_entry = d

        return entries

    # -----------------------------------------------------------------
    # P&L réalisé (léger — pas de BDH, juste le payoff)
    # -----------------------------------------------------------------

    def _compute_realized_pnl(
        self,
        strategy: StrategyComparison,
    ) -> Dict[str, object]:
        """
        P&L réalisé au payoff intrinsèque à l'expiration.

        pnl_leg = sign × (payoff(S_T, K) - premium)
        """
        assert self.fetcher is not None
        expiry = self.config.sfr_config.end_date
        F_T = self.fetcher.get_underlying_at_date(expiry)

        if F_T is None:
            return {"realized_pnl": float("nan"), "underlying_at_expiry": None}

        total_pnl = 0.0
        for i, opt in enumerate(strategy.all_options):
            sign = float(strategy.signs[i])
            K = opt.strike
            if opt.option_type == "call":
                payoff = max(F_T - K, 0.0)
            else:
                payoff = max(K - F_T, 0.0)
            total_pnl += sign * (payoff - opt.premium)

        return {"realized_pnl": total_pnl, "underlying_at_expiry": F_T}

    # -----------------------------------------------------------------
    # Mark-to-Market (optionnel — coûteux)
    # -----------------------------------------------------------------

    def _compute_mtm_series(
        self,
        strategy: StrategyComparison,
        entry_date: date,
    ) -> Dict[date, float]:
        """MtM quotidien. Ne tourne que si ``compute_mtm=True``."""
        if not self.config.compute_mtm:
            return {}

        assert self.fetcher is not None
        all_dates = self.fetcher.get_all_dates()
        mtm: Dict[date, float] = {}

        for d in all_dates:
            if d < entry_date:
                continue

            prices = self.fetcher.get_prices_at_date(d)
            total_mtm = 0.0
            valid = True

            for i, opt in enumerate(strategy.all_options):
                sign = float(strategy.signs[i])
                ticker = self._find_ticker_for_option(opt)
                if ticker and ticker in prices:
                    total_mtm += sign * (prices[ticker] - opt.premium)
                else:
                    valid = False
                    break

            if valid:
                mtm[d] = total_mtm

        return mtm

    def _find_ticker_for_option(self, opt: Option) -> Optional[str]:
        """Retrouve le ticker Bloomberg dans le builder."""
        if self.builder is None:
            return None
        for ticker, meta in self.builder.metadata.items():
            if (abs(meta.strike - opt.strike) < 1e-6
                    and meta.option_type == opt.option_type):
                return ticker
        return None

    # -----------------------------------------------------------------
    # Run (single weight set)
    # -----------------------------------------------------------------

    def run(
        self,
        csv_path: Optional[str] = None,
        save_csv: Optional[str] = None,
        verbose: bool = True,
    ) -> BacktestResults:
        """
        Backtesting avec un **seul jeu de poids**.

        Pour tester plusieurs jeux de poids, utiliser ``run_weight_grid()``.
        """
        if verbose:
            self._print_header()

        # ---- 1. Init données ----
        if verbose:
            print("\n[1/4] Chargement des données...")
        self._init_data(csv_path)

        if save_csv and self.fetcher:
            self.fetcher.save_to_csv(save_csv)

        # ---- 2. Dates d'entrée ----
        entry_dates = self._get_entry_dates()
        if verbose:
            print(f"\n[2/4] {len(entry_dates)} dates d'entrée sélectionnées "
                  f"(freq={self.config.entry_frequency_days}j, "
                  f"cutoff={self.config.min_days_before_expiry}j avant expiry)")

        if not entry_dates:
            if verbose:
                print("  ⚠ Aucune date d'entrée — vérifiez la config.")
            return BacktestResults(trades=[], config=self.config)

        # ---- 3. Boucle ----
        if verbose:
            print(f"\n[3/4] Backtesting ({len(entry_dates)} dates, "
                  f"poids={self.config.scoring_weights})...")

        trades = self._run_dates(
            entry_dates, self.config.scoring_weights, verbose,
        )

        # ---- 4. Résultats ----
        if verbose:
            print(f"\n\n[4/4] Compilation ({len(trades)} trades)...")

        results = BacktestResults(
            trades=trades, config=self.config,
            scoring_weights=self.config.scoring_weights,
        )

        if verbose:
            results.print_summary()

        return results

    # -----------------------------------------------------------------
    # Grid search sur les poids
    # -----------------------------------------------------------------

    def run_weight_grid(
        self,
        weight_grid: Optional[List[Dict[str, float]]] = None,
        csv_path: Optional[str] = None,
        save_csv: Optional[str] = None,
        verbose: bool = True,
    ) -> WeightGridResult:
        """
        Itère sur plusieurs jeux de poids de scoring.

        Pour chaque jeu de poids :
        - Réutilise les mêmes données (BDH, distributions)
        - Réutilise les Options cachées par date
        - Seule l'étape de scoring/ranking C++ est refaite

        C'est la bonne façon de comparer l'impact des poids
        sur la performance réalisée.

        Args:
            weight_grid: Liste de dicts de poids. Défaut: ``DEFAULT_WEIGHT_GRID``
            csv_path: CSV pour mode offline
            save_csv: Sauvegarder les données BDH
            verbose: Logs de progression

        Returns:
            ``WeightGridResult`` avec tous les résultats comparés
        """
        if weight_grid is None:
            weight_grid = DEFAULT_WEIGHT_GRID

        if verbose:
            self._print_header()
            print(f"\n  MODE GRID SEARCH : {len(weight_grid)} jeux de poids")

        # ---- 1. Init données (une seule fois) ----
        if verbose:
            print("\n[1/3] Chargement des données...")
        self._init_data(csv_path)

        if save_csv and self.fetcher:
            self.fetcher.save_to_csv(save_csv)

        # ---- 2. Dates d'entrée ----
        entry_dates = self._get_entry_dates()
        if verbose:
            print(f"\n[2/3] {len(entry_dates)} dates d'entrée")

        if not entry_dates:
            return WeightGridResult(all_results=[], weight_grid=weight_grid)

        # ---- 3. Pré-construire les options (cache) ----
        if verbose:
            print(f"\n  Pré-construction des options pour {len(entry_dates)} dates...")
        for d in entry_dates:
            self._get_options_at_date(d)
        if verbose:
            cached = sum(len(v) for v in self._options_cache.values())
            print(f"  → {cached} options en cache "
                  f"({len(self._options_cache)} dates)")

        # ---- 4. Itérer sur les poids ----
        all_results: List[BacktestResults] = []

        for w_idx, weights in enumerate(weight_grid):
            if verbose:
                print(f"\n[3/3] Jeu de poids {w_idx + 1}/{len(weight_grid)}: "
                      f"{weights}")

            trades = self._run_dates(entry_dates, weights, verbose=False)

            result = BacktestResults(
                trades=trades, config=self.config,
                scoring_weights=weights,
            )
            all_results.append(result)

            if verbose:
                m = result.summary_metrics()
                nt = m.get("n_trades", 0)
                hr = m.get("hit_rate", 0)
                sr = m.get("sharpe_ratio", 0)
                tp = m.get("total_pnl", 0)
                print(f"  → {nt} trades | hit={hr:.0%} | "
                      f"sharpe={sr:.2f} | P&L={tp:+.4f}")

        grid_result = WeightGridResult(
            all_results=all_results, weight_grid=weight_grid,
        )

        if verbose:
            grid_result.print_comparison()

        return grid_result

    # -----------------------------------------------------------------
    # Boucle interne
    # -----------------------------------------------------------------

    def _run_dates(
        self,
        entry_dates: List[date],
        scoring_weights: Dict[str, float],
        verbose: bool,
    ) -> List[TradeRecord]:
        """Boucle sur les dates d'entrée avec un jeu de poids donné."""
        assert self.fetcher is not None

        trades: List[TradeRecord] = []
        last_cached_date: Optional[date] = None

        for idx, entry_date in enumerate(entry_dates):
            if verbose:
                print(f"\n  [{idx + 1}/{len(entry_dates)}] {entry_date}", end=" ")

            try:
                batch = self._process_entry_date(
                    entry_date, scoring_weights, verbose,
                    _last_cached_date=last_cached_date,
                )
                last_cached_date = entry_date
                trades.extend(batch)
            except Exception as e:
                if verbose:
                    print(f"→ ERREUR: {e}")
                traceback.print_exc()

        return trades

    def _process_entry_date(
        self,
        entry_date: date,
        scoring_weights: Dict[str, float],
        verbose: bool,
        _last_cached_date: Optional[date] = None,
    ) -> List[TradeRecord]:
        """Traite une date d'entrée avec un jeu de poids donné."""
        assert self.fetcher is not None

        # 1. Options (depuis le cache si possible)
        options = self._get_options_at_date(entry_date)
        if len(options) < 2:
            if verbose:
                print(f"→ {len(options)} options (insuffisant)")
            return []

        # 2. Scoring C++ — ne ré-initialise le cache que si la date change
        from myproject.strategy.batch_processor import init_cpp_cache, process_batch_cpp_with_scoring

        if _last_cached_date != entry_date:
            init_cpp_cache(options)

        strategies = process_batch_cpp_with_scoring(
            self.config.max_legs,
            self.config.filter,
            top_n=self.config.top_n,
            custom_weights=scoring_weights,
        )

        if not strategies:
            if verbose:
                print(f"→ {len(options)} opts, 0 strats")
            return []

        # 3. Top-K
        selected = strategies[: self.config.select_top_k]

        # 4. Évaluer
        trades: List[TradeRecord] = []
        for rank, strat in enumerate(selected):
            realized = self._compute_realized_pnl(strat)
            mtm = self._compute_mtm_series(strat, entry_date)

            trade = TradeRecord(
                entry_date=entry_date,
                expiry_date=self.config.sfr_config.end_date,
                strategy_name=strat.strategy_name,
                n_legs=len(strat.all_options),
                entry_premium=strat.premium,
                predicted_avg_pnl=strat.average_pnl or 0.0,
                predicted_score=strat.score,
                realized_pnl=float(str(realized["realized_pnl"])),
                underlying_at_entry=self.fetcher.get_underlying_at_date(entry_date),
                underlying_at_expiry=realized.get("underlying_at_expiry"),  # type: ignore
                rank_at_entry=rank + 1,
                max_profit=strat.max_profit,
                max_loss=strat.max_loss,
                total_delta=strat.total_delta,
                mtm_series=mtm,
                legs_detail=[
                    {
                        "type": opt.option_type,
                        "strike": opt.strike,
                        "premium": opt.premium,
                        "sign": float(strat.signs[i]),
                    }
                    for i, opt in enumerate(strat.all_options)
                ],
            )
            trades.append(trade)

        if verbose and trades:
            best = trades[0]
            print(f"→ {len(options)} opts, {len(strategies)} strats | "
                  f"best='{best.strategy_name}' "
                  f"pred={best.predicted_avg_pnl:+.4f} "
                  f"real={best.realized_pnl:+.4f}")

        return trades

    # -----------------------------------------------------------------
    # Affichage
    # -----------------------------------------------------------------

    def _print_header(self):
        sfr = self.config.sfr_config
        print("╔" + "═" * 58 + "╗")
        print("║  BACKTESTING ENGINE — Strategy Performance               ║")
        print("╚" + "═" * 58 + "╝")
        print(f"\n  Sous-jacent  : {sfr.underlying} "
              f"{sfr.expiry_month}{sfr.expiry_year}")
        print(f"  Strikes      : {sfr.strike_min} → {sfr.strike_max} "
              f"(step={sfr.strike_step})")
        print(f"  Période      : {sfr.start_date} → {sfr.end_date}")
        print(f"  Max legs     : {self.config.max_legs}")
        print(f"  Fréquence    : {self.config.entry_frequency_days}j | "
              f"MtM={'oui' if self.config.compute_mtm else 'non'}")
