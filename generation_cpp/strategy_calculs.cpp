#include "strategy_metrics.hpp"
#include <numeric>
#include <cmath>

// ============================================================================
// CALCULS
// ============================================================================

namespace strategy {
    
void StrategyCalculator::calculate_greeks(
    const OptionData* const* options,
    const int* signs,
    size_t n_options,
    double& total_iv
) {
    total_iv = 0.0;
    
    for (size_t i = 0; i < n_options; ++i) {
        const double s = static_cast<double>(signs[i]);
        total_iv += s * options[i]->implied_volatility;
    }
}

std::vector<double> StrategyCalculator::calculate_total_pnl(
    const std::vector<std::vector<double>>& pnl_matrix,
    const std::vector<int>& signs
) {
    if (pnl_matrix.empty()) {
        return {};
    }
    
    const size_t n_options = pnl_matrix.size();
    const size_t pnl_length = pnl_matrix[0].size();
    
    std::vector<double> total_pnl(pnl_length, 0.0);
    
    // Dot product: signs @ pnl_matrix
    for (size_t i = 0; i < n_options; ++i) {
        const double s = static_cast<double>(signs[i]);
        const auto& row = pnl_matrix[i];
        
        for (size_t j = 0; j < pnl_length; ++j) {
            total_pnl[j] += s * row[j];
        }
    }
    
    return total_pnl;
}

double StrategyCalculator::avg_pnl_levrage(
    const double total_average_pnl,
    const double premium
) {
    return total_average_pnl /(std::max(std::abs(premium) , 0.005));
}

} // namespace strategy
