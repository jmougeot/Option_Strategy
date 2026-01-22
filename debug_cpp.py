"""
Script de diagnostic complet pour le module C++ strategy_metrics_cpp
Exécuter ce script pour comprendre pourquoi le module ne fonctionne pas.
"""

import sys
import os
import platform
import struct

print("=" * 60)
print("DIAGNOSTIC DU MODULE C++ strategy_metrics_cpp")
print("=" * 60)

# 1. Informations système
print("\n[1] INFORMATIONS SYSTÈME")
print("-" * 40)
print(f"OS: {platform.system()} {platform.release()}")
print(f"Architecture OS: {platform.machine()}")
print(f"Python version: {sys.version}")
print(f"Python architecture: {struct.calcsize('P') * 8}-bit")
print(f"Python executable: {sys.executable}")

# 2. Environnement virtuel
print("\n[2] ENVIRONNEMENT VIRTUEL")
print("-" * 40)
venv = os.environ.get("VIRTUAL_ENV", "Non détecté")
print(f"VIRTUAL_ENV: {venv}")
print(f"sys.prefix: {sys.prefix}")
print(f"sys.base_prefix: {sys.base_prefix}")
is_venv = sys.prefix != sys.base_prefix
print(f"Dans un venv: {is_venv}")

# 3. Chemins de recherche Python
print("\n[3] CHEMINS DE RECHERCHE (sys.path)")
print("-" * 40)
for i, p in enumerate(sys.path):
    print(f"  [{i}] {p}")

# 4. Recherche du module .pyd/.so
print("\n[4] RECHERCHE DU FICHIER COMPILÉ")
print("-" * 40)
found_files = []
search_patterns = ["strategy_metrics_cpp*.pyd", "strategy_metrics_cpp*.so", "strategy_metrics_cpp.py"]

import glob
for path in sys.path:
    if os.path.isdir(path):
        for pattern in ["strategy_metrics_cpp*.pyd", "strategy_metrics_cpp*.so"]:
            matches = glob.glob(os.path.join(path, pattern))
            for m in matches:
                found_files.append(m)
                print(f"  ✓ TROUVÉ: {m}")
                # Vérifier la taille du fichier
                size = os.path.getsize(m)
                print(f"    Taille: {size:,} bytes")

if not found_files:
    print("  ✗ AUCUN fichier .pyd ou .so trouvé!")
    print("  → Le module n'a pas été compilé ou pas installé dans cet environnement.")

# 5. Vérification pybind11
print("\n[5] VÉRIFICATION PYBIND11")
print("-" * 40)
try:
    import pybind11
    print(f"  ✓ pybind11 version: {pybind11.__version__}")
    print(f"  ✓ pybind11 path: {pybind11.__file__}")
except ImportError as e:
    print(f"  ✗ pybind11 non installé: {e}")

# 6. Vérification NumPy
print("\n[6] VÉRIFICATION NUMPY")
print("-" * 40)
try:
    import numpy as np
    print(f"  ✓ numpy version: {np.__version__}")
    print(f"  ✓ numpy path: {np.__file__}")
except ImportError as e:
    print(f"  ✗ numpy non installé: {e}")

# 7. Vérification des DLL Visual C++ Runtime
print("\n[7] VÉRIFICATION VC++ RUNTIME (Windows)")
print("-" * 40)
if platform.system() == "Windows":
    import ctypes
    import ctypes.util
    
    dll_names = [
        "vcruntime140.dll",
        "vcruntime140_1.dll",
        "msvcp140.dll",
        "concrt140.dll",
    ]
    
    for dll in dll_names:
        try:
            ctypes.CDLL(dll)
            print(f"  ✓ {dll} - OK")
        except OSError:
            print(f"  ✗ {dll} - MANQUANT!")
            print(f"    → Installer Visual C++ Redistributable 2015-2022")
else:
    print("  (Non applicable sur Linux/Mac)")

