"""
Benchmark comparatif C++ vs Python pour le calcul de stratégies d'options
=========================================================================
Test de performance avec un grand nombre de combinaisons
"""

import numpy as np
import time
from itertools import product, combinations_with_replacement

# ============================================================================
# CONFIGURATION DU TEST
# ============================================================================

N_OPTIONS = 50  # Nombre d'options simulées
PNL_LENGTH = 500  # Longueur du vecteur P&L
MAX_LEGS = 4  # Nombre max de legs (2=rapide, 3=moyen, 4=lent)

# ============================================================================
# GÉNÉRATION DE DONNÉES DE TEST
# ============================================================================

def generate_test_data(n_options: int, pnl_length: int):
    """Génère des données de test réalistes"""
    np.random.seed(42)
    
    premiums = np.random.uniform(0.01, 0.5, n_options)
    deltas = np.random.uniform(-0.8, 0.8, n_options)
    gammas = np.random.uniform(0.01, 0.1, n_options)
    vegas = np.random.uniform(0.1, 2.0, n_options)
    thetas = np.random.uniform(-0.05, -0.001, n_options)
    ivs = np.random.uniform(0.15, 0.45, n_options)
    avg_pnls = np.random.uniform(-0.1, 0.3, n_options)
    sigma_pnls = np.random.uniform(0.05, 0.2, n_options)
    strikes = np.linspace(90, 110, n_options)
    profit_surf = np.random.uniform(0.1, 1.0, n_options)
    loss_surf = np.random.uniform(0.1, 1.0, n_options)
    is_calls = np.random.choice([True, False], n_options)
    
    prices = np.linspace(80, 120, pnl_length)
    pnl_matrix = np.random.randn(n_options, pnl_length) * 0.5
    
    # Simuler des expirations (pour le filtrage)
    # Grouper par paquets pour simuler des options de même expiration
    expirations = []
    n_groups = n_options // 10
    for i in range(n_options):
        group = i // 10
        expirations.append((2026, 'F' if group % 2 == 0 else 'G', 1, 15))
    
    return {
        'premiums': premiums,
        'deltas': deltas,
        'gammas': gammas,
        'vegas': vegas,
        'thetas': thetas,
        'ivs': ivs,
        'avg_pnls': avg_pnls,
        'sigma_pnls': sigma_pnls,
        'strikes': strikes,
        'profit_surf': profit_surf,
        'loss_surf': loss_surf,
        'is_calls': is_calls,
        'prices': prices,
        'pnl_matrix': pnl_matrix,
        'expirations': expirations
    }

# ============================================================================
# TEST C++ BATCH
# ============================================================================

def test_cpp_batch(data, max_legs, max_loss=5.0, max_premium=2.0):
    """Test avec appel batch C++"""
    import strategy_metrics_cpp
    
    n_opts = len(data['premiums'])
    
    # Étape 1: Init cache
    start_init = time.perf_counter()
    strategy_metrics_cpp.init_options_cache(
        data['premiums'], data['deltas'], data['gammas'],
        data['vegas'], data['thetas'], data['ivs'],
        data['avg_pnls'], data['sigma_pnls'], data['strikes'],
        data['profit_surf'], data['loss_surf'], data['is_calls'],
        data['pnl_matrix'], data['prices']
    )
    init_time = time.perf_counter() - start_init
    
    # Étape 2: Générer les combinaisons
    start_combo = time.perf_counter()
    all_indices = []
    all_signs = []
    all_sizes = []
    
    for n_legs in range(1, max_legs + 1):
        sign_variants = list(product([-1, 1], repeat=n_legs))
        for combo in combinations_with_replacement(range(n_opts), n_legs):
            # Filtrer par expiration
            if n_legs > 1:
                if data['expirations'][combo[0]] != data['expirations'][combo[-1]]:
                    continue
            
            for signs in sign_variants:
                all_indices.append(list(combo) + [-1] * (max_legs - n_legs))
                all_signs.append(list(signs) + [0] * (max_legs - n_legs))
                all_sizes.append(n_legs)
    
    indices_batch = np.array(all_indices, dtype=np.int32)
    signs_batch = np.array(all_signs, dtype=np.int32)
    combo_sizes = np.array(all_sizes, dtype=np.int32)
    combo_time = time.perf_counter() - start_combo
    
    n_combos = len(all_sizes)
    
    # Étape 3: Traitement batch C++
    start_cpp = time.perf_counter()
    results = strategy_metrics_cpp.process_combinations_batch(
        indices_batch, signs_batch, combo_sizes,
        max_loss, max_premium, True  # ouvert=True
    )
    cpp_time = time.perf_counter() - start_cpp
    
    total_time = time.perf_counter() - start_init
    
    return {
        'n_combos': n_combos,
        'n_valid': len(results),
        'init_time': init_time,
        'combo_time': combo_time,
        'cpp_time': cpp_time,
        'total_time': total_time,
        'speed': n_combos / total_time
    }

# ============================================================================
# TEST PYTHON PUR (simulation du mode sans C++)
# ============================================================================

