# Guide Complet - Module C++ pour les Calculs de Strategies

## Table des Matieres

1. [Architecture Generale](#1-architecture-generale)
2. [Structures de Donnees](#2-structures-de-donnees)
3. [Flux de Donnees](#3-flux-de-donnees)
4. [Cache Global](#4-cache-global)
5. [Fonctions Exposees a Python](#5-fonctions-exposees-a-python)
6. [Logique de Calcul](#6-logique-de-calcul)
7. [Interface Python](#7-interface-python)
8. [Performances](#8-performances)
9. [Compilation](#9-compilation)
10. [Resume du Flux Complet](#10-resume-du-flux-complet)

---

## 1. Architecture Generale

Le module C++ est concu pour accelerer le calcul des metriques de strategies d'options. Il remplace les boucles Python par du code compile optimise.

### Structure des fichiers

```
src/myproject/strategy/cpp/
    strategy_metrics.hpp    # Declarations (structures + classe)
    strategy_metrics.cpp    # Implementations des calculs
    bindings.cpp            # Interface Python via pybind11
    setup.py                # Configuration de compilation
```

### Module produit

Le module compile s'appelle `strategy_metrics_cpp` et est importe directement en Python :

```python
import strategy_metrics_cpp
```

---

## 2. Structures de Donnees

### 2.1 OptionData (donnees d'entree)

Structure representant une seule option. Definie dans `strategy_metrics.hpp` :

```cpp
struct OptionData {
    double premium;                    // Prime de l'option
    double delta;                      // Sensibilite au sous-jacent
    double gamma;                      // Derivee seconde (courbure)
    double vega;                       // Sensibilite a la volatilite
    double theta;                      // Decay temporel
    double implied_volatility;         // Volatilite implicite
    double average_pnl;                // P&L moyen pondere par la mixture
    double sigma_pnl;                  // Ecart-type du P&L
    double strike;                     // Prix d'exercice
    double profit_surface_ponderated;  // Surface profit ponderee (calcule dynamiquement)
    double loss_surface_ponderated;    // Surface perte ponderee (calcule dynamiquement)
    double roll;                       // Roll moyen normalise
    double roll_quarterly;             // Roll Q-1 (trimestre precedent)
    double roll_sum;                   // Roll brut non normalise
    bool is_call;                      // True = Call, False = Put
};
```

### 2.2 StrategyMetrics (donnees de sortie)

Structure retournee apres calcul. Contient toutes les metriques :

```cpp
struct StrategyMetrics {
    // Greeks agreges
    double total_premium;
    double total_delta;
    double total_gamma;
    double total_vega;
    double total_theta;
    double total_iv;
    
    // P&L metrics
    double max_profit;
    double max_loss;
    double max_loss_left;        // Max loss a gauche de average_mix
    double max_loss_right;       // Max loss a droite de average_mix
    double total_average_pnl;
    double total_sigma_pnl;
    
    // Surfaces
    double surface_profit_nonponderated;
    double surface_loss_nonponderated;
    double total_profit_surface_ponderated;
    double total_loss_surface_ponderated;
    
    // Profit zone
    double min_profit_price;
    double max_profit_price;
    double profit_zone_width;
    
    // Counts
    int call_count;
    int put_count;
    
    // Roll
    double total_roll;
    double total_roll_quarterly;
    double total_roll_sum;
    
    // Arrays dynamiques
    std::vector<double> breakeven_points;
    std::vector<double> total_pnl_array;
};
```

### 2.3 Tableau recapitulatif des metriques

| Categorie | Champs |
|-----------|--------|
| Greeks | `total_premium`, `total_delta`, `total_gamma`, `total_vega`, `total_theta`, `total_iv` |
| P&L | `max_profit`, `max_loss`, `max_loss_left`, `max_loss_right`, `total_average_pnl`, `total_sigma_pnl` |
| Surfaces | `surface_profit_nonponderated`, `surface_loss_nonponderated`, `total_profit_surface_ponderated`, `total_loss_surface_ponderated` |
| Zone Profit | `min_profit_price`, `max_profit_price`, `profit_zone_width` |
| Counts | `call_count`, `put_count` |
| Roll | `total_roll`, `total_roll_quarterly`, `total_roll_sum` |
| Arrays | `breakeven_points`, `total_pnl_array` |

---

## 3. Flux de Donnees

### 3.1 Schema global

```
Python                           C++                              Python
   |                              |                                  |
   |  init_options_cache()        |                                  |
   |----------------------------->|                                  |
   |  (numpy arrays)              |  Stockage dans g_cache           |
   |                              |  (OptionsCache global)           |
   |                              |                                  |
   |  process_combinations_batch()|                                  |
   |----------------------------->|                                  |
   |  (indices, signs, filtres)   |  Pour chaque combo:              |
   |                              |    1. Extraire options du cache  |
   |                              |    2. Appeler calculate()        |
   |                              |    3. Si valide, ajouter result  |
   |                              |                                  |
   |                              |  Retour liste de tuples          |
   |<-----------------------------|                                  |
   |                              |                                  |
   |  batch_to_strategies()       |                                  |
   |----------------------------->|                                  |
   |  Conversion en               |                                  |
   |  StrategyComparison          |                                  |
```

### 3.2 Etapes detaillees

1. **Initialisation** : Python envoie toutes les donnees des options au cache C++
2. **Preparation** : Python genere les combinaisons (indices + signes)
3. **Traitement** : C++ filtre et calcule les metriques pour chaque combinaison
4. **Conversion** : Python convertit les resultats en objets `StrategyComparison`

---

## 4. Cache Global

Le cache evite de passer les donnees a chaque appel. Defini dans `bindings.cpp` :

```cpp
struct OptionsCache {
    std::vector<OptionData> options;              // Toutes les options
    std::vector<std::vector<double>> pnl_matrix;  // Matrice P&L [n_options x pnl_length]
    std::vector<double> prices;                   // Prix du sous-jacent
    std::vector<double> mixture;                  // Distribution de probabilite
    double average_mix;                           // Point de separation left/right
    size_t n_options;                             // Nombre d'options
    size_t pnl_length;                            // Taille du P&L array
    bool valid;                                   // Cache initialise?
};

static OptionsCache g_cache;  // Instance globale
```

### Pourquoi un cache ?

- **Performance** : Les donnees sont copiees une seule fois de Python vers C++
- **Simplicite** : Les appels suivants ne passent que les indices et signes
- **Memoire** : La matrice P&L peut etre volumineuse (n_options x pnl_length)

---

## 5. Fonctions Exposees a Python

### 5.1 init_options_cache()

Initialise le cache avec toutes les donnees des options.

**Signature :**
```python
strategy_metrics_cpp.init_options_cache(
    premiums,         # np.array float64 [n_options]
    deltas,           # np.array float64 [n_options]
    gammas,           # np.array float64 [n_options]
    vegas,            # np.array float64 [n_options]
    thetas,           # np.array float64 [n_options]
    ivs,              # np.array float64 [n_options]
    average_pnls,     # np.array float64 [n_options]
    sigma_pnls,       # np.array float64 [n_options]
    strikes,          # np.array float64 [n_options]
    is_calls,         # np.array bool [n_options]
    rolls,            # np.array float64 [n_options]
    rolls_quarterly,  # np.array float64 [n_options]
    rolls_sum,        # np.array float64 [n_options]
    pnl_matrix,       # np.array float64 [n_options x pnl_length]
    prices,           # np.array float64 [pnl_length]
    mixture,          # np.array float64 [pnl_length]
    average_mix       # float
)
```

**Usage :**
```python
from batch_processor import init_cpp_cache

success = init_cpp_cache(options)  # Wrapper Python
```

### 5.2 process_combinations_batch()

Traite un batch de combinaisons et retourne les strategies valides.

**Signature :**
```python
results = strategy_metrics_cpp.process_combinations_batch(
    indices_batch,     # np.array int32 [n_combos x max_legs], -1 pour padding
    signs_batch,       # np.array int32 [n_combos x max_legs], +1=long, -1=short
    combo_sizes,       # np.array int32 [n_combos], nombre de legs par combo
    max_loss_left,     # float, perte max autorisee a gauche
    max_loss_right,    # float, perte max autorisee a droite
    max_premium_params,# float, premium max autorise
    ouvert_gauche,     # int, short puts non couverts autorises
    ouvert_droite,     # int, short calls non couverts autorises
    min_premium_sell,  # float, premium minimum pour vendre
    delta_min,         # float, borne inferieure du delta
    delta_max          # float, borne superieure du delta
)
```

**Retour :**
```python
# Liste de tuples pour les strategies valides
[
    ([idx1, idx2], [sign1, sign2], {metrics_dict}),
    ([idx3], [sign3], {metrics_dict}),
    ...
]
```

### 5.3 calculate_strategy_metrics()

Calcule les metriques d'une seule strategie (sans utiliser le cache).

Utilise pour des calculs ponctuels. Combine les parametres de `init_options_cache` et les filtres.

**Retour :** `dict` avec les metriques ou `None` si la strategie est invalide.

---

## 6. Logique de Calcul

### 6.1 Fonction principale : StrategyCalculator::calculate()

Definie dans `strategy_metrics.cpp`. Processus en 4 etapes :

```
calculate() {
    1. VALIDATION
       - Verifier n_options > 0
       - Verifier coherence des tailles

    2. FILTRES (early exit)
       - filter_useless_sell()
       - filter_same_option_buy_sell()
       - filter_put_count()
       - filter_call_open()
       - filter_premium()
       - filter_delta()
       - filter_average_pnl()

    3. CALCULS
       - calculate_greeks()
       - calculate_total_pnl()
       - Calcul max_loss_left/right
       - Filtres sur max_loss
       - calculate_breakeven_points()
       - calculate_profit_zone()
       - Calcul surfaces et sigma_pnl
       - Agregation des rolls

    4. CONSTRUCTION RESULTAT
       - Remplir StrategyMetrics
       - Retourner std::optional
}
```

### 6.2 Filtres (early exit pattern)

Chaque filtre retourne `false` si la strategie doit etre rejetee, permettant un early exit avant les calculs couteux.

| Filtre | Condition de rejet |
|--------|-------------------|
| `filter_useless_sell` | Une option vendue a `premium < min_premium_sell` |
| `filter_same_option_buy_sell` | Meme strike + meme type + signes opposes |
| `filter_put_count` | `(short_puts - long_puts) > ouvert_gauche` |
| `filter_call_open` | `(short_calls - long_calls) > ouvert_droite` |
| `filter_premium` | `abs(total_premium) > max_premium_params` |
| `filter_delta` | `delta < delta_min` OU `delta > delta_max` |
| `filter_average_pnl` | `total_average_pnl < 0` |

### 6.3 Calculs principaux

#### calculate_total_pnl()

Produit scalaire entre les signes et la matrice P&L :

```cpp
// Dot product: signs @ pnl_matrix
for (size_t i = 0; i < n_options; ++i) {
    const double s = static_cast<double>(signs[i]);
    for (size_t j = 0; j < pnl_length; ++j) {
        total_pnl[j] += s * pnl_matrix[i][j];
    }
}
```

#### calculate_breakeven_points()

Detection des changements de signe avec interpolation lineaire :

```cpp
for (size_t i = 0; i < pnl.size() - 1; ++i) {
    if (pnl[i] * pnl[i+1] < 0.0) {  // Changement de signe
        double t = -pnl[i] / (pnl[i+1] - pnl[i]);
        double breakeven = prices[i] + (prices[i+1] - prices[i]) * t;
        breakevens.push_back(breakeven);
    }
}
```

#### Max Loss Left/Right

Separation du P&L en deux zones basee sur `average_mix` :

```cpp
// Trouver l'index de separation
size_t split_idx = 0;
for (size_t i = 0; i < prices.size(); ++i) {
    if (prices[i] >= average_mix) {
        split_idx = i;
        break;
    }
}

// Max loss a gauche (indices 0 a split_idx)
for (size_t i = 0; i < split_idx; ++i) {
    if (total_pnl[i] < max_loss_left) {
        max_loss_left = total_pnl[i];
    }
}

// Max loss a droite (split_idx a fin)
for (size_t i = split_idx; i < total_pnl.size(); ++i) {
    if (total_pnl[i] < max_loss_right) {
        max_loss_right = total_pnl[i];
    }
}
```

#### Agregation des rolls

```cpp
double total_roll = 0.0;
double total_roll_quarterly = 0.0;
double total_roll_sum = 0.0;

for (size_t i = 0; i < options.size(); ++i) {
    total_roll += signs[i] * options[i].roll;
    total_roll_quarterly += signs[i] * options[i].roll_quarterly;
    total_roll_sum += signs[i] * options[i].roll_sum;
}
```

---

## 7. Interface Python

### 7.1 batch_processor.py

Wrapper Python pour le module C++.

#### init_cpp_cache()

Prepare les arrays numpy et appelle le C++ :

```python
def init_cpp_cache(options: List[Option]) -> bool:
    n = len(options)
    
    # Extraction des donnees en arrays numpy
    premiums = np.array([opt.premium for opt in options], dtype=np.float64)
    deltas = np.array([opt.delta for opt in options], dtype=np.float64)
    # ... autres arrays ...
    
    # Construction de la matrice P&L
    pnl_length = len(options[0].pnl_array)
    pnl_matrix = np.zeros((n, pnl_length), dtype=np.float64)
    for i, opt in enumerate(options):
        pnl_matrix[i] = opt.pnl_array
    
    # Appel C++
    strategy_metrics_cpp.init_options_cache(
        premiums, deltas, gammas, vegas, thetas, ivs,
        average_pnls, sigma_pnls, strikes,
        is_calls, rolls, rolls_quarterly, rolls_sum,
        pnl_matrix, prices, mixture, average_mix
    )
    return True
```

#### prepare_batch_data_by_legs()

Genere les combinaisons pour un nombre de legs specifique :

```python
def prepare_batch_data_by_legs(options, n_legs, max_legs=4):
    all_combos = []
    all_signs = []
    
    sign_variants = list(product([-1, 1], repeat=n_legs))
    
    for combo in combinations_with_replacement(options, n_legs):
        # Verifier meme expiration
        if n_legs > 1:
            if combo[0].expiration_month != combo[-1].expiration_month:
                continue
        
        indices = [option_to_idx[id(opt)] for opt in combo]
        
        # Toutes les variantes de signes
        for signs in sign_variants:
            all_combos.append(indices)
            all_signs.append(signs)
    
    # Conversion en numpy avec padding
    indices_batch = np.full((n_combos, max_legs), -1, dtype=np.int32)
    signs_batch = np.zeros((n_combos, max_legs), dtype=np.int32)
    
    return indices_batch, signs_batch, combo_sizes, n_combos
```

#### batch_to_strategies()

Convertit les resultats C++ en objets `StrategyComparison` :

```python
def batch_to_strategies(results, options):
    strategies = []
    
    for indices, signs, metrics in results:
        opts = [options[i] for i in indices]
        signs_arr = np.array(signs, dtype=np.float64)
        
        # Calcul rolls_detail en Python (types complexes)
        total_rolls_detail = {}
        for i, opt in enumerate(opts):
            if opt.rolls_detail:
                for label, value in opt.rolls_detail.items():
                    if label not in total_rolls_detail:
                        total_rolls_detail[label] = 0.0
                    total_rolls_detail[label] += signs_arr[i] * value
        
        strat = StrategyComparison(
            premium=metrics['total_premium'],
            total_delta=metrics['total_delta'],
            rolls_detail=total_rolls_detail,
            # ... autres champs ...
        )
        strategies.append(strat)
    
    return strategies
```

### 7.2 Note sur rolls_detail

Le champ `rolls_detail` (dictionnaire label -> valeur) est calcule cote Python apres l'appel C++ car :

- Les types complexes (Dict[str, float]) sont difficiles a passer entre C++ et Python
- Le calcul est simple (agregation) et ne beneficie pas de l'acceleration C++
- Cela maintient l'interface C++ simple et generique

---

## 8. Performances

### 8.1 Optimisations implementees

| Technique | Description |
|-----------|-------------|
| Cache global | Donnees copiees une seule fois de Python vers C++ |
| Early exit | Filtres eliminent les strategies invalides avant les calculs couteux |
| Structures plates | `OptionData` est POD (Plain Old Data) pour bonne localite cache |
| Pre-allocation | Vecteurs reserves avant les boucles |
| Batch processing | Milliers de combinaisons en un seul appel Python -> C++ |

### 8.2 Complexite

| Operation | Complexite |
|-----------|-----------|
| Initialisation cache | O(n_options * pnl_length) |
| Par combinaison | O(n_legs * pnl_length) |
| Total batch | O(n_combos * n_legs * pnl_length) |

### 8.3 Gains typiques

- **Sans C++** : ~1000 strategies/seconde en Python pur
- **Avec C++** : ~50000 strategies/seconde (x50 acceleration)

---

## 9. Compilation

### 9.1 Prerequis

- Python 3.8+
- pybind11
- Compilateur C++ avec support C++17 (MSVC, GCC, Clang)

### 9.2 Fichier setup.py

```python
from pybind11.setup_helpers import Pybind11Extension, build_ext
from setuptools import setup

ext_modules = [
    Pybind11Extension(
        "strategy_metrics_cpp",
        ["strategy_metrics.cpp", "bindings.cpp"],
        cxx_std=17,
    ),
]

setup(
    name="strategy_metrics_cpp",
    version="1.0.0",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
    install_requires=["pybind11>=2.6"],
)
```

### 9.3 Commandes de compilation

```bash
# Installation du module
cd src/myproject/strategy/cpp
pip install -e .

# Ou en mode development
pip install -e . --no-build-isolation
```

### 9.4 Verification

```python
import strategy_metrics_cpp
print(strategy_metrics_cpp.__doc__)
```

---

## 10. Resume du Flux Complet

### Etape par etape

1. **Importation Bloomberg**
   - Recuperation des donnees d'options via l'API Bloomberg
   - Creation d'objets `Option` avec toutes les metriques

2. **Initialisation du cache C++**
   ```python
   init_cpp_cache(options)
   ```
   - Copie des donnees dans le cache global C++

3. **Generation des combinaisons par nombre de legs**
   ```python
   for n_legs in [1, 2, 3, 4]:
       indices, signs, sizes, n_combos = prepare_batch_data_by_legs(options, n_legs)
   ```

4. **Traitement batch C++**
   ```python
   results = process_combinations_batch(indices, signs, sizes, filtres...)
   ```
   - Filtrage et calcul des metriques en C++

5. **Conversion en objets Python**
   ```python
   strategies = batch_to_strategies(results, options)
   ```
   - Creation des `StrategyComparison`
   - Calcul de `rolls_detail` cote Python

6. **Affichage**
   - Tableau de comparaison avec colonnes dynamiques

### Schema recapitulatif

```
Bloomberg API
     |
     v
List[Option]
     |
     v
init_cpp_cache() -----> g_cache (C++)
     |
     v
prepare_batch_data_by_legs()
     |
     v
process_combinations_batch() -----> StrategyCalculator::calculate()
     |                                    |
     v                                    v
List[(indices, signs, metrics)]      Filtres + Calculs
     |
     v
batch_to_strategies()
     |
     v
List[StrategyComparison]
     |
     v
Tableau de comparaison
```

---

## Annexes

### A. Liste complete des filtres

1. **filter_useless_sell** : Rejette si une option vendue a un premium inferieur au seuil
2. **filter_same_option_buy_sell** : Rejette si achat et vente de la meme option
3. **filter_put_count** : Rejette si trop de puts vendus non couverts
4. **filter_call_open** : Rejette si trop de calls vendus non couverts
5. **filter_premium** : Rejette si premium total hors limites
6. **filter_delta** : Rejette si delta total hors bornes
7. **filter_average_pnl** : Rejette si P&L moyen negatif
8. **max_loss_left/right** : Rejette si perte max trop importante

### B. Metriques retournees

| Metrique | Description | Formule |
|----------|-------------|---------|
| total_premium | Somme des primes | sum(sign * premium) |
| total_delta | Delta de la strategie | sum(sign * delta) |
| max_profit | Profit maximum | max(pnl_array) |
| max_loss | Perte maximum | min(pnl_array) |
| breakeven_points | Points d'equilibre | Interpolation lineaire |
| profit_zone_width | Largeur zone profit | max_profit_price - min_profit_price |

### C. Types Python correspondants

| Type C++ | Type Python |
|----------|-------------|
| double | float64 |
| int | int32 |
| bool | bool |
| std::vector<double> | np.ndarray |
| std::optional<T> | T ou None |
