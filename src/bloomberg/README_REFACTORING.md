# Module Bloomberg - Architecture Refactorisée

## 📁 Structure du Module

Le module Bloomberg a été refactorisé en fichiers plus petits et spécialisés pour faciliter la maintenance et l'extension, avec un focus particulier sur **EURIBOR** (options sur futures de taux).

```
src/bloomberg/
├── __init__.py              # Point d'entrée, exports publics
├── models.py                # ⭐ Dataclasses (OptionData, EuriborOptionData)
├── connection.py            # ⭐ Gestion connexion Bloomberg
├── ticker_builder.py        # ⭐ Construction tickers (actions, indices, EURIBOR)
├── fetcher.py               # ⭐ Client principal pour récupération données
├── formatters.py            # ⭐ Fonctions d'affichage
├── euribor_example.py       # 📖 Exemples EURIBOR complets
├── bloomberg_connector.py   # (Legacy, conservé pour compatibilité)
├── connexion.py             # (Legacy)
├── helper.py                # (Legacy)
└── option_data_fetcher.py   # (Ancien fichier monolithique, remplacé)
```

**⭐ = Nouveaux fichiers modulaires**  
**📖 = Documentation par l'exemple**

---

## 🚀 Quick Start

### Installation

```bash
# Prérequis: Bloomberg Terminal lancé et connecté
pip install blpapi
```

### Usage Basique - Options sur Actions

```python
from datetime import date
from bloomberg import BloombergOptionFetcher

# Context manager gère automatiquement la connexion
with BloombergOptionFetcher() as fetcher:
    # Récupérer une option AAPL
    option = fetcher.get_option_data(
        underlying="AAPL",
        expiry=date(2024, 12, 20),
        option_type="C",  # CALL
        strike=150.0
    )
    
    print(f"Delta: {option.delta}")
    print(f"Volatilité implicite: {option.implied_volatility}%")
    print(f"Dernier prix: ${option.last}")
```

### Usage EURIBOR - Options sur Taux

```python
from datetime import date
from bloomberg import BloombergOptionFetcher, format_euribor_option

with BloombergOptionFetcher() as fetcher:
    # Option EURIBOR Mars 2025, strike 97.50
    # (taux implicite: 100 - 97.50 = 2.50%)
    euribor_opt = fetcher.get_option_data(
        underlying="ER",
        expiry=date(2025, 3, 15),
        option_type="C",
        strike=97.50,
        is_euribor=True  # ⚠️ Important!
    )
    
    # Affichage spécialisé EURIBOR
    print(format_euribor_option(euribor_opt))
    
    # Métriques spécifiques taux
    print(f"Taux implicite: {euribor_opt.implied_rate:.2f}%")
    print(f"Valeur du tick: €{euribor_opt.tick_value:.2f}")
    
    # Payoff selon un scénario de taux
    payoff = euribor_opt.payoff_at_rate(final_rate=2.75)
    print(f"Payoff si taux final = 2.75%: €{payoff:.2f}")
```

---

## 📚 Architecture Détaillée

### 1️⃣ `models.py` - Structures de Données

**Classes:**
- `OptionData`: Dataclass pour options standard (actions, indices)
- `EuriborOptionData`: Extension pour options EURIBOR avec métriques de taux

**Attributs OptionData:**
```python
@dataclass
class OptionData:
    # Identification
    ticker: str              # Ticker Bloomberg complet
    underlying: str          # Symbole sous-jacent
    option_type: str         # 'CALL' ou 'PUT'
    strike: float           # Prix d'exercice
    expiry: date            # Date d'expiration
    
    # Prix marché
    bid, ask, last, mid: Optional[float]
    volume, open_interest: Optional[int]
    
    # Greeks
    delta, gamma, vega, theta, rho: Optional[float]
    
    # Volatilité
    implied_volatility: Optional[float]
    
    # Propriétés calculées
    @property
    def spread(self) -> Optional[float]  # Spread bid-ask
    
    @property
    def is_liquid(self) -> bool  # Check liquidité
```

**Extension EURIBOR:**
```python
@dataclass
class EuriborOptionData(OptionData):
    contract_size: float = 2500.0  # €2500 par point de base
    
    @property
    def implied_rate(self) -> float:
        """Taux = 100 - Strike"""
        return 100.0 - self.strike
    
    @property
    def tick_value(self) -> float:
        """Valeur d'un tick (0.01 point) = €25"""
        return self.contract_size * 0.01
    
    def payoff_at_rate(self, final_rate: float) -> float:
        """Calcule le payoff à expiration pour un taux donné"""
        # Implementation...
```

