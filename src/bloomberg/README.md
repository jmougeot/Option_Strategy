# Bloomberg Option Data Fetcher

## 📋 Description

Module Python pour récupérer les prix et les Greeks des options via l'API Bloomberg Terminal.

**Fonctionnalités principales:**
- ✅ Connexion automatique au Terminal Bloomberg
- 📊 Récupération des prix (Bid, Ask, Last, Mid)
- 📈 Récupération des Greeks (Delta, Gamma, Vega, Theta, Rho)
- 🔢 Volatilité implicite et volumes
- 🔗 Récupération de chaînes d'options complètes
- 🎯 Support des CALLS et PUTS
- 🛡️ Gestion d'erreurs robuste

---

## 🚀 Installation

### Prérequis

1. **Bloomberg Terminal** installé et actif
2. **Python 3.8+**
3. **blpapi** (bibliothèque Bloomberg Python)

```bash
# Installer blpapi
pip install blpapi

# Vérifier l'installation
python3 -c "import blpapi; print('✅ blpapi installé')"
```

---

## 📖 Usage

### 1. Récupérer une option unique

```python
from bloomberg.option_data_fetcher import BloombergOptionFetcher

# Créer le fetcher
fetcher = BloombergOptionFetcher()

# Se connecter
if fetcher.connect():
    # Récupérer une option SPY CALL
    option = fetcher.get_option_data(
        underlying='SPY',
        option_type='CALL',
        strike=450.0,
        expiration='2024-12-20'
    )
    
    if option:
        print(f"Prix: ${option.last}")
        print(f"Delta: {option.delta}")
        print(f"IV: {option.implied_volatility}%")
    
    # Déconnecter
    fetcher.disconnect()
```

### 2. Utiliser le context manager (recommandé)

```python
from bloomberg.option_data_fetcher import BloombergOptionFetcher

with BloombergOptionFetcher() as fetcher:
    option = fetcher.get_option_data('SPY', 'CALL', 450.0, '2024-12-20')
    print(option)
```

### 3. Récupérer une chaîne d'options

```python
from bloomberg.option_data_fetcher import BloombergOptionFetcher, format_option_table

with BloombergOptionFetcher() as fetcher:
    # Récupérer plusieurs strikes
    strikes = [440, 445, 450, 455, 460]
    
    options = fetcher.get_option_chain(
        underlying='SPY',
        expiration='2024-12-20',
        strikes=strikes,
        option_types=['CALL', 'PUT']  # Ou seulement ['CALL']
    )
    
    # Afficher en tableau
    print(format_option_table(options))
```

### 4. Champs personnalisés

```python
# Récupérer uniquement certains champs
custom_fields = ['PX_LAST', 'DELTA', 'IVOL_MID']

option = fetcher.get_option_data(
    'SPY', 'CALL', 450.0, '2024-12-20',
    fields=custom_fields
)
```

---

## 🔧 API Référence

### `BloombergOptionFetcher`

#### Constructeur

```python
BloombergOptionFetcher(host='localhost', port=8194)
```

**Paramètres:**
- `host` (str): Adresse du serveur Bloomberg (défaut: 'localhost')
- `port` (int): Port du serveur (défaut: 8194)

#### Méthodes principales

##### `connect() -> bool`

Établit la connexion avec Bloomberg Terminal.

**Retourne:** `True` si succès, `False` sinon

##### `disconnect()`

Ferme la connexion Bloomberg proprement.

##### `get_option_data(...) -> OptionData | None`

Récupère les données d'une option spécifique.

**Paramètres:**
- `underlying` (str): Symbole du sous-jacent (ex: 'SPY', 'AAPL')
- `option_type` (str): 'CALL' ou 'PUT'
- `strike` (float): Prix d'exercice
- `expiration` (str): Date d'expiration au format 'YYYY-MM-DD'
- `fields` (List[str], optional): Liste des champs Bloomberg à récupérer

**Retourne:** `OptionData` ou `None` si échec

**Exemple:**
```python
option = fetcher.get_option_data('SPY', 'CALL', 450.0, '2024-12-20')
```

##### `get_option_chain(...) -> List[OptionData]`

Récupère une chaîne d'options pour plusieurs strikes.

**Paramètres:**
- `underlying` (str): Symbole du sous-jacent
- `expiration` (str): Date d'expiration 'YYYY-MM-DD'
- `strikes` (List[float]): Liste des strikes à récupérer
- `option_types` (List[str], optional): ['CALL', 'PUT'] par défaut

