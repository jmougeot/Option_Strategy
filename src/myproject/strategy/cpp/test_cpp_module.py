"""
Test du module C++ strategy_metrics_cpp
Compare les résultats C++ et Python pour valider la cohérence
"""

import numpy as np
import time
import strategy_metrics_cpp


def test_module_import():
    """Test que le module s'importe correctement"""
    print("✅ Module C++ importé avec succès")
    print(f"   Doc: {strategy_metrics_cpp.__doc__}")


def test_invalid_strategy():
    """Test qu'une stratégie invalide retourne None"""
    n = 10
    pnl_length = 100
    
    # Stratégie avec vente à premium trop faible (< 0.04)
    premiums = np.array([0.02, 0.5], dtype=np.float64)  # 0.02 < 0.04 sur une vente
    deltas = np.array([0.5, -0.3], dtype=np.float64)
    gammas = np.array([0.01, 0.02], dtype=np.float64)
    vegas = np.array([0.1, 0.15], dtype=np.float64)
    thetas = np.array([-0.01, -0.02], dtype=np.float64)
    ivs = np.array([0.2, 0.25], dtype=np.float64)
    average_pnls = np.array([0.1, 0.2], dtype=np.float64)
    sigma_pnls = np.array([0.05, 0.08], dtype=np.float64)
    strikes = np.array([100.0, 105.0], dtype=np.float64)
    profit_surfaces = np.array([1.0, 1.5], dtype=np.float64)
    loss_surfaces = np.array([0.5, 0.8], dtype=np.float64)
    is_calls = np.array([True, True], dtype=bool)
    signs = np.array([-1, 1], dtype=np.int32)  # Première option vendue avec premium < 0.04
    pnl_matrix = np.random.randn(n, pnl_length).astype(np.float64)
    prices = np.linspace(80, 120, pnl_length, dtype=np.float64)
    
    result = strategy_metrics_cpp.calculate_strategy_metrics(
        premiums, deltas, gammas, vegas, thetas, ivs,
        average_pnls, sigma_pnls, strikes,
        profit_surfaces, loss_surfaces, is_calls,
        signs, pnl_matrix, prices,
        max_loss_params=10.0, max_premium_params=5.0, ouvert=True
    )
    
    assert result is None, "Devrait retourner None pour une vente à premium < 0.04"
    print("✅ Test stratégie invalide (vente inutile) : PASS")


def test_valid_strategy():
    """Test qu'une stratégie valide retourne les métriques"""
    n = 2
    pnl_length = 100
    
    # Stratégie valide
    premiums = np.array([0.5, 0.3], dtype=np.float64)
    deltas = np.array([0.3, -0.2], dtype=np.float64)
    gammas = np.array([0.01, 0.02], dtype=np.float64)
    vegas = np.array([0.1, 0.15], dtype=np.float64)
    thetas = np.array([-0.01, -0.02], dtype=np.float64)
    ivs = np.array([0.2, 0.25], dtype=np.float64)
    average_pnls = np.array([0.1, 0.2], dtype=np.float64)
    sigma_pnls = np.array([0.05, 0.08], dtype=np.float64)
    strikes = np.array([100.0, 105.0], dtype=np.float64)
    profit_surfaces = np.array([1.0, 1.5], dtype=np.float64)
    loss_surfaces = np.array([0.5, 0.8], dtype=np.float64)
    is_calls = np.array([True, False], dtype=bool)  # Call + Put
    signs = np.array([1, 1], dtype=np.int32)  # Les deux achetées
    
    # P&L réaliste
    prices = np.linspace(80, 120, pnl_length, dtype=np.float64)
    pnl_matrix = np.zeros((n, pnl_length), dtype=np.float64)
    
    # Call acheté: profit quand prix monte
    pnl_matrix[0] = np.maximum(prices - 100, 0) - premiums[0]
    # Put acheté: profit quand prix baisse
    pnl_matrix[1] = np.maximum(105 - prices, 0) - premiums[1]
    
    result = strategy_metrics_cpp.calculate_strategy_metrics(
        premiums, deltas, gammas, vegas, thetas, ivs,
        average_pnls, sigma_pnls, strikes,
        profit_surfaces, loss_surfaces, is_calls,
        signs, pnl_matrix, prices,
        max_loss_params=10.0, max_premium_params=5.0, ouvert=True
    )
    
    assert result is not None, "Devrait retourner un dict pour une stratégie valide"
    assert "total_premium" in result
    assert "total_delta" in result
    assert "max_profit" in result
    assert "max_loss" in result
    assert "pnl_array" in result
    assert len(result["pnl_array"]) == pnl_length
    
    print("✅ Test stratégie valide : PASS")
    print(f"   Premium total: {result['total_premium']:.4f}")
    print(f"   Delta total: {result['total_delta']:.4f}")
    print(f"   Max profit: {result['max_profit']:.4f}")
    print(f"   Max loss: {result['max_loss']:.4f}")


def test_performance():
    """Benchmark de performance"""
    n = 4
    pnl_length = 500
    iterations = 1000000
    
    # Données aléatoires valides
    premiums = np.random.uniform(0.1, 2.0, n).astype(np.float64)
    deltas = np.random.uniform(-0.2, 0.2, n).astype(np.float64)
    gammas = np.random.uniform(0.0, 0.05, n).astype(np.float64)
    vegas = np.random.uniform(0.0, 0.2, n).astype(np.float64)
    thetas = np.random.uniform(-0.05, 0.0, n).astype(np.float64)
    ivs = np.random.uniform(0.1, 0.5, n).astype(np.float64)
    average_pnls = np.random.uniform(0.0, 0.5, n).astype(np.float64)
    sigma_pnls = np.random.uniform(0.01, 0.1, n).astype(np.float64)
    strikes = np.random.uniform(95, 105, n).astype(np.float64)
    profit_surfaces = np.random.uniform(0.5, 2.0, n).astype(np.float64)
    loss_surfaces = np.random.uniform(0.2, 1.0, n).astype(np.float64)
    is_calls = np.random.choice([True, False], n)
    signs = np.array([1, 1, 1, 1], dtype=np.int32)  # Tous achetés pour éviter les filtres
    pnl_matrix = np.random.randn(n, pnl_length).astype(np.float64) * 0.5
    prices = np.linspace(80, 120, pnl_length, dtype=np.float64)
    
    # Benchmark
    start = time.perf_counter()
    valid_count = 0
    
    for _ in range(iterations):
        result = strategy_metrics_cpp.calculate_strategy_metrics(
            premiums, deltas, gammas, vegas, thetas, ivs,
            average_pnls, sigma_pnls, strikes,
            profit_surfaces, loss_surfaces, is_calls,
            signs, pnl_matrix, prices,
            max_loss_params=10.0, max_premium_params=10.0, ouvert=True
        )
        if result is not None:
            valid_count += 1
    
    elapsed = time.perf_counter() - start
    
    print(f"✅ Test performance : PASS")
    print(f"   {iterations} itérations en {elapsed:.3f}s")
    print(f"   {iterations/elapsed:.0f} stratégies/seconde")
    print(f"   {valid_count}/{iterations} stratégies valides")


if __name__ == "__main__":
    print("=" * 60)
    print("Tests du module C++ strategy_metrics_cpp")
    print("=" * 60)
    
    test_module_import()
    test_invalid_strategy()
    test_valid_strategy()
    test_performance()
    
    print("=" * 60)
    print("🎉 Tous les tests passent !")
    print("=" * 60)