---

### 2️⃣ `connection.py` - Gestion Connexion Bloomberg

**Classe `BloombergConnection`:**
```python
class BloombergConnection:
    def __init__(self, host="localhost", port=8194):
        """Paramètres connexion Terminal"""
        
    def connect(self) -> bool:
        """Établit connexion + ouvre service //blp/refdata"""
        
    def disconnect(self):
        """Ferme proprement la connexion"""
        
    def is_connected(self) -> bool:
        """Vérifie si connexion active"""
        
    # Context Manager support
    def __enter__(self):
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
```

**Fonction utilitaire:**
```python
def test_connection(host="localhost", port=8194) -> bool:
    """Test rapide de connexion Bloomberg"""
```

---

### 3️⃣ `ticker_builder.py` - Construction Tickers

**Fonctions principales:**

```python
def build_option_ticker(
    underlying: str,
    expiry: date,
    option_type: Literal['C', 'P', 'CALL', 'PUT'],
    strike: float,
    is_euribor: bool = False
) -> str:
    """
    Fonction générique qui route vers le bon format.
    
    Exemples:
        build_option_ticker("AAPL", date(2024, 12, 20), "C", 150.0)
        → "AAPL 12/20/24 C150 Equity"
        
        build_option_ticker("SPX", date(2024, 12, 20), "P", 4500.0)
        → "SPX 12/20/24 P4500 Index"
        
        build_option_ticker("ER", date(2025, 3, 15), "C", 97.50, is_euribor=True)
        → "ER H5 C97.50 Comdty"
    """
```

**Format EURIBOR:**
```python
def build_euribor_option_ticker(
    expiry: date,
    option_type: Literal['C', 'P', 'CALL', 'PUT'],
    strike: float
) -> str:
    """
    Format spécial EURIBOR: "ER{MonthCode}{Year} {C/P}{Strike} Comdty"
    
    Month Codes:
        H = Mars, M = Juin, U = Sept, Z = Déc
    
    Exemples:
        Mars 2025 → "ER H5 C97.50 Comdty"
        Juin 2025 → "ER M5 P98.00 Comdty"
    """
```

**Détection automatique du suffixe:**
```python
def get_suffix(underlying: str) -> str:
    """
    Auto-détecte le type d'actif:
    - 'ER' ou 'EURIBOR' → 'Comdty'
    - Finit par 'X' → 'Index' (SPX, NDX, etc.)
    - Sinon → 'Equity'
    """
```

---

### 4️⃣ `fetcher.py` - Client Principal

**Classe `BloombergOptionFetcher`:**

```python
class BloombergOptionFetcher:
    def __init__(self, fields: Optional[List[str]] = None):
        """
        Initialise avec champs Bloomberg désirés.
        Par défaut: DEFAULT_OPTION_FIELDS (20+ champs)
        """
    
    def get_option_data(
        self,
        underlying: str,
        expiry: date,
        option_type: str,
        strike: float,
        is_euribor: bool = False
    ) -> Optional[OptionData]:
        """
        Récupère toutes les données d'une option.
        Retourne OptionData ou EuriborOptionData selon le type.
        """
    
    def list_expiries(
        self,
        underlying: str,
        is_euribor: bool = False
    ) -> List[date]:
        """
        Liste toutes les dates d'expiration disponibles.
        """
    
    def get_options_by_strike(
        self,
        underlying: str,
        strike: float,
        option_type: str,
        expiries: Optional[List[date]] = None,
        is_euribor: bool = False
    ) -> List[OptionData]:
        """
        Récupère toutes les options pour un strike sur plusieurs expiries.
        Utile pour analyser la structure de terme (term structure).
        """
```

**Champs Bloomberg par défaut:**
```python
DEFAULT_OPTION_FIELDS = [
    # Prix marché
    'PX_BID', 'PX_ASK', 'PX_LAST', 'PX_MID',
    'PX_VOLUME', 'OPEN_INT',
    
    # Greeks
    'DELTA', 'GAMMA', 'VEGA', 'THETA', 'RHO',
    
    # Volatilité
    'IVOL_MID',
    
    # Info contractuelles
    'OPT_STRIKE_PX', 'OPT_EXPIRE_DT', 'OPT_PUT_CALL', 'OPT_UNDL_TICKER'
]
```

