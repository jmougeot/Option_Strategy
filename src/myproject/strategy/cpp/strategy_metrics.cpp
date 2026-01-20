/**
 * Implémentation des calculs de métriques de stratégies
 * Optimisé pour la performance (SIMD-friendly, cache-friendly)
 */

#include "strategy_metrics.hpp"
#include <numeric>
#include <cmath>

namespace strategy {

// ============================================================================
// FILTRES
// ============================================================================

bool StrategyCalculator::filter_useless_sell(
    const std::vector<OptionData>& options,
    const std::vector<int>& signs,
    double min_premium_sell
) {
    // Éliminer la vente d'un put ou d'un call qui ne rapporte rien
    for (size_t i = 0; i < options.size(); ++i) {
        if (signs[i] < 0 && options[i].premium < min_premium_sell) {
            return false;  // Stratégie invalide
        }
    }
    return true;  // OK
}

bool StrategyCalculator::filter_same_option_buy_sell(
    const std::vector<OptionData>& options,
    const std::vector<int>& signs
) {
    const size_t n = options.size();
    
    for (size_t i = 0; i < n; ++i) {
        for (size_t j = i + 1; j < n; ++j) {
            // Même type (call/put) et même strike mais signes opposés = inutile
            if (options[i].is_call == options[j].is_call &&
                options[i].strike == options[j].strike &&
                signs[i] != signs[j]) {
                return false;
            }
        }
    }
    return true;
}


bool StrategyCalculator::filter_put_count(
    const std::vector<OptionData>& options,
    const std::vector<int>& signs,
    int ouvert_gauche,
    int& put_count
) {
    int long_put_count = 0;
    int short_put_count = 0;
    
    for (size_t i = 0; i < options.size(); ++i) {
        if (!options[i].is_call) {
            if (signs[i] > 0) {
                ++long_put_count;
            } else {
                ++short_put_count;
            }
        }
    }
    
    put_count = long_put_count - short_put_count;
    
    
    // Filtre 1: Trop de short puts par rapport aux longs
    if ((short_put_count - long_put_count) > ouvert_gauche) {
        return false;
    }
    return true;
}


bool StrategyCalculator::filter_call_open(
    const std::vector<OptionData>& options,
    const std::vector<int>& signs,
    int ouvert_droite,
    int long_put_count,
    int& call_count
) {
    int long_call_count = 0;
    int short_call_count = 0;
    
    for (size_t i = 0; i < options.size(); ++i) {
        if (options[i].is_call) {
            if (signs[i] > 0) {
                ++long_call_count;
            } else {
                ++short_call_count;
            }
        }
    }
    
    call_count = long_call_count - short_call_count;
    
    // Filtre : Trop de short calls par rapport aux longs
    if ((short_call_count - long_call_count) > ouvert_droite) {
        return false;
    }
    return true;
}


bool StrategyCalculator::filter_premium(
    const std::vector<OptionData>& options,
    const std::vector<int>& signs,
    double max_premium_params,
    double& total_premium
) {
    total_premium = 0.0;
    for (size_t i = 0; i < options.size(); ++i) {
        total_premium += signs[i] * options[i].premium;
    }
    return std::abs(total_premium) <= max_premium_params;
}


bool StrategyCalculator::filter_delta(
    const std::vector<OptionData>& options,
    const std::vector<int>& signs,
    double& total_delta
) {
    total_delta = 0.0;
    for (size_t i = 0; i < options.size(); ++i) {
        total_delta += signs[i] * options[i].delta;
    }
    return std::abs(total_delta) <= 0.75;
}


bool StrategyCalculator::filter_average_pnl(
    const std::vector<OptionData>& options,
    const std::vector<int>& signs,
    double& total_average_pnl
) {
    total_average_pnl = 0.0;
    for (size_t i = 0; i < options.size(); ++i) {
        total_average_pnl += signs[i] * options[i].average_pnl;
    }
    return total_average_pnl >= 0.0;
}


// ============================================================================
// CALCULS
// ============================================================================

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


void StrategyCalculator::calculate_surfaces(
    const std::vector<double>& total_pnl,
    const std::vector<OptionData>& options,
    const std::vector<int>& signs,
    double dx,
    double& surface_profit,
    double& total_loss_ponderated,
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
    
    
    // Surfaces pondérées
    double sum_signed_sigma = 0.0;
    
    for (size_t i = 0; i < options.size(); ++i) {
        sum_signed_sigma += signs[i] * options[i].sigma_pnl;
    }
    
    total_sigma_pnl = std::abs(sum_signed_sigma);
}


// ============================================================================
// FONCTION PRINCIPALE
// ============================================================================

std::optional<StrategyMetrics> StrategyCalculator::calculate(
    const std::vector<OptionData>& options,
    const std::vector<int>& signs,
    const std::vector<std::vector<double>>& pnl_matrix,
    const std::vector<double>& prices,
    double max_loss_params,
    double max_premium_params,
    int ouvert_gauche,
    int ouvert_droite,
    double min_premium_sell
) {
    const size_t n_options = options.size();
    
    // Validation de base
    if (n_options == 0 || n_options != signs.size() || 
        n_options != pnl_matrix.size() || prices.empty()) {
        return std::nullopt;
    }
    
    // ========== FILTRES (early exit) ==========
    
    // Filtre 1: Vente inutile (premium < min_premium_sell)
    if (!filter_useless_sell(options, signs, min_premium_sell)) {
        return std::nullopt;
    }
    
    
    // Filtre 3: Achat et vente de la même option
    if (!filter_same_option_buy_sell(options, signs)) {
        return std::nullopt;
    }
    
    // Filtre 4: Put count (ouvert_gauche)
    int put_count;
    int long_put_count = 0;
    for (size_t i = 0; i < options.size(); ++i) {
        if (!options[i].is_call && signs[i] > 0) {
            ++long_put_count;
        }
    }
    if (!filter_put_count(options, signs, ouvert_gauche, put_count)) {
        return std::nullopt;
    }
    
    // Filtre 4b: Call open (ouvert_droite)
    int call_count_check;
    if (!filter_call_open(options, signs, ouvert_droite, long_put_count, call_count_check)) {
        return std::nullopt;
    }
    
    // Filtre 5: Premium
    double total_premium;
    if (!filter_premium(options, signs, max_premium_params, total_premium)) {
        return std::nullopt;
    }
    
    // Filtre 6: Delta
    double total_delta;
    if (!filter_delta(options, signs, total_delta)) {
        return std::nullopt;
    }
    
    // Filtre 7: Average P&L
    double total_average_pnl;
    if (!filter_average_pnl(options, signs, total_average_pnl)) {
        return std::nullopt;
    }
    
    // ========== CALCULS ==========
    
    // Greeks
    double total_gamma, total_vega, total_theta, total_iv;
    calculate_greeks(options, signs, total_gamma, total_vega, total_theta, total_iv);
    
    // P&L total
    std::vector<double> total_pnl = calculate_total_pnl(pnl_matrix, signs);
    
    if (total_pnl.empty()) {
        return std::nullopt;
    }
    
    // Max profit / max loss
    auto [min_it, max_it] = std::minmax_element(total_pnl.begin(), total_pnl.end());
    double max_profit = *max_it;
    double max_loss = *min_it;
    
    // Filtre 8: Max loss
    if (max_loss < -max_loss_params) {
        return std::nullopt;
    }
    
    // Breakeven points
    std::vector<double> breakeven_points = calculate_breakeven_points(total_pnl, prices);
    
    // Profit zone
    double min_profit_price, max_profit_price, profit_zone_width;
    calculate_profit_zone(total_pnl, prices, min_profit_price, max_profit_price, profit_zone_width);
    
    // Surfaces
    double dx = (prices.size() > 1) ? (prices[1] - prices[0]) : 1.0;
    double total_sigma_pnl;
    calculate_surfaces(total_pnl, options, signs, dx, total_sigma_pnl);
    
    // ========== CONSTRUCTION DU RÉSULTAT ==========
    
    StrategyMetrics result;
    result.total_premium = total_premium;
    result.total_delta = total_delta;
    result.total_gamma = total_gamma;
    result.total_vega = total_vega;
    result.total_theta = total_theta;
    result.total_iv = total_iv;
    result.max_profit = max_profit;
    result.max_loss = max_loss;
    result.total_average_pnl = total_average_pnl;
    result.total_sigma_pnl = total_sigma_pnl;
    result.min_profit_price = min_profit_price;
    result.max_profit_price = max_profit_price;
    result.profit_zone_width = profit_zone_width;
    result.breakeven_points = std::move(breakeven_points);
    result.total_pnl_array = std::move(total_pnl);
    
    return result;
}

} // namespace strategy
