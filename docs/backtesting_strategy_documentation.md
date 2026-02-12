# Backtesting Module — Documentation

## Vue d'ensemble

Le module `src/backtesting/` implémente un pipeline complet de backtesting pour des stratégies d'options sur SOFR Futures (SFR). Il combine :

1. **Récupération de données Bloomberg** (BDH) pour les prix historiques
2. **Extraction de la distribution implicite** risque-neutre (Breeden-Litzenberger)
3. **Construction d'objets `Option`** avec vol implicite Bachelier et Greeks
4. **Génération et scoring de stratégies** via le moteur C++ existant (`strategy_metrics_cpp`)
5. **Évaluation du P&L réalisé** et comparaison avec les prédictions
6. **Grid search sur les poids de scoring** pour optimiser le ranking

---

## Architecture des fichiers

```
src/backtesting/
├── main.py                         # Point d'entrée CLI (2 modes : distribution, strategy)
├── config.py                       # SFRConfig — paramètres centralisés
│
├── bloomberg/
│   ├── ticker_builder.py           # Construit les tickers Bloomberg (SFR{M}{Y}{C/P} {K} Comdty)
│   └── bdh_fetcher.py              # Fetch BDH historique (batch 25, CSV offline)
│
├── distrib_proba/
│   ├── implied_distribution.py     # Breeden-Litzenberger (densité risque-neutre)
│   └── density_analysis.py         # Moments, heatmaps, visualisations
│
└── strategy/
    ├── __init__.py                 # Exports du sous-module
    ├── option_builder.py           # BDH → objets Option (IV Bachelier, Greeks, surfaces)
    ├── backtest_engine.py          # Moteur principal (single run + grid search)
    └── results.py                  # TradeRecord, BacktestResults, WeightGridResult
```

---

## Flux de données

```
Bloomberg BDH / CSV offline
        │
        ▼
┌──────────────────┐
│  SFRTickerBuilder │  → tickers calls + puts + sous-jacent
└──────────────────┘
        │
        ▼
┌──────────────────┐
│    BDHFetcher     │  → DataFrame (dates × tickers) + accesseurs typés
└──────────────────┘
        │
        ├────────────────────────────┐
        ▼                            ▼
┌──────────────────┐     ┌──────────────────────┐
│ImpliedDistribution│     │    OptionBuilder      │
│(Breeden-Litzenberg)│     │(IV Bachelier + Greeks)│
└──────────────────┘     └──────────────────────┘
        │                            │
        │  densité/mixture           │  List[Option]
        └────────────┬───────────────┘
                     ▼
        ┌──────────────────────────┐
        │     BacktestEngine       │
        │  (scoring C++ + P&L)     │
        └──────────────────────────┘
                     │
                     ▼
        ┌──────────────────────────┐
        │  BacktestResults /       │
        │  WeightGridResult        │
        └──────────────────────────┘
```

---

## Modules en détail

### 1. `config.py` — `SFRConfig`

Dataclass centralisée pour tous les paramètres du backtesting :

| Champ | Type | Défaut | Description |
|-------|------|--------|-------------|
| `underlying` | `str` | `"SFR"` | Préfixe Bloomberg |
| `suffix` | `str` | `"Comdty"` | Suffixe Bloomberg |
| `expiry_month` | `str` | `"H"` | Code mois (H = Mars) |
| `expiry_year` | `int` | `5` | Année sur 1 chiffre (5 = 2025) |
| `strike_min` | `float` | `95.0` | Strike minimum |
| `strike_max` | `float` | `97.0` | Strike maximum |
| `strike_step` | `float` | `0.125` | Pas (12.5 bps SOFR) |
| `start_date` | `date` | `2024-07-30` | Début historique |
| `end_date` | `date` | `2025-03-13` | Fin historique / expiry |
| `bbg_field` | `str` | `"PX_LAST"` | Champ Bloomberg |
| `risk_free_rate` | `float` | `0.0` | Taux sans risque |
| `price_grid_points` | `int` | `500` | Points de la grille de prix |
| `price_grid_margin` | `float` | `1.0` | Marge autour des strikes |

Propriétés calculées : `strikes`, `start_date_str`, `end_date_str`, `full_year`.

---

### 2. `bloomberg/ticker_builder.py` — `SFRTickerBuilder`

Construit les tickers Bloomberg pour toutes les options calls et puts sur chaque strike.

