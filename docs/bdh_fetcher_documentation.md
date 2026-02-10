# Documentation — `BDHFetcher` (Bloomberg Historical Data Fetcher)

## Vue d'ensemble

Le module `bdh_fetcher.py` permet de **récupérer les données historiques de prix d'options SOFR (SFR)** via l'API Bloomberg `blpapi`. Il est l'équivalent programmatique de la formule Excel :

```
=@BDH("SFRH5C 96.00 Comdty", "PX_LAST", "30/07/2024", "13/03/2025")
```

Le fetcher utilise le type de requête `HistoricalDataRequest` du service `//blp/refdata`.

---

## Architecture du module

```
backtesting/bloomberg/
├── __init__.py          # Expose BDHFetcher et SFRTickerBuilder
├── bdh_fetcher.py       # Récupération des données historiques (ce fichier)
├── ticker_builder.py    # Construction des tickers Bloomberg
```

### Dépendances internes

| Composant | Rôle |
|---|---|
| `SFRConfig` (backtesting.config) | Configuration centralisée (strikes, dates, champs Bloomberg) |
| `SFRTickerBuilder` (backtesting.bloomberg.ticker_builder) | Construction et métadonnées de tous les tickers Bloomberg |

### Dépendances externes

| Package | Usage |
|---|---|
| `blpapi` | API officielle Bloomberg pour Python |
| `pandas` | DataFrame pour la consolidation des séries temporelles |
| `numpy` | Arrays pour les données de prix/strikes triés |

---

## 1. Gestion de la connexion Bloomberg

### Variable globale `_session`

Une session Bloomberg unique est maintenue en singleton via la variable globale `_session`.

### `_get_session(host="localhost", port=8194) → Session`

Crée ou retourne la session Bloomberg existante.

| Paramètre | Défaut | Description |
|---|---|---|
| `host` | `"localhost"` | Hôte du service Bloomberg |
| `port` | `8194` | Port du service Bloomberg |

**Comportement :**
1. Si `_session` est `None`, crée une nouvelle session avec les options suivantes :
   - `setAutoRestartOnDisconnection(True)` — reconnexion automatique
   - `setNumStartAttempts(3)` — 3 tentatives de démarrage
2. Démarre la session (`session.start()`)
3. Ouvre le service `//blp/refdata`
4. Lève `ConnectionError` si l'une des étapes échoue

### `close_session()`

Ferme proprement la session Bloomberg et remet `_session` à `None`.

---

## 2. Classe `BDHFetcher`

### Constructeur

```python
BDHFetcher(config: SFRConfig, builder: SFRTickerBuilder)
```

| Attribut | Type | Description |
|---|---|---|
| `config` | `SFRConfig` | Configuration (dates, strikes, champ Bloomberg) |
| `builder` | `SFRTickerBuilder` | Builder contenant les tickers et métadonnées |
| `raw_data` | `Dict[str, Dict[date, float]]` | Données brutes : `{ticker → {date → prix}}` |
| `_df` | `Optional[pd.DataFrame]` | DataFrame mis en cache (lazy) |

---

### Méthodes de récupération des données

#### `fetch_all() → BDHFetcher`

**Point d'entrée principal.** Récupère l'historique `PX_LAST` de tous les tickers (calls + puts + sous-jacent).

**Fonctionnement :**
1. Combine `builder.all_tickers` + `builder.underlying_ticker` dans une liste unique
2. Découpe en **batches de 25 tickers** pour respecter les limites Bloomberg
3. Appelle `_fetch_batch()` pour chaque batch
4. Affiche un résumé (nombre de tickers et dates reçus)
5. Retourne `self` pour permettre le chaînage : `fetcher.fetch_all().to_dataframe()`

#### `_fetch_batch(tickers: List[str])`

Envoie une `HistoricalDataRequest` Bloomberg pour un batch de tickers.

**Paramètres de la requête Bloomberg :**

| Paramètre | Valeur | Description |
|---|---|---|
| `securities` | Liste des tickers du batch | Instruments à requêter |
| `fields` | `config.bbg_field` (défaut `"PX_LAST"`) | Champ demandé |
| `startDate` | `config.start_date_str` (format `YYYYMMDD`) | Date de début |
| `endDate` | `config.end_date_str` (format `YYYYMMDD`) | Date de fin |
| `periodicitySelection` | `"DAILY"` | Fréquence journalière |
| `nonTradingDayFillOption` | `"NON_TRADING_WEEKDAYS"` | Remplir les jours ouvrés non tradés |
| `nonTradingDayFillMethod` | `"PREVIOUS_VALUE"` | Utiliser la dernière valeur connue |

