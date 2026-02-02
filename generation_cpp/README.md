# Module C++ pour les calculs de stratégies d'options

## Architecture

Ce module C++ optimise les calculs "hot path" du moteur de stratégies :

### Python (garde tel quel)
- Génération des combinaisons d'options
- Filtrage par expiration
- Extraction des données des objets `Option`
- Création finale de `StrategyComparison`
- Génération du nom de stratégie

### C++ (partie chaude 🔥)
- Tous les calculs numériques (Greeks, P&L, surfaces)
- Tous les filtres de validation
- Tous les `return None` (early exit optimisés)

Le C++ retourne soit :
- `None` (stratégie invalide)
- Un dictionnaire Python avec toutes les métriques calculées

## Performance attendue

- **5-10x plus rapide** sur les calculs de métriques
- **Meilleure localité de cache** (structures de données plates)
- **Early exit optimisés** (les filtres arrêtent le calcul dès qu'une condition échoue)

## Installation

### Prérequis

```bash
pip install pybind11
```

### Compilation avec pip (recommandé)

```bash
cd src/myproject/strategy/cpp
pip install .
```

### Compilation avec CMake

```bash
cd src/myproject/strategy/cpp
chmod +x build.sh
./build.sh
```

### Copier le module

Après compilation, copiez le fichier `.so` (Linux/Mac) ou `.pyd` (Windows) dans le répertoire `strategy/` :

```bash
cp build/strategy_metrics_cpp*.so ..
```

## Utilisation

```python
# Import automatique avec fallback
from myproject.strategy.calcul_linear_metrics_cpp import create_strategy_fast_with_signs

# Utilisation identique à l'ancienne fonction
result = create_strategy_fast_with_signs(
    options, signs, max_loss_params, max_premium_params, ouvert
)
```

Si le module C++ n'est pas disponible, la fonction utilise automatiquement l'implémentation Python pure.

## Structure des fichiers

```
cpp/
├── strategy_metrics.hpp    # Header C++ avec les structures
├── strategy_metrics.cpp    # Implémentation des calculs
├── bindings.cpp            # Bindings pybind11
├── CMakeLists.txt          # Configuration CMake
├── setup.py                # Configuration pip
├── build.sh                # Script de compilation
└── README.md               # Ce fichier
```

## API C++

### `StrategyMetrics` (struct retournée)

| Champ | Type | Description |
|-------|------|-------------|
| `total_premium` | double | Prime totale |
| `total_delta` | double | Delta agrégé |
| `total_gamma` | double | Gamma agrégé |
| `total_vega` | double | Vega agrégé |
| `total_theta` | double | Theta agrégé |
| `total_iv` | double | IV moyenne |
| `max_profit` | double | Profit maximum |
| `max_loss` | double | Perte maximum |
| `breakeven_points` | vector<double> | Points d'équilibre |
| `total_pnl_array` | vector<double> | Courbe P&L |
| ... | | |

### Filtres implémentés

1. **Vente inutile** : Premium < 0.04 sur une vente
2. **Call count** : `call_count > -1`
3. **Même option achat/vente** : Détection des combinaisons inutiles
4. **Put count** : Validation selon `ouvert`
5. **Premium** : `|total_premium| <= max_premium_params`
6. **Delta** : `|total_delta| <= 0.75`
7. **Average P&L** : `total_average_pnl >= 0`
8. **Max loss** : `max_loss >= -max_loss_params`