**Retourne:** Liste d'objets `OptionData`

---

### `OptionData`

Structure de données pour une option.

**Attributs:**

| Attribut | Type | Description |
|----------|------|-------------|
| `ticker` | str | Ticker Bloomberg complet |
| `underlying` | str | Symbole du sous-jacent |
| `option_type` | str | 'CALL' ou 'PUT' |
| `strike` | float | Prix d'exercice |
| `expiration` | date | Date d'expiration |
| `bid` | float | Prix Bid |
| `ask` | float | Prix Ask |
| `last` | float | Dernier prix |
| `mid` | float | Prix Mid |
| `delta` | float | Delta (sensibilité au prix) |
| `gamma` | float | Gamma (sensibilité du delta) |
| `vega` | float | Vega (sensibilité à la volatilité) |
| `theta` | float | Theta (déclin temporel) |
| `rho` | float | Rho (sensibilité aux taux) |
| `implied_volatility` | float | Volatilité implicite (%) |
| `open_interest` | int | Open Interest |
| `volume` | int | Volume |

---

## 🧪 Tests

### Lancer tous les tests

```bash
cd /Users/jacquesmougeot/Desktop/BGC/Stratégies
python3 src/bloomberg/option_data_fetcher_test.py
```

### Tests inclus

1. **Test de connexion** - Vérifie la connexion au Terminal
2. **Option unique** - Récupère une option SPY CALL
3. **Chaîne d'options** - Récupère plusieurs strikes
4. **Format ticker** - Teste la construction des tickers Bloomberg
5. **Champs personnalisés** - Récupère des champs spécifiques

---

## 📊 Format des tickers Bloomberg

Le module construit automatiquement les tickers Bloomberg au bon format:

**Format:** `UNDERLYING MM/DD/YY C/P STRIKE Index/Equity`

**Exemples:**
- SPY CALL 450 exp 2024-12-20 → `SPY 12/20/24 C450 Index`
- AAPL PUT 175.5 exp 2024-11-15 → `AAPL 11/15/24 P175.5 Equity`
- QQQ CALL 380 exp 2025-01-17 → `QQQ 01/17/25 C380 Index`

**Suffixes:**
- `Index` : Pour les ETF et indices (SPY, QQQ, IWM, SPX)
- `Equity` : Pour les actions individuelles (AAPL, TSLA, etc.)

---

## 🔍 Champs Bloomberg disponibles

| Champ Bloomberg | Description | Type |
|-----------------|-------------|------|
| `PX_BID` | Prix Bid | float |
| `PX_ASK` | Prix Ask | float |
| `PX_LAST` | Dernier prix | float |
| `PX_MID` | Prix Mid | float |
| `DELTA` | Delta | float |
| `GAMMA` | Gamma | float |
| `VEGA` | Vega | float |
| `THETA` | Theta | float |
| `RHO` | Rho | float |
| `IVOL_MID` | Volatilité implicite | float |
| `OPEN_INT` | Open Interest | int |
| `PX_VOLUME` | Volume | int |
| `OPT_STRIKE_PX` | Strike | float |
| `OPT_EXPIRE_DT` | Date expiration | date |

---

## ⚠️ Troubleshooting

### Erreur: "Session Bloomberg non connectée"

**Solution:** Appelez `connect()` avant `get_option_data()`

```python
fetcher = BloombergOptionFetcher()
fetcher.connect()  # ← N'oubliez pas !
option = fetcher.get_option_data(...)
```

### Erreur: "Échec du démarrage de la session Bloomberg"

**Causes possibles:**
1. Bloomberg Terminal n'est pas ouvert
2. Vous n'êtes pas authentifié dans Bloomberg
3. Le port 8194 est bloqué

**Solution:**
- Ouvrir Bloomberg Terminal
- Se connecter avec vos identifiants
- Vérifier le pare-feu

### Erreur: "Échec de l'ouverture du service //blp/refdata"

**Solution:** Attendre quelques secondes que Bloomberg Terminal soit complètement chargé

### Option retourne `None`

**Causes possibles:**
1. Le ticker est mal formaté
2. L'option n'existe pas (strike/date invalides)
3. Pas de données disponibles

