# Guide de Démarrage Rapide 🚀

## Installation & Test en 3 étapes

### 1️⃣ Vérifier Bloomberg Terminal

```bash
# Ouvrir Bloomberg Terminal et se connecter
# Attendre que le terminal soit complètement chargé
```

### 2️⃣ Tester la connexion

```bash
cd /Users/jacquesmougeot/Desktop/BGC/Stratégies
python3 src/bloomberg/option_data_fetcher_test.py
```

Si tous les tests passent ✅, vous êtes prêt !

### 3️⃣ Utiliser dans votre code

```python
from bloomberg import BloombergOptionFetcher

# Méthode simple
with BloombergOptionFetcher() as fetcher:
    option = fetcher.get_option_data('SPY', 'CALL', 450.0, '2024-12-20')
    print(f"Delta: {option.delta}")
```

---

## 📖 Exemples Courants

### Récupérer un CALL unique

```python
from bloomberg import BloombergOptionFetcher

with BloombergOptionFetcher() as fetcher:
    call = fetcher.get_option_data(
        underlying='SPY',      # Ticker
        option_type='CALL',    # CALL ou PUT
        strike=450.0,          # Strike
        expiration='2024-12-20'  # YYYY-MM-DD
    )
    
    print(f"Prix: ${call.last}")
    print(f"Delta: {call.delta}")
    print(f"IV: {call.implied_volatility}%")
```

### Récupérer plusieurs options

```python
from bloomberg import BloombergOptionFetcher, format_option_table

strikes = [440, 445, 450, 455, 460]

with BloombergOptionFetcher() as fetcher:
    options = fetcher.get_option_chain(
        underlying='SPY',
        expiration='2024-12-20',
        strikes=strikes,
        option_types=['CALL', 'PUT']  # Les deux types
    )
    
    # Afficher en tableau
    print(format_option_table(options))
```

### Analyser un Spread

```python
with BloombergOptionFetcher() as fetcher:
    # Bull Call Spread: Long 445 CALL, Short 455 CALL
    long = fetcher.get_option_data('SPY', 'CALL', 445, '2024-12-20')
    short = fetcher.get_option_data('SPY', 'CALL', 455, '2024-12-20')
    
    net_debit = long.last - short.last
    max_profit = (455 - 445) - net_debit
    
    print(f"Coût: ${net_debit:.2f}")
    print(f"Max Profit: ${max_profit:.2f}")
```

---

## 🔍 Données Disponibles

Chaque option retourne un objet `OptionData` avec:

**Prix:**
- `bid` - Prix Bid
- `ask` - Prix Ask
- `last` - Dernier prix
- `mid` - Prix Mid

**Greeks:**
- `delta` - Sensibilité au prix du sous-jacent
- `gamma` - Sensibilité du delta
- `vega` - Sensibilité à la volatilité
- `theta` - Déclin temporel (time decay)
- `rho` - Sensibilité aux taux d'intérêt

**Autres:**
- `implied_volatility` - Volatilité implicite (%)
- `open_interest` - Open Interest
- `volume` - Volume du jour

---

## ⚡ Commandes Utiles

```bash
# Lancer tous les tests
python3 src/bloomberg/option_data_fetcher_test.py

# Voir des exemples
python3 src/bloomberg/quick_example.py

# Documentation complète
cat src/bloomberg/README.md
```

---

## ⚠️ Troubleshooting

**Erreur: "Session Bloomberg non connectée"**
→ Vérifiez que Bloomberg Terminal est ouvert et connecté

**Erreur: "Option retourne None"**
→ Vérifiez que l'option existe (strike et date valides)

**Erreur: "ModuleNotFoundError: blpapi"**
→ Installez: `pip install blpapi`

---

## 📚 Plus d'Info

- **Documentation complète:** `src/bloomberg/README.md`
- **Code source:** `src/bloomberg/option_data_fetcher.py`
- **Tests:** `src/bloomberg/option_data_fetcher_test.py`
- **Exemples:** `src/bloomberg/quick_example.py`

---

**Besoin d'aide?** Consultez le README.md complet ! 📖