**Format** : `SFR{MONTH}{YEAR}{C/P} {STRIKE:.2f} Comdty`  
**Exemple** : `SFRH5C 96.00 Comdty` (Call SOFR Mars 2025, strike 96.00)

**Résultat** :
- `builder.call_tickers` : liste des tickers calls
- `builder.put_tickers` : liste des tickers puts
- `builder.all_tickers` : les deux concaténés
- `builder.metadata` : `Dict[str, TickerMeta]` avec strike, type, etc.
- `builder.underlying_ticker` : ex. `"SFRH5 Comdty"`

---

### 3. `bloomberg/bdh_fetcher.py` — `BDHFetcher`

Récupère les séries historiques via `HistoricalDataRequest` de l'API Bloomberg (`blpapi`).

**Fonctionnalités** :
- Requêtes par batch de **25 tickers** (limite Bloomberg)
- Mode **offline** via `BDHFetcher.load_from_csv(path, config, builder)`
- Sauvegarde CSV : `fetcher.save_to_csv(path)`
- Accesseurs typés :
  - `get_underlying_at_date(date) → Optional[float]`
  - `get_call_prices_at_date(date) → Tuple[List[float], List[float]]`
  - `get_put_prices_at_date(date) → Tuple[List[float], List[float]]`
  - `get_prices_at_date(date) → Dict[str, float]`
  - `get_all_dates() → List[date]`
  - `to_dataframe() → pd.DataFrame`

---

### 4. `distrib_proba/implied_distribution.py` — `ImpliedDistribution`

Extraction de la densité risque-neutre par **Breeden-Litzenberger** :

$$q_T(K) = e^{rT} \cdot \frac{\partial^2 C}{\partial K^2}$$

**Méthode** :
1. Récupère les prix calls pour une date donnée
2. Interpole par **CubicSpline** (strikes → prix)
3. Dérive deux fois → densité brute
4. Lissage gaussien (`gaussian_filter1d`, sigma paramétrable)
5. Normalisation pour obtenir une densité de probabilité

**API** :
- `compute_at_date(date, smooth_sigma) → Optional[np.ndarray]`
- `compute_all_dates(smooth_sigma) → Dict[date, np.ndarray]`
- `get_density(date) → Optional[np.ndarray]`
- `get_moments(date) → Optional[Dict]` (mean, std, skewness, kurtosis)
- `get_quantiles(date, quantiles) → Optional[Dict]`
- `get_available_dates() → List[date]`

---

### 5. `distrib_proba/density_analysis.py` — `DensityAnalyzer`

Analyse et visualisation de l'évolution de la densité.

**Méthodes** :
- `moments_timeseries() → pd.DataFrame` : série temporelle des moments
- `density_matrix() → Tuple[matrix, dates, grid]` : matrice pour heatmap
- `export_summary() → pd.DataFrame`
- `plot_density_at_date(date)` : graphique de la densité
- `plot_density_evolution()` : superposition des densités
- `plot_moments_evolution()` : évolution des 4 moments
- `plot_heatmap()` : heatmap dates × strikes

---

### 6. `strategy/option_builder.py` — `OptionBuilder`

Transforme les données BDH historiques en objets `Option` (de `myproject.option.option_class`) prêts pour le scoring C++.

Pour chaque date :
1. Récupère prix calls/puts et sous-jacent depuis le BDH
2. Calcule la **vol implicite Bachelier** par méthode de Brent :
   - `bachelier_implied_vol(market_price, F, K, T, is_call)` → σ_normal
3. Calcule les **Greeks Bachelier** (delta, gamma, vega, theta)
4. Injecte la **mixture** (densité implicite ou fallback log-normale)
5. Appelle `Option._calcul_all_surface()` → PnL array, average_pnl, sigma_pnl, etc.
6. Appelle `Option.calculate_all_intra_life()` → prix et PnL intra-vie

**Cache** : les options sont mises en cache par date dans `BacktestEngine._options_cache` pour éviter de reconstruire quand seuls les poids de scoring changent.

---

### 7. `strategy/backtest_engine.py` — `BacktestEngine`

Moteur principal du backtesting avec deux modes d'exécution.

#### `BacktestConfig`