**Boucle événementielle :**
- Attend les événements Bloomberg avec un timeout de **10 secondes** (`session.nextEvent(10_000)`)
- Parse les réponses `PARTIAL_RESPONSE` et `RESPONSE`
- Sort de la boucle quand le type est `RESPONSE` (réponse complète)

#### `_parse_historical_response(event: Event)`

Parse une réponse Bloomberg de type `HistoricalDataRequest`.

**Structure attendue du message Bloomberg :**
```
msg
└── securityData
    ├── security       → "SFRH5C 96.00 Comdty" (ticker)
    ├── securityError?  → (erreur éventuelle)
    └── fieldData[]     → tableau de {date, PX_LAST}
```

**Logique de parsing :**
1. Extrait le ticker depuis `securityData.security`
2. Si `securityError` est présent → affiche un warning et retourne
3. Itère sur chaque élément de `fieldData` :
   - Extrait la `date` (convertie en `datetime.date`)
   - Extrait la valeur du champ (`PX_LAST` par défaut)
   - **Filtre** : seules les valeurs `> 0` sont conservées
4. Stocke dans `self.raw_data[ticker]`

---

### Méthodes de conversion et d'accès aux données

#### `to_dataframe() → pd.DataFrame`

Convertit les données brutes en DataFrame pandas consolidé.

| Caractéristique | Détail |
|---|---|
| **Index** | `DatetimeIndex` (trié chronologiquement) |
| **Colonnes** | Tickers Bloomberg (ex: `"SFRH5C 96.00 Comdty"`) |
| **Valeurs** | Prix (`PX_LAST`) |
| **Forward-fill** | `ffill()` appliqué pour combler les jours sans données |
| **Cache** | Le DataFrame est calculé une seule fois (lazy, stocké dans `_df`) |

#### `get_prices_at_date(target_date: date) → Dict[str, float]`

Retourne les prix de **tous les tickers** pour une date donnée.

- Utilise `searchsorted` pour trouver la date la plus proche **en arrière** (≤ target_date)
- Retourne `{ticker: prix}` en excluant les valeurs `NaN`

#### `get_call_prices_at_date(target_date: date) → Tuple[np.ndarray, np.ndarray]`

Retourne les prix des **calls uniquement** pour une date donnée.

- **Retour** : `(strikes, call_prices)` — deux arrays numpy triés par strike croissant
- Ne retourne que les tickers présents dans `builder.call_tickers` et ayant un prix disponible

#### `get_put_prices_at_date(target_date: date) → Tuple[np.ndarray, np.ndarray]`

Identique à `get_call_prices_at_date` mais pour les **puts**.

- **Retour** : `(strikes, put_prices)` — deux arrays numpy triés par strike croissant

#### `get_underlying_at_date(target_date: date) → Optional[float]`

Retourne le prix du **sous-jacent** (future SOFR) pour une date donnée, ou `None` si indisponible.

#### `get_all_dates() → List[date]`

Retourne la liste complète de toutes les dates pour lesquelles des données existent.

---

### Persistance CSV (mode offline)

#### `save_to_csv(filepath: str)`

Sauvegarde le DataFrame consolidé en fichier CSV.

- Crée les répertoires parents si nécessaire (`mkdir(parents=True, exist_ok=True)`)
- Format : index = dates, colonnes = tickers

#### `load_from_csv(filepath, config, builder) → BDHFetcher` *(classmethod)*

Charge les données depuis un CSV existant (mode offline, sans connexion Bloomberg).

**Fonctionnement :**
1. Crée une nouvelle instance `BDHFetcher`
2. Lit le CSV avec `pd.read_csv(..., parse_dates=True)`
3. Reconstruit `raw_data` depuis le DataFrame pour maintenir la cohérence
4. Filtre les valeurs `NaN` et `≤ 0`

---

## 3. Configuration associée (`SFRConfig`)

Le `BDHFetcher` dépend de `SFRConfig` pour tous ses paramètres :

