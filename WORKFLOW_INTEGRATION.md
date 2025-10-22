# Intégration du Workflow Complet Bloomberg → Stratégies

## 📋 Résumé des Modifications

### 1. **Fichier `main.py`** (NOUVEAU)
Workflow complet implémenté avec 2 fonctions principales :

#### `run_complete_workflow()`
Exécute le pipeline complet :
```
Bloomberg Data → Options → Stratégies → Ranking
```

**Paramètres:**
- `bloomberg_data`: Liste de dictionnaires Bloomberg
- `target_price`: Prix cible du sous-jacent
- `price_min` / `price_max`: Intervalle pour surfaces
- `max_legs`: Nombre max d'options par stratégie (1-4)
- `top_n`: Nombre de meilleures stratégies à retourner
- `scoring_weights`: Poids personnalisés (optionnel)

**Retourne:** Liste des top N stratégies classées

#### `run_workflow_with_target_prices()`
Version multi-prix pour tester plusieurs prix cibles

**Utilise:**
- `bloomberg_data_to_options()` pour la conversion
- `OptionStrategyGeneratorV2` pour générer toutes les combinaisons
- `StrategyComparerV2` pour le ranking

### 2. **Fichier `app.py`** (MODIFIÉ)

#### Nouveaux Imports
```python
from myproject.option.option_generator_v2 import OptionStrategyGeneratorV2
from myproject.option.comparor_v2 import StrategyComparerV2
from myproject.option.dic_to_option import bloomberg_data_to_options
```

#### Modifications du Sidebar
- **Ajout:** Slider `max_legs` (1-4) pour contrôler la complexité des stratégies
- **Supprimé:** Checkboxes `include_flies`, `include_condors`, `require_symmetric` (obsolètes)
- **Conservé:** `top_n_structures` pour limiter l'affichage

#### Nouveau Workflow dans `compare_button`

**ÉTAPE 1 : Import Bloomberg**
```python
data = load_options_from_bloomberg(bloomberg_params)
# → Sauvegarde optionnelle en JSON
# → Affichage du nombre d'options
```

**ÉTAPE 2 : Conversion et Génération**
```python
# Conversion Bloomberg → Options
options = bloomberg_data_to_options(
    bloomberg_data=data['options'],
    default_position='long',
    price_min=price_min,
    price_max=price_max
)

# Génération de toutes les stratégies (1 à max_legs)
generator = OptionStrategyGeneratorV2(options)
all_strategies = generator.generate_all_combinations(
    target_price=target_price_median,
    price_min=price_min,
    price_max=price_max,
    max_legs=max_legs
)
```

**ÉTAPE 3 : Comparaison et Ranking**
```python
comparer = StrategyComparerV2()
best_strategies = comparer.compare_and_rank(
    strategies=all_strategies,
    top_n=top_n_structures,
    weights=scoring_weights
)
```

## 🔄 Flux de Données

```
┌─────────────────────────┐
│   Bloomberg Terminal    │
│  (import_euribor_options)│
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Liste de Dictionnaires │
│   (bloomberg_data)      │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ bloomberg_data_to_options│
│   (dic_to_option.py)    │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   Liste d'Options       │
│   (Option objects)      │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ OptionStrategyGeneratorV2│
│  generate_all_combinations│
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ Toutes les Stratégies   │
│  (1 à 4 legs, 2^k pos.) │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   StrategyComparerV2    │
│   compare_and_rank      │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Top N Stratégies       │
│   (ranked & scored)     │
└─────────────────────────┘
```

## 📊 Scoring System

Le système de scoring utilise 6 critères pondérés :

| Critère | Poids par défaut | Description |
|---------|------------------|-------------|
| `max_profit` | 15% | Profit maximum possible |
| `risk_reward` | 15% | Ratio risque/récompense (inversé) |
| `profit_zone` | 10% | Largeur de la zone profitable |
| `target_performance` | 10% | Performance au prix cible |
| `surface_gauss` | 35% | Surface profit pondérée (PRIORITAIRE) |
| `profit_loss_ratio` | 15% | Ratio surface_profit/surface_loss |

## 🎯 Exemple d'Utilisation

### Dans un script Python :
```python
from myproject.option.main import run_complete_workflow
from myproject.bloomberg_data_importer import import_euribor_options

# Import Bloomberg
data = import_euribor_options(
    underlying='EURIBOR',
    months=['F', 'G', 'H'],
    years=[2025],
    strikes=[95.0, 96.0, 97.0, ..., 105.0]
)

# Workflow complet
best_strategies = run_complete_workflow(
    bloomberg_data=data['options'],
    target_price=100.0,
    price_min=85.0,
    price_max=115.0,
    max_legs=4,
    top_n=10
)

# Afficher les résultats
for s in best_strategies[:5]:
    print(f"#{s.rank}: {s.strategy_name} - Score: {s.score:.3f}")
```

### Dans Streamlit (app.py) :
1. Configurer les paramètres dans le sidebar
2. Cliquer sur "🚀 COMPARER"
3. Le système :
   - Importe les données Bloomberg
   - Convertit en Options
   - Génère toutes les stratégies
   - Classe et affiche le top N

## ✅ Tests de Validation

### Test du workflow (main.py)
```bash
python src/myproject/option/main.py
```
**Sortie attendue:**
- Conversion de 5 options
- Génération de ~35-70 stratégies (selon max_legs)
- Top 10 classé avec scores et métriques

### Test de l'application (app.py)
```bash
streamlit run src/myproject/app.py
```
**Fonctionnalités:**
- Import Bloomberg interactif
- Sliders pour max_legs et poids
- Tableaux et graphiques des résultats

## 🚀 Améliorations Futures

1. **Performance:**
   - Cache des surfaces calculées
   - Parallélisation du calcul des stratégies

2. **Fonctionnalités:**
   - Filtres par type de stratégie
   - Export des résultats en Excel
   - Backtesting des stratégies

3. **Interface:**
   - Graphiques interactifs de P&L
   - Comparaison côte-à-côte
   - Alertes sur critères personnalisés

## 📝 Notes Techniques

- **Type Safety:** Utilise `Literal['long', 'short']` pour les positions
- **Error Handling:** Toutes les étapes incluent validation et messages
- **Modularité:** Chaque fonction est réutilisable indépendamment
- **Compatibilité:** Compatible avec l'ancien workflow `MultiStructureComparer`