def test_python_loop(data, max_legs, max_loss=5.0, max_premium=2.0):
    """Test avec boucle Python appelant C++ pour chaque combinaison"""
    import strategy_metrics_cpp
    
    n_opts = len(data['premiums'])
    
    start = time.perf_counter()
    valid_count = 0
    total_count = 0
    
    for n_legs in range(1, max_legs + 1):
        sign_variants = list(product([-1, 1], repeat=n_legs))
        
        for combo in combinations_with_replacement(range(n_opts), n_legs):
            # Filtrer par expiration
            if n_legs > 1:
                if data['expirations'][combo[0]] != data['expirations'][combo[-1]]:
                    continue
            
            for signs in sign_variants:
                total_count += 1
                
                # Extraire les données pour cette combinaison
                combo_premiums = data['premiums'][list(combo)]
                combo_deltas = data['deltas'][list(combo)]
                combo_gammas = data['gammas'][list(combo)]
                combo_vegas = data['vegas'][list(combo)]
                combo_thetas = data['thetas'][list(combo)]
                combo_ivs = data['ivs'][list(combo)]
                combo_avg_pnls = data['avg_pnls'][list(combo)]
                combo_sigma_pnls = data['sigma_pnls'][list(combo)]
                combo_strikes = data['strikes'][list(combo)]
                combo_profit_surf = data['profit_surf'][list(combo)]
                combo_loss_surf = data['loss_surf'][list(combo)]
                combo_is_calls = data['is_calls'][list(combo)]
                combo_pnl_matrix = data['pnl_matrix'][list(combo)]
                
                signs_arr = np.array(signs, dtype=np.int32)
                
                # Appel C++ unitaire
                result = strategy_metrics_cpp.calculate_strategy_metrics(
                    combo_premiums, combo_deltas, combo_gammas,
                    combo_vegas, combo_thetas, combo_ivs,
                    combo_avg_pnls, combo_sigma_pnls, combo_strikes,
                    combo_profit_surf, combo_loss_surf, combo_is_calls,
                    signs_arr, combo_pnl_matrix, data['prices'],
                    max_loss, max_premium, True
                )
                
                if result is not None:
                    valid_count += 1
    
    total_time = time.perf_counter() - start
    
    return {
        'n_combos': total_count,
        'n_valid': valid_count,
        'total_time': total_time,
        'speed': total_count / total_time
    }

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("BENCHMARK: C++ Batch vs Python Loop (appels C++ unitaires)")
    print("=" * 70)
    
    # Vérifier que le module C++ est disponible
    try:
        import strategy_metrics_cpp
        print("✅ Module C++ disponible")
        print(f"   Fonctions: {[x for x in dir(strategy_metrics_cpp) if not x.startswith('_')]}")
    except ImportError:
        print("❌ Module C++ non disponible!")
        exit(1)
    
    print(f"\n📊 Configuration:")
    print(f"   - Nombre d'options: {N_OPTIONS}")
    print(f"   - Longueur P&L: {PNL_LENGTH}")
    print(f"   - Max legs: {MAX_LEGS}")
    
    # Générer les données de test
    print("\n📦 Génération des données de test...")
    data = generate_test_data(N_OPTIONS, PNL_LENGTH)
    
    # Calculer le nombre théorique de combinaisons
    from math import comb
    n_combos_theory = sum(
        comb(N_OPTIONS + n - 1, n) * (2 ** n)
        for n in range(1, MAX_LEGS + 1)
    )
    print(f"   Combinaisons théoriques (sans filtre expiration): ~{n_combos_theory:,}")
    
    # Test 1: C++ Batch
    print("\n" + "=" * 70)
    print("🚀 TEST 1: C++ BATCH (UN SEUL APPEL)")
    print("=" * 70)
    
    cpp_results = test_cpp_batch(data, MAX_LEGS)
    
    print(f"\n   📈 Résultats C++ Batch:")
    print(f"      - Combinaisons testées: {cpp_results['n_combos']:,}")
    print(f"      - Stratégies valides: {cpp_results['n_valid']:,} ({cpp_results['n_valid']/cpp_results['n_combos']*100:.1f}%)")
    print(f"      - Init cache: {cpp_results['init_time']:.4f}s")
    print(f"      - Génération combos: {cpp_results['combo_time']:.4f}s")
    print(f"      - Traitement C++: {cpp_results['cpp_time']:.4f}s")
    print(f"      - TOTAL: {cpp_results['total_time']:.4f}s")
    print(f"      - Vitesse: {cpp_results['speed']:,.0f} évals/sec")
    
    # Test 2: Python Loop (appels unitaires)
    print("\n" + "=" * 70)
    print("🐢 TEST 2: PYTHON LOOP (APPELS C++ UNITAIRES)")
    print("=" * 70)
    
    python_results = test_python_loop(data, MAX_LEGS)
    
    print(f"\n   📈 Résultats Python Loop:")
    print(f"      - Combinaisons testées: {python_results['n_combos']:,}")
    print(f"      - Stratégies valides: {python_results['n_valid']:,}")
    print(f"      - TOTAL: {python_results['total_time']:.4f}s")
    print(f"      - Vitesse: {python_results['speed']:,.0f} évals/sec")
    
    # Comparaison
    print("\n" + "=" * 70)
    print("📊 COMPARAISON")
    print("=" * 70)
    
    speedup = python_results['total_time'] / cpp_results['total_time']
    
    print(f"\n   🏆 SPEEDUP C++ Batch: {speedup:.1f}x plus rapide")
    print(f"\n   Temps C++ Batch:  {cpp_results['total_time']:.4f}s")
    print(f"   Temps Python Loop: {python_results['total_time']:.4f}s")
    print(f"   Gain de temps: {python_results['total_time'] - cpp_results['total_time']:.4f}s")
    
    # Validation: même nombre de stratégies valides?
    if cpp_results['n_valid'] == python_results['n_valid']:
        print(f"\n   ✅ Validation: Mêmes résultats ({cpp_results['n_valid']} stratégies)")
    else:
        print(f"\n   ⚠️ Différence: C++={cpp_results['n_valid']} vs Python={python_results['n_valid']}")
    
    print("\n" + "=" * 70)
    print("🎉 Benchmark terminé!")
    print("=" * 70)