# 8. Tentative d'import avec message d'erreur détaillé
print("\n[8] TENTATIVE D'IMPORT DU MODULE")
print("-" * 40)
try:
    import strategy_metrics_cpp
    print("  ✓ Import réussi!")
    print(f"  ✓ Module path: {strategy_metrics_cpp.__file__}")
    
    # Vérifier les fonctions disponibles
    print("\n[9] FONCTIONS DISPONIBLES")
    print("-" * 40)
    funcs = [f for f in dir(strategy_metrics_cpp) if not f.startswith("_")]
    for f in funcs:
        print(f"  • {f}")
    
    # Test rapide
    print("\n[10] TEST RAPIDE")
    print("-" * 40)
    try:
        import numpy as np
        # Test avec des données minimales
        n = 2
        pnl_len = 10
        
        premiums = np.array([1.0, 2.0], dtype=np.float64)
        deltas = np.array([0.5, -0.5], dtype=np.float64)
        gammas = np.array([0.1, 0.1], dtype=np.float64)
        vegas = np.array([0.2, 0.2], dtype=np.float64)
        thetas = np.array([-0.01, -0.01], dtype=np.float64)
        ivs = np.array([0.2, 0.2], dtype=np.float64)
        avg_pnls = np.array([10.0, -5.0], dtype=np.float64)
        sigma_pnls = np.array([5.0, 5.0], dtype=np.float64)
        strikes = np.array([100.0, 105.0], dtype=np.float64)
        is_calls = np.array([True, False], dtype=bool)
        rolls = np.array([0.0, 0.0], dtype=np.float64)
        rolls_q = np.array([0.0, 0.0], dtype=np.float64)
        rolls_sum = np.array([0.0, 0.0], dtype=np.float64)
        signs = np.array([1, -1], dtype=np.int32)
        pnl_matrix = np.random.randn(n, pnl_len).astype(np.float64)
        prices = np.linspace(90, 110, pnl_len).astype(np.float64)
        mixture = np.ones(pnl_len, dtype=np.float64) / pnl_len
        
        result = strategy_metrics_cpp.calculate_strategy_metrics(
            premiums, deltas, gammas, vegas, thetas, ivs,
            avg_pnls, sigma_pnls, strikes, is_calls,
            rolls, rolls_q, rolls_sum,
            signs, pnl_matrix, prices, mixture,
            100.0,  # average_mix
            1000.0, 1000.0,  # max_loss_left, max_loss_right
            1000.0,  # max_premium
            5, 5,  # ouvert_gauche, ouvert_droite
            0.0,  # min_premium_sell
            -10.0, 10.0  # delta_min, delta_max
        )
        
        if result is not None:
            print("  ✓ calculate_strategy_metrics() fonctionne!")
            print(f"    total_delta = {result.get('total_delta', 'N/A')}")
        else:
            print("  ⚠ Résultat None (stratégie filtrée)")
            
    except Exception as e:
        print(f"  ✗ Erreur lors du test: {e}")
        import traceback
        traceback.print_exc()

except ImportError as e:
    print(f"  ✗ ÉCHEC DE L'IMPORT: {e}")
    print()
    
    # Diagnostic avancé de l'erreur
    import traceback
    traceback.print_exc()
    
    print("\n[SOLUTIONS POSSIBLES]")
    print("-" * 40)
    
    error_str = str(e).lower()
    
    if "dll load failed" in error_str:
        print("  → Visual C++ Redistributable manquant")
        print("  → Installer: winget install Microsoft.VCRedist.2015+.x64")
        
    elif "no module named" in error_str:
        print("  → Le module n'est pas installé dans cet environnement")
        print("  → Solution:")
        print("    1. Activer le bon environnement: .venv\\Scripts\\activate")
        print("    2. Recompiler: cd src/myproject/strategy/cpp && pip install .")
        
    elif "not a valid win32 application" in error_str:
        print("  → Mauvaise architecture (32-bit vs 64-bit)")
        print("  → Vérifier que Python est 64-bit si compilé en 64-bit")
        
    else:
        print("  → Erreur inconnue. Vérifier:")
        print("    1. Le module est-il compilé?")
        print("    2. Les dépendances sont-elles installées?")
        print("    3. L'environnement est-il correct?")

except Exception as e:
    print(f"  ✗ ERREUR INATTENDUE: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("FIN DU DIAGNOSTIC")
print("=" * 60)

# Résumé
print("\n[RÉSUMÉ]")
if found_files:
    print(f"  Fichier compilé trouvé: {found_files[0]}")
else:
    print("  ⚠ Aucun fichier compilé trouvé!")
    print("  → Exécuter: cd src/myproject/strategy/cpp && pip install . --verbose")