| Champ | Type | Défaut | Description |
|-------|------|--------|-------------|
| `sfr_config` | `SFRConfig` | défaut | Configuration Bloomberg |
| `filter` | `FilterData` | peu restrictif | Filtres de stratégies |
| `scoring_weights` | `Dict[str, float]` | `{"average_pnl": 1.0}` | Poids de scoring |
| `max_legs` | `int` | `4` | Max legs par stratégie |
| `top_n` | `int` | `10` | Stratégies générées/date |
| `select_top_k` | `int` | `1` | Stratégies suivies/date |
| `entry_frequency_days` | `int` | `10` | Fréquence d'entrée |
| `min_days_before_expiry` | `int` | `5` | Pas d'entrée trop proche expiry |
| `smooth_sigma` | `float` | `0.5` | Lissage Breeden-Litzenberger |
| `compute_mtm` | `bool` | `False` | Mark-to-market quotidien |

#### Mode A — Single run : `engine.run()`

```python
engine = BacktestEngine(config)
results = engine.run(csv_path="data.csv", verbose=True)
# results: BacktestResults
```

Étapes :
1. Charge BDH + distributions (une seule fois)
2. Sélectionne les dates d'entrée (fréquence + cutoff expiry)
3. Pour chaque date :
   - Construit les `Option` (cache)
   - Initialise le cache C++ (`init_cpp_cache`)
   - Score via `process_combinations_batch_with_scoring` (C++)
   - Calcule le P&L réalisé (payoff intrinsèque à l'expiration)
4. Compile les `TradeRecord` dans un `BacktestResults`

#### Mode B — Grid search : `engine.run_weight_grid()`

```python
engine = BacktestEngine(config)
grid_result = engine.run_weight_grid(csv_path="data.csv")
# grid_result: WeightGridResult
```

Itère sur **8 jeux de poids prédéfinis** (`DEFAULT_WEIGHT_GRID`) :

| # | Poids | Description |
|---|-------|-------------|
| 1 | `{average_pnl: 1.0}` | Pur P&L moyen |
| 2 | `{average_pnl: 0.7, max_loss: 0.3}` | P&L + tail risk |
| 3 | `{average_pnl: 0.6, avg_intra_life_pnl: 0.4}` | P&L + intra-vie |
| 4 | `{average_pnl: 0.5, max_loss: 0.2, avg_intra_life_pnl: 0.3}` | Équilibré |
| 5 | `{avg_pnl_levrage: 0.6, average_pnl: 0.4}` | Levier |
| 6 | `{premium: 0.5, average_pnl: 0.3, max_loss: 0.2}` | Revenu premium |
| 7 | `{roll: 0.4, average_pnl: 0.6}` | Roll + P&L |
| 8 | `{average_pnl: 0.4, max_loss: 0.4, sigma_pnl: 0.2}` | Conservateur |

**Optimisations** :
- Données BDH et distributions chargées **une seule fois**
- Options cachées par date → réutilisées pour chaque jeu de poids
- Cache C++ (`init_cpp_cache`) ré-initialisé uniquement quand la date change (pas quand seuls les poids changent)
- MtM désactivé par défaut

#### Coût de calcul estimé

| Mode | Temps estimé |
|------|-------------|
| Single run (16 dates) | ~5-10 secondes |
| Grid search (8 poids × 16 dates) | ~40-60 secondes |

---

### 8. `strategy/results.py`

#### `TradeRecord` (dataclass)

Enregistrement unitaire d'un trade backtesté :
- Dates : `entry_date`, `expiry_date`
- Stratégie : `strategy_name`, `n_legs`, `legs_detail`
- Entrée : `entry_premium`, `predicted_avg_pnl`, `predicted_score`, `rank_at_entry`
- Résultats : `realized_pnl`, `underlying_at_entry`, `underlying_at_expiry`
- Bornes : `max_profit`, `max_loss`, `total_delta`
- MtM : `mtm_series` (dict date → valeur)

#### `BacktestResults`

Collection de trades + métriques agrégées.

**Méthodes** :
- `to_dataframe() → pd.DataFrame` : un trade par ligne
- `summary_metrics() → Dict` :
  - `n_trades`, `total_pnl`, `avg_pnl`, `std_pnl`
  - `sharpe_ratio` (P&L moyen / écart-type)
  - `hit_rate` (% trades positifs)
  - `avg_win`, `avg_loss`, `profit_factor`
  - `max_drawdown`
  - `prediction_correlation` (corr entre prédit et réalisé)
- `print_summary()` : affichage formaté avec top 5 meilleurs/pires trades
- `save_to_csv(path)`

#### `WeightGridResult`

Comparaison de N jeux de poids.

**Méthodes** :
- `to_comparison_dataframe()` : 1 ligne par jeu de poids avec toutes les métriques
- `best_weights(criterion="sharpe_ratio")` : identifie le meilleur jeu
- `print_comparison()` : tableau formaté
- `save_comparison_csv(path)`

---

## Utilisation CLI

### Mode Distribution (analyse de densité)

```bash
# Depuis la racine du projet
$env:PYTHONPATH = "."

# Online (Bloomberg)
python src/backtesting/main.py distribution

# Offline (CSV)
python src/backtesting/main.py distribution --offline data/sfr_data.csv --smooth 0.3

# Sans graphiques
python src/backtesting/main.py distribution --offline data.csv --no-plots
```

### Mode Strategy (backtesting)

```bash
# Single run (un jeu de poids par défaut)
python src/backtesting/main.py strategy --offline data.csv

# Paramètres custom
python src/backtesting/main.py strategy --offline data.csv \
    --max-legs 3 --top-n 20 --freq 5 --min-dte 10

# Grid search (compare 8 jeux de poids)
python src/backtesting/main.py strategy --offline data.csv --grid

# Export des résultats
python src/backtesting/main.py strategy --offline data.csv --grid --output results.csv

# Défaut (si aucun sous-commande → strategy)
python src/backtesting/main.py --offline data.csv
```

### Paramètres CLI

| Flag | Défaut | Description |
|------|--------|-------------|
| `--offline` | None | Chemin CSV (mode sans Bloomberg) |
| `--save` | None | Sauvegarder BDH en CSV |
| `--strike-min` | 95.0 | Strike minimum |
| `--strike-max` | 97.0 | Strike maximum |
| `--strike-step` | 0.125 | Pas des strikes |
| `--smooth` | 0.5 | Lissage densité |
| `--max-legs` | 4 | Max legs/stratégie |
| `--top-n` | 10 | Stratégies générées/date |
| `--top-k` | 1 | Stratégies suivies/date |
| `--freq` | 5 | Fréquence d'entrée (jours) |
| `--min-dte` | 5 | DTE min pour entrer |
| `--max-loss` | -999 | Perte max (-999 = désactivé) |
| `--output` | None | CSV de sortie |
| `--grid` | False | Activer grid search |

---

## Dépendances

### Internes (myproject)

| Module | Usage |
|--------|-------|
| `myproject.option.option_class.Option` | Dataclass option (~50 champs) avec `_calcul_all_surface()`, `calculate_all_intra_life()`, `bachelier_price()` |
| `myproject.strategy.batch_processor` | `init_cpp_cache()`, `process_batch_cpp_with_scoring()` — interface Python → C++ |
| `myproject.strategy.strategy_class.StrategyComparison` | Résultat scoré d'une combinaison |
| `myproject.app.data_types.FilterData` | Filtres pour la génération |

### Externes

| Package | Usage |
|---------|-------|
| `blpapi` | API Bloomberg (BDH) |
| `strategy_metrics_cpp` | Module C++ compilé pour le scoring combinatoire |
| `numpy` | Calculs numériques |
| `scipy` | `CubicSpline`, `brentq`, `gaussian_filter1d`, `norm` |
| `pandas` | DataFrames résultats |
| `matplotlib` | Graphiques (optionnel) |

---

## Modèle de pricing : Bachelier (Normal Model)

Le modèle Bachelier est utilisé pour les options STIR (Short-Term Interest Rate) car le sous-jacent est un taux/prix proche de 100.

**Prix d'un call** :

$$C = (F - K) \cdot \Phi(d) + \sigma\sqrt{T} \cdot \phi(d) \quad \text{où} \quad d = \frac{F - K}{\sigma\sqrt{T}}$$

**Greeks** :
- $\Delta = \Phi(d)$ (call), $\Delta = \Phi(d) - 1$ (put)
- $\Gamma = \frac{\phi(d)}{\sigma\sqrt{T}}$
- $\mathcal{V} = \sqrt{T} \cdot \phi(d) / 100$
- $\Theta = -\frac{\sigma \cdot \phi(d)}{2\sqrt{T} \cdot 365}$

**Vol implicite** : retrouvée par méthode de Brent (`brentq`) en inversant le prix Bachelier.
