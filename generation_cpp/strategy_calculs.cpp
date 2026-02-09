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
    double& total_gamma,
    double& total_vega,
    double& total_theta,
    double& total_iv
) {
    total_gamma = 0.0;
    total_vega = 0.0;
    total_theta = 0.0;
    total_iv = 0.0;
    
    for (size_t i = 0; i < options.size(); ++i) {
        const double s = static_cast<double>(signs[i]);
        total_gamma += s * options[i].gamma;
        total_vega += s * options[i].vega;
        total_theta += s * options[i].theta;
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
    
    int first_profitable = -1;
    int last_profitable = -1;
    
    for (size_t i = 0; i < total_pnl.size(); ++i) {
        if (total_pnl[i] > 0.0) {
            if (first_profitable < 0) {
                first_profitable = static_cast<int>(i);
            }
            last_profitable = static_cast<int>(i);
        }
    }
    
    if (first_profitable >= 0) {
        min_profit_price = prices[first_profitable];
        max_profit_price = prices[last_profitable];
        profit_zone_width = max_profit_price - min_profit_price;
    }
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

double StrategyCalculator::delta_levrage(
    const double total_average_pnl,
    const double premium
) {
    if (std::abs(premium) > 1e-10) {
        return std::abs(total_average_pnl / (1+ premium));
    }
    return 0.0;
}

double StrategyCalculator::avg_pnl_levrage(
    const double total_average_pnl,
    const double premium
) {
    return total_average_pnl /(std::max(std::abs(premium) , 0.0005));
}

void StrategyCalculator::calculate_surfaces(
    const std::vector<double>& total_pnl,
    const std::vector<OptionData>& options,
    const std::vector<int>& signs,
    double dx,
    double& total_sigma_pnl
) {
    // Surfaces non pondérées
    double sum_positive = 0.0;
    double sum_negative = 0.0;
    
    for (double pnl : total_pnl) {
        if (pnl > 0.0) {
            sum_positive += pnl;
        } else {
            sum_negative += pnl;  // Négatif
        }
    }
    
    double sum_signed_sigma = 0.0;
    
    for (size_t i = 0; i < options.size(); ++i) {
        sum_signed_sigma += signs[i] * options[i].sigma_pnl;
    }
    
    total_sigma_pnl = std::abs(sum_signed_sigma);
}

} // namespace strategy