| Champ | Type | Défaut | Description |
|---|---|---|---|
| `underlying` | `str` | `"SFR"` | Préfixe Bloomberg du sous-jacent |
| `suffix` | `str` | `"Comdty"` | Suffixe Bloomberg (classe d'actif) |
| `expiry_month` | `str` | `"H"` | Code mois Bloomberg (H = Mars) |
| `expiry_year` | `int` | `5` | Année sur 1 chiffre (5 = 2025) |
| `strike_min` | `float` | `95.0` | Strike minimum |
| `strike_max` | `float` | `97.0` | Strike maximum |
| `strike_step` | `float` | `0.125` | Pas entre strikes (12.5 bps pour SOFR) |
| `start_date` | `date` | `2024-07-30` | Début de l'historique |
| `end_date` | `date` | `2025-03-13` | Fin de l'historique (expiration) |
| `bbg_field` | `str` | `"PX_LAST"` | Champ Bloomberg demandé |

### Codes mois Bloomberg utilisés

| Code | Mois |
|---|---|
| F | Janvier |
| G | Février |
| H | Mars |
| J | Avril |
| K | Mai |
| M | Juin |
| N | Juillet |
| Q | Août |
| U | Septembre |
| V | Octobre |
| X | Novembre |
| Z | Décembre |

---

## 4. Flux de données complet

```
SFRConfig                    SFRTickerBuilder
(strikes, dates, field)      (tickers Bloomberg)
        │                            │
        └──────────┬─────────────────┘
                   ▼
             BDHFetcher
                   │
      ┌────────────┼────────────┐
      ▼            ▼            ▼
  fetch_all()  to_dataframe()  save_to_csv()
      │            │
      ▼            ▼
  Bloomberg     DataFrame pandas
  blpapi        (index=dates, cols=tickers)
      │            │
      ▼            ▼
  raw_data      get_call_prices_at_date()
  {ticker →     get_put_prices_at_date()
   {date →      get_underlying_at_date()
    prix}}      get_all_dates()
```

---

## 5. Exemple d'utilisation

```python
from backtesting.config import SFRConfig
from backtesting.bloomberg.ticker_builder import SFRTickerBuilder
from backtesting.bloomberg.bdh_fetcher import BDHFetcher, close_session
from datetime import date

# 1. Configuration
config = SFRConfig(
    underlying="SFR",
    expiry_month="H",
    expiry_year=5,
    strike_min=95.0,
    strike_max=97.0,
    strike_step=0.125,
    start_date=date(2024, 7, 30),
    end_date=date(2025, 3, 13),
    bbg_field="PX_LAST",
)

# 2. Construire les tickers
builder = SFRTickerBuilder(config).build()
# → "SFRH5C 95.00 Comdty", "SFRH5P 95.00 Comdty", ..., "SFRH5C 97.00 Comdty"

# 3. Fetcher les données historiques
fetcher = BDHFetcher(config, builder)
fetcher.fetch_all()

# 4. Convertir en DataFrame
df = fetcher.to_dataframe()
print(df.head())

# 5. Accéder aux prix à une date donnée
strikes, call_prices = fetcher.get_call_prices_at_date(date(2025, 1, 15))
underlying = fetcher.get_underlying_at_date(date(2025, 1, 15))

# 6. Sauvegarder pour usage offline
fetcher.save_to_csv("data/sfr_options_history.csv")

# 7. Recharger plus tard sans Bloomberg
fetcher_offline = BDHFetcher.load_from_csv(
    "data/sfr_options_history.csv", config, builder
)

# 8. Fermer la session
close_session()
```

---

## 6. Gestion des erreurs

| Situation | Comportement |
|---|---|
| Impossible de se connecter à Bloomberg | `ConnectionError` levée par `_get_session()` |
| Service `//blp/refdata` indisponible | `ConnectionError` levée par `_get_session()` |
| Ticker inconnu de Bloomberg | Warning affiché, ticker ignoré (pas dans `raw_data`) |
| Valeur manquante ou ≤ 0 | Ignorée silencieusement lors du parsing |
| Exception dans un batch | Catch global avec `traceback.print_exc()`, les autres batches continuent |
| DataFrame vide (aucune donnée) | `to_dataframe()` retourne un `DataFrame` vide |
| Date demandée hors plage | `get_prices_at_date()` retourne la première date disponible |

---

## 7. Points techniques importants

1. **Batch de 25 tickers** : Bloomberg limite le nombre de securities par requête. Le fetcher découpe automatiquement en lots de 25.

2. **Forward-fill** : Les jours sans données (weekends, jours fériés restants) sont remplis avec la dernière valeur connue via `df.ffill()`.

3. **Singleton de session** : Une seule session Bloomberg est ouverte pour toute la durée du programme. Toujours appeler `close_session()` en fin de programme.

4. **Lazy DataFrame** : Le DataFrame n'est construit qu'au premier appel de `to_dataframe()`, puis mis en cache dans `_df`.

5. **Mode offline** : Grâce à `save_to_csv()` / `load_from_csv()`, les données peuvent être utilisées sans connexion Bloomberg.

6. **Timeout événementiel** : Chaque `session.nextEvent()` a un timeout de 10 secondes. Si Bloomberg ne répond pas dans ce délai, l'exécution continue.
