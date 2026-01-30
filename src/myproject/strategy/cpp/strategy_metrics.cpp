/**
 * Implémentation des calculs de métriques de stratégies
 * Optimisé pour la performance (SIMD-friendly, cache-friendly)
 */

#include "strategy_metrics.hpp"
#include "strategy_scoring.hpp"
#include <numeric>
#include <cmath>

// Inclure les implémentations séparées (unity build)
#include "strategy_filters.cpp"
#include "strategy_calculs.cpp"
#include "strategy_scoring.cpp"

// Note: strategy_filters.cpp et strategy_calculs.cpp définissent leurs fonctions
// dans le namespace strategy, donc pas besoin de rouvrir le namespace ici.

namespace strategy {

// ============================================================================
// FONCTION PRINCIPALE
// ============================================================================

bool StrategyCalculator::next_combination(
    std::vector<int>& c,
    int N
) {
    int k = c.size();

    for (int i = k - 1; i >= 0; --i) {
        if (c[i] < N - 1) {
            int v = ++c[i];
            for (int j = i + 1; j < k; ++j)
                c[j] = v;
            return true;
        }
    }
    return false; 
}

std::optional<StrategyMetrics> StrategyCalculator::calculate(
    const std::vector<OptionData>& options,
    const std::vector<int>& signs,
    const std::vector<std::vector<double>>& pnl_matrix,
    const std::vector<double>& prices,
    const std::vector<double>& mixture,
    double average_mix,
    double max_loss_left_param,
    double max_loss_right_param,
    double max_premium_params,
    int ouvert_gauche,
    int ouvert_droite,
    double min_premium_sell,
    double delta_min,
    double delta_max,
    double limit_left,
    double limit_right
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
    if (!filter_put_open(options, signs, ouvert_gauche)) {
        return std::nullopt;
    }
    
    // Filtre 4b: Call open (ouvert_droite)
    int call_count_check;
    if (!filter_call_open(options, signs, ouvert_droite)) {
        return std::nullopt;
    }
    
    // Filtre 5: Premium
    double total_premium;
    if (!filter_premium(options, signs, max_premium_params, total_premium)) {
        return std::nullopt;
    }
    
    // Filtre 6: Delta (avec bornes min/max)
    double total_delta;
    if (!filter_delta(options, signs, delta_min, delta_max, total_delta)) {
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
    
    // ========== FILTRES DE PERTE BASÉS SUR LES LIMITES DE PRIX ==========
    
    double max_loss_left = 0.0;
    double max_loss_right = 0.0;
    
    for (size_t i = 0; i < prices.size() && i < total_pnl.size(); ++i) {
        double price = prices[i];
        double pnl = total_pnl[i];
        
        if (price < limit_left) {
            // Zone gauche: vérifier contre max_loss_left_param
            if (pnl < -max_loss_left_param) {
                return std::nullopt;
            }
            if (pnl < max_loss_left) {
                max_loss_left = pnl;
            }
        } else if (price > limit_right) {
            // Zone droite: vérifier contre max_loss_right_param
            if (pnl < -max_loss_right_param) {
                return std::nullopt;
            }
            if (pnl < max_loss_right) {
                max_loss_right = pnl;
            }
        } else {
            // Zone centrale: la perte ne doit pas dépasser le premium payé
            if (pnl < -std::abs(total_premium)) {
                return std::nullopt;
            }
        }
    }
    
    // Trouver l'index de séparation basé sur average_mix (pour d'autres calculs)
    size_t split_idx = 0;
    for (size_t i = 0; i < prices.size(); ++i) {
        if (prices[i] >= average_mix) {
            split_idx = i;
            break;
        }
    }
    if (split_idx == 0) split_idx = prices.size() / 2;
    
    // Max profit / max loss global
    auto [min_it, max_it] = std::minmax_element(total_pnl.begin(), total_pnl.end());
    double max_profit = *max_it;
    double max_loss = *min_it;
    
    // Breakeven points
    std::vector<double> breakeven_points = calculate_breakeven_points(total_pnl, prices);
    
    // Profit zone
    double min_profit_price, max_profit_price, profit_zone_width;
    calculate_profit_zone(total_pnl, prices, min_profit_price, max_profit_price, profit_zone_width);
    
    // Surfaces et sigma
    double dx = (prices.size() > 1) ? (prices[1] - prices[0]) : 1.0;
    double total_sigma_pnl = 0.0;
    
    // Calcul sigma avec mixture
    if (!mixture.empty()) {
        double mass = 0.0;
        for (double m : mixture) mass += m;
        mass *= dx;
        
        if (mass > 0.0) {
            double var = 0.0;
            for (size_t i = 0; i < total_pnl.size() && i < mixture.size(); ++i) {
                double diff = total_pnl[i] - total_average_pnl;
                var += mixture[i] * diff * diff;
            }
            var *= dx / mass;
            total_sigma_pnl = std::sqrt(std::max(var, 0.0));
        }
    }
    
    // Calcul des rolls
    double total_roll = 0.0;
    double total_roll_quarterly = 0.0;
    double total_roll_sum = 0.0;
    for (size_t i = 0; i < options.size(); ++i) {
        total_roll += signs[i] * options[i].roll;
        total_roll_quarterly += signs[i] * options[i].roll_quarterly;
        total_roll_sum += signs[i] * options[i].roll_sum;
    }
    
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
    result.max_loss_left = max_loss_left;
    result.max_loss_right = max_loss_right;
    result.total_average_pnl = total_average_pnl;
    result.total_sigma_pnl = total_sigma_pnl;
    result.min_profit_price = min_profit_price;
    result.max_profit_price = max_profit_price;
    result.profit_zone_width = profit_zone_width;
    result.breakeven_points = std::move(breakeven_points);
    result.total_pnl_array = std::move(total_pnl);
    result.total_roll = total_roll;
    result.total_roll_quarterly = total_roll_quarterly;
    result.total_roll_sum = total_roll_sum;
    result.call_count = call_count_check;
    result.put_count = put_count;
    
    return result;
}

} // namespace strategy
