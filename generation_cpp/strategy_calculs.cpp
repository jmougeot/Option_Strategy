#include "strategy_metrics.hpp"
#include <numeric>
#include <cmath>

// ============================================================================
// CALCULS
// ============================================================================

namespace strategy {
    
void StrategyCalculator::calculate_greeks(
    const std::vector<OptionData>& options,
    const std::vector<int>& signs,
    double& total_iv
) {
    total_iv = 0.0;
    
    for (size_t i = 0; i < options.size(); ++i) {
        const double s = static_cast<double>(signs[i]);
        total_iv += s * options[i].implied_volatility;
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

std::vector<double> StrategyCalculator::calculate_breakeven_points(
    const std::vector<double>& total_pnl,
    const std::vector<double>& prices
) {
    std::vector<double> breakevens;
    
    if (total_pnl.size() < 2) {
        return breakevens;
    }
    
    for (size_t i = 0; i < total_pnl.size() - 1; ++i) {
        // Changement de signe ?
        if (total_pnl[i] * total_pnl[i + 1] < 0.0) {
            // Interpolation linéaire
            double t = -total_pnl[i] / (total_pnl[i + 1] - total_pnl[i]);
            double breakeven = prices[i] + (prices[i + 1] - prices[i]) * t;
            breakevens.push_back(breakeven);
        }
    }
    
    return breakevens;
}

void StrategyCalculator::calculate_profit_zone(
    const std::vector<double>& total_pnl,
    const std::vector<double>& prices,
    double& min_profit_price,
    double& max_profit_price,
    double& profit_zone_width
) {
    min_profit_price = 0.0;
    max_profit_price = 0.0;
    profit_zone_width = 0.0;

    if (total_pnl.empty() || prices.empty() || total_pnl.size() != prices.size()) {
        return;
    }

    bool found = false;
    for (size_t i = 0; i < total_pnl.size(); ++i) {
        if (total_pnl[i] > 0.0) {
            if (!found) {
                min_profit_price = prices[i];
                max_profit_price = prices[i];
                found = true;
            } else {
                if (prices[i] < min_profit_price) min_profit_price = prices[i];
                if (prices[i] > max_profit_price) max_profit_price = prices[i];
            }
        }
    }

    if (found) {
        profit_zone_width = max_profit_price - min_profit_price;
    }
}

double StrategyCalculator::avg_pnl_levrage(
    const double total_average_pnl,
    const double premium
) {
    return total_average_pnl /(std::max(std::abs(premium) , 0.005));
}

} // namespace strategy