**Solution:**
- Vérifier que l'option existe sur Bloomberg Terminal
- Vérifier le format de la date ('YYYY-MM-DD')
- Essayer avec un strike proche de l'ATM

---

## 📝 Exemples complets

### Exemple 1: Scanner de volatilité implicite

```python
from bloomberg.option_data_fetcher import BloombergOptionFetcher

def scan_iv(underlying, expiration, strikes):
    """Scanne la volatilité implicite pour plusieurs strikes"""
    
    with BloombergOptionFetcher() as fetcher:
        options = fetcher.get_option_chain(
            underlying=underlying,
            expiration=expiration,
            strikes=strikes,
            option_types=['CALL']
        )
        
        print(f"\n📊 Volatilité Implicite - {underlying}")
        print("-" * 40)
        
        for opt in sorted(options, key=lambda x: x.strike):
            if opt.implied_volatility:
                print(f"Strike ${opt.strike:>6.2f} → IV: {opt.implied_volatility:>6.2f}%")

# Usage
scan_iv('SPY', '2024-12-20', [440, 445, 450, 455, 460])
```

### Exemple 2: Calculateur de spread

```python
def analyze_vertical_spread(underlying, expiration, long_strike, short_strike):
    """Analyse un vertical spread (Bull Call Spread)"""
    
    with BloombergOptionFetcher() as fetcher:
        # Acheter le call bas
        long_call = fetcher.get_option_data(underlying, 'CALL', long_strike, expiration)
        
        # Vendre le call haut
        short_call = fetcher.get_option_data(underlying, 'CALL', short_strike, expiration)
        
        if long_call and short_call:
            # Coût net du spread
            net_debit = long_call.last - short_call.last
            
            # Max profit = largeur - débit
            max_profit = (short_strike - long_strike) - net_debit
            
            # Greeks nets
            net_delta = long_call.delta - short_call.delta
            
            print(f"\n📊 Bull Call Spread: {underlying}")
            print(f"   Long  ${long_strike} CALL @ ${long_call.last:.2f}")
            print(f"   Short ${short_strike} CALL @ ${short_call.last:.2f}")
            print(f"   ───────────────────────────────")
            print(f"   Net Debit:  ${net_debit:.2f}")
            print(f"   Max Profit: ${max_profit:.2f}")
            print(f"   Net Delta:  {net_delta:.4f}")

# Usage
analyze_vertical_spread('SPY', '2024-12-20', 445, 455)
```

### Exemple 3: Comparaison CALL vs PUT

```python
def compare_call_put(underlying, expiration, strike):
    """Compare le CALL et PUT au même strike"""
    
    with BloombergOptionFetcher() as fetcher:
        call = fetcher.get_option_data(underlying, 'CALL', strike, expiration)
        put = fetcher.get_option_data(underlying, 'PUT', strike, expiration)
        
        if call and put:
            print(f"\n📊 {underlying} Strike ${strike} - Exp: {expiration}")
            print(f"{'Métrique':<20} {'CALL':<15} {'PUT':<15}")
            print("-" * 50)
            print(f"{'Prix':<20} ${call.last:<14.2f} ${put.last:<14.2f}")
            print(f"{'Delta':<20} {call.delta:<14.4f} {put.delta:<14.4f}")
            print(f"{'Gamma':<20} {call.gamma:<14.4f} {put.gamma:<14.4f}")
            print(f"{'Vega':<20} {call.vega:<14.4f} {put.vega:<14.4f}")
            print(f"{'Theta':<20} {call.theta:<14.4f} {put.theta:<14.4f}")
            print(f"{'IV':<20} {call.implied_volatility:<14.2f}% {put.implied_volatility:<14.2f}%")

# Usage
compare_call_put('SPY', '2024-12-20', 450)
```

---

## 📚 Ressources

- [Bloomberg API Documentation](https://www.bloomberg.com/professional/support/api-library/)
- [blpapi Python Documentation](https://github.com/Bloomberg-Beta/blpapi-python)
- [Options Greeks Explained](https://www.investopedia.com/terms/g/greeks.asp)

---

## 🤝 Support

Pour toute question ou problème:
1. Vérifier la section Troubleshooting ci-dessus
2. Lancer les tests: `python3 option_data_fetcher_test.py`
3. Consulter les logs pour plus de détails

---

## 📄 License

© 2025 BGC Trading Desk - Usage interne uniquement

---

**Dernière mise à jour:** 15 octobre 2025