---

### 5️⃣ `formatters.py` - Affichage des Données

**Fonctions d'affichage:**

```python
def format_option_summary(option: OptionData) -> str:
    """Résumé compact sur une ligne"""
    # → "AAPL 12/20/24 C150: Last=$5.20 Delta=0.45 IV=25.3%"

def format_option_table(options: List[OptionData], title: str) -> str:
    """Tableau formaté pour liste d'options"""

def format_euribor_option(option: EuriborOptionData) -> str:
    """Affichage spécialisé EURIBOR avec métriques de taux"""

def format_greeks_summary(option: OptionData) -> str:
    """Affichage détaillé des Greeks uniquement"""

def format_liquidity_check(option: OptionData) -> str:
    """Évalue la liquidité (volume, OI, spread)"""

def format_term_structure(options: List[OptionData], metric: str) -> str:
    """Affiche la structure de terme d'une métrique (IV, delta, etc.)"""
```

**Exemple d'utilisation:**
```python
from bloomberg import BloombergOptionFetcher, format_greeks_summary

with BloombergOptionFetcher() as fetcher:
    opt = fetcher.get_option_data("AAPL", date(2024, 12, 20), "C", 150.0)
    print(format_greeks_summary(opt))

# Output:
# Greeks for AAPL 12/20/24 C150:
#   Delta: 0.450 (45.0% probability ITM)
#   Gamma: 0.023 (delta sensitivity)
#   Vega: 0.180 (volatility sensitivity)
#   Theta: -0.052 (time decay per day)
#   Rho: 0.012 (interest rate sensitivity)
```

---

## 🎯 Focus EURIBOR

### Qu'est-ce que EURIBOR ?

**EURIBOR** = Euro Interbank Offered Rate  
→ Taux d'intérêt de référence pour les prêts interbancaires en euros

**Options EURIBOR** = Options sur **futures** de taux EURIBOR 3 mois sur Eurex

### Caractéristiques Spécifiques

| Caractéristique | Valeur |
|----------------|--------|
| **Symbole Bloomberg** | `ER` |
| **Suffixe** | `Comdty` (commodity/future) |
| **Taille contrat** | €2,500 par point de base |
| **Valeur tick** | €25 (1 tick = 0.01 point) |
| **Expiries** | Trimestriel (Mars/Juin/Sept/Déc) |

### Format Ticker EURIBOR

```
ER {MonthCode}{Year} {C/P}{Strike} Comdty

Exemples:
- ER H5 C97.50 Comdty  → CALL Mars 2025, strike 97.50
- ER M5 P98.00 Comdty  → PUT Juin 2025, strike 98.00
- ER U5 C97.75 Comdty  → CALL Sept 2025, strike 97.75
```

**Month Codes:**
- H = Mars (March)
- M = Juin (June)
- U = Septembre (September)
- Z = Décembre (December)

### Relation Strike ↔ Taux

```
Taux Implicite = 100 - Strike

Exemples:
- Strike 97.50 → Taux = 2.50%
- Strike 98.00 → Taux = 2.00%
- Strike 97.00 → Taux = 3.00%
```

⚠️ **Logique inversée:**
- Strike monte → Taux baisse
- CALL profitable si taux **baisse** (future monte)
- PUT profitable si taux **monte** (future baisse)

### Calcul du Payoff

```python
# Pour un CALL strike 97.50 (taux implicite 2.50%)
euribor_call = EuriborOptionData(
    strike=97.50,
    option_type='CALL',
    contract_size=2500.0,
    # ... autres attributs
)

# Scénario 1: Taux final = 2.25% (baisse de 0.25%)
payoff_1 = euribor_call.payoff_at_rate(2.25)
# Future price = 100 - 2.25 = 97.75
# Intrinsic = max(0, 97.75 - 97.50) = 0.25 points
# Payoff = 0.25 × €2500 = €625

# Scénario 2: Taux final = 2.75% (hausse de 0.25%)
payoff_2 = euribor_call.payoff_at_rate(2.75)
# Future price = 100 - 2.75 = 97.25
# Intrinsic = max(0, 97.25 - 97.50) = 0
# Payoff = €0 (out-of-the-money)
```

