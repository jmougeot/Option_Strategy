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
    const int N
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
    double limit_right,
    bool premium_only,
    bool premium_only_left,
    bool premium_only_right
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
    if (!filter_put_open(options, signs, ouvert_gauche)) {
        return std::nullopt;
    }
    
    // Filtre 4b: Call open (ouvert_droite)
    if (!filter_call_open(options, signs, ouvert_droite)) {
        return std::nullopt;
    }
    
    // Filtres/agrégations fusionnés en une seule passe
    double total_premium = 0.0;
    double total_delta = 0.0;
    double total_average_pnl = 0.0;
    double total_roll = 0.0;
    int call_count = 0;
    int put_count = 0;

    for (size_t i = 0; i < options.size(); ++i) {
        const double s = static_cast<double>(signs[i]);
        total_premium += s * options[i].premium;
        total_delta += s * options[i].delta;
        total_average_pnl += s * options[i].average_pnl;
        total_roll += s * options[i].roll;

        if (options[i].is_call) {
            ++call_count;
        } else {
            ++put_count;
        }
    }

    // Filtre 5: Premium
    if (std::abs(total_premium) > max_premium_params) {
        return std::nullopt;
    }

    // Filtre 6: Delta (avec bornes min/max)
    if (total_delta < delta_min || total_delta > delta_max) {
        return std::nullopt;
    }

    // Filtre 7: Average P&L
    if (total_average_pnl < 0.0) {
        return std::nullopt;
    }
    
    // ========== CALCULS ==========
    
    // Greeks
    double total_iv;
    calculate_greeks(options, signs, total_iv);
    
    // P&L total — calcul fusionné avec filtres de perte pour early-exit
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
    
    if (total_pnl.empty()) {
        return std::nullopt;
    }

    double avg_pnl_lvg = avg_pnl_levrage(total_average_pnl, total_premium);
    
    // ========== FILTRES DE PERTE + MAX/MIN en une seule passe ==========
    
    double max_loss_left = 0.0;
    double max_loss_right = 0.0;
    double max_profit = total_pnl[0];
    double max_loss = total_pnl[0];
    const double abs_premium = std::abs(total_premium);
    
    for (size_t i = 0; i < pnl_length; ++i) {
        const double price = prices[i];
        const double pnl = total_pnl[i];
        
        // Track global min/max
        if (pnl > max_profit) max_profit = pnl;
        if (pnl < max_loss) max_loss = pnl;
        
        if (price < limit_left) {
            if (pnl < max_loss_left) max_loss_left = pnl;
            if (premium_only_left) {
                if (pnl < -abs_premium) return std::nullopt;
            } else {
                if (pnl < -max_loss_left_param) return std::nullopt;
            }
        } else if (price > limit_right) {
            if (pnl < max_loss_right) max_loss_right = pnl;
            if (premium_only_right) {
                if (pnl < -abs_premium) return std::nullopt;
            } else {
                if (pnl < -max_loss_right_param) return std::nullopt;
            }
        } else {
            if (pnl < -abs_premium) return std::nullopt;
        }
    }
    
    // Filtre premium_only: |max_loss| doit être < |premium|
    if (premium_only && std::abs(max_loss) > abs_premium) {
        return std::nullopt;
    }
    
    // Breakeven points
    std::vector<double> breakeven_points = calculate_breakeven_points(total_pnl, prices);
    
    // Profit zone
    double min_profit_price, max_profit_price, profit_zone_width;
    calculate_profit_zone(total_pnl, prices, min_profit_price, max_profit_price, profit_zone_width);
    
    // Calcul des prix intra-vie et P&L de la stratégie
    std::array<double, N_INTRA_DATES> strategy_intra_life_prices;
    std::array<double, N_INTRA_DATES> strategy_intra_life_pnl;
    for (int t = 0; t < N_INTRA_DATES; ++t) {
        double total_value = 0.0;
        double total_pnl_t = 0.0;
        for (size_t i = 0; i < options.size(); ++i) {
            total_value += signs[i] * options[i].intra_life_prices[t];
            total_pnl_t += signs[i] * options[i].intra_life_pnl[t];
        }
        strategy_intra_life_prices[t] = total_value;
        strategy_intra_life_pnl[t] = total_pnl_t;
    }
    
    // Calcul de la moyenne des P&L intra-vie
    double sum_intra_pnl = 0.0;
    for (int t = 0; t < N_INTRA_DATES; ++t) {
        sum_intra_pnl += strategy_intra_life_pnl[t];
    }
    double avg_intra_life_pnl = sum_intra_pnl / N_INTRA_DATES;
    
    // ========== CONSTRUCTION DU RÉSULTAT ==========
    
    StrategyMetrics result;
    result.total_premium = total_premium;
    result.total_delta = total_delta;
    result.total_iv = total_iv;
    result.max_profit = max_profit;
    result.max_loss = max_loss;
    result.max_loss_left = max_loss_left;
    result.max_loss_right = max_loss_right;
    result.total_average_pnl = total_average_pnl;
    result.min_profit_price = min_profit_price;
    result.max_profit_price = max_profit_price;
    result.profit_zone_width = profit_zone_width;
    result.breakeven_points = std::move(breakeven_points);
    result.total_pnl_array = std::move(total_pnl);
    result.total_roll = total_roll;
    result.call_count = call_count;
    result.put_count = put_count;
    result.avg_pnl_levrage = avg_pnl_lvg;
    result.intra_life_prices = strategy_intra_life_prices;
    result.intra_life_pnl = strategy_intra_life_pnl;
    result.avg_intra_life_pnl = avg_intra_life_pnl;
    
    return result;
}

} // namespace strategy