---

## 📖 Exemples Complets

Le fichier **`euribor_example.py`** contient 4 exemples détaillés:

### Exemple 1: Option EURIBOR Individuelle
```python
# Récupère et affiche une option EURIBOR spécifique
# Ticker: ER H5 C97.50 Comdty (CALL Mars 2025, strike 97.50)
```

### Exemple 2: Structure de Terme
```python
# Scanne toutes les expiries pour un strike donné
# Affiche comment la volatilité implicite évolue dans le temps
```

### Exemple 3: Scénarios de Payoff
```python
# Calcule le P&L sous différents scénarios de taux
# (ex: taux final = 2.00%, 2.25%, 2.50%, 2.75%, 3.00%, etc.)
```

### Exemple 4: Bull Call Spread
```python
# Construit un spread:
#   - BUY CALL strike 97.50
#   - SELL CALL strike 98.00
# Calcule coût, profit max, perte max, break-even
```

**Exécuter les exemples:**
```bash
cd src/bloomberg
python euribor_example.py
```

---

## 🔧 Migration depuis l'Ancien Code

### Ancien code (option_data_fetcher.py)

```python
from bloomberg.option_data_fetcher import BloombergOptionFetcher

fetcher = BloombergOptionFetcher()
fetcher.connect()

# ... utilisation ...

fetcher.disconnect()
```

### Nouveau code (architecture modulaire)

```python
from bloomberg import BloombergOptionFetcher

# Plus besoin de connect/disconnect manuel
with BloombergOptionFetcher() as fetcher:
    # ... utilisation ...
    pass  # Déconnexion automatique
```

### Changements dans les imports

| Ancien | Nouveau |
|--------|---------|
| `from bloomberg.option_data_fetcher import BloombergOptionFetcher` | `from bloomberg import BloombergOptionFetcher` |
| `format_option_table()` dans fetcher | `from bloomberg import format_option_table` |
| Pas de support EURIBOR dédié | `is_euribor=True` + `EuriborOptionData` |

---

## 🧪 Tests

### Test Connexion Bloomberg
```python
from bloomberg import test_connection

if test_connection():
    print("✓ Bloomberg Terminal accessible")
else:
    print("✗ Vérifiez que Terminal est lancé")
```

### Test Récupération Option
```python
from datetime import date
from bloomberg import BloombergOptionFetcher

with BloombergOptionFetcher() as fetcher:
    # Test action
    aapl = fetcher.get_option_data("AAPL", date(2024, 12, 20), "C", 150.0)
    assert aapl is not None
    assert aapl.ticker.startswith("AAPL")
    
    # Test EURIBOR
    euribor = fetcher.get_option_data("ER", date(2025, 3, 15), "C", 97.50, is_euribor=True)
    assert euribor is not None
    assert euribor.ticker.startswith("ER H5")
    assert euribor.implied_rate == 2.50
```

---

## ❓ Troubleshooting

### Erreur: "Cannot connect to Bloomberg Terminal"
```
Solution:
1. Vérifier que Bloomberg Terminal est lancé
2. Vérifier que vous êtes connecté (login Bloomberg)
3. Tester avec: python -c "from bloomberg import test_connection; test_connection()"
```

### Erreur: "Option not found"
```
Solution:
1. Vérifier que la date d'expiry existe (EURIBOR = trimestriel seulement)
2. Vérifier le format du ticker avec print(build_option_ticker(...))
3. Vérifier l'accès aux données sur votre abonnement Bloomberg
```

### Erreur: "Module 'blpapi' not found"
```
Solution:
pip install blpapi
```

---

## 📞 Support

Pour questions ou bugs:
1. Vérifier les exemples dans `euribor_example.py`
2. Consulter la doc inline (docstrings détaillés dans chaque fichier)
3. Contacter: BGC Trading Desk

---

## 🗺️ Roadmap

Améliorations futures possibles:

- [ ] Support d'autres futures de taux (SOFR, SONIA, etc.)
- [ ] Cache des données pour limiter les appels Bloomberg
- [ ] Mode async pour requêtes parallèles
- [ ] Export vers Excel/CSV
- [ ] Intégration avec le système de stratégies existant
- [ ] Graphiques de volatility surface
- [ ] Backtesting avec données historiques

---

## 📝 Licence

© 2025 BGC Trading Desk - Usage interne uniquement
