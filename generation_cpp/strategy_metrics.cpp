/**
 * Implémentation des calculs de métriques de stratégies
 * Optimisé pour la performance (SIMD-friendly, cache-friendly)
 */

#include "strategy_metrics.hpp"
#include "strategy_scoring.hpp"
#include <numeric>
#include <cmath>
#include <cstring>

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
    const OptionData* const* options,
    const int* signs,
    size_t n_options,
    const double* const* pnl_rows,
    size_t pnl_length,
    const double* prices,
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
    double* __restrict total_pnl,
    bool premium_only,
    bool premium_only_left,
    bool premium_only_right
) {
    // Validation de base
    if (n_options == 0 || pnl_length == 0) {
        return std::nullopt;
    }
    
    // ========== FILTRES (early exit) ==========
    
    // Filtre 1: Vente inutile (premium < min_premium_sell)
    if (!filter_useless_sell(options, signs, n_options, min_premium_sell)) {
        return std::nullopt;
    }
    
    // Filtre 3: Achat et vente de la même option
    if (!filter_same_option_buy_sell(options, signs, n_options)) {
        return std::nullopt;
    }
    
    // Filtre 4+4b: Put/Call open (fusionné en une seule passe)
    // + Agrégation fusionnée (premium, delta, avg_pnl, roll, IV, counts)
    // → une seule boucle pour tout
    double total_premium = 0.0;
    double total_delta = 0.0;
    double total_average_pnl = 0.0;
    double total_roll = 0.0;
    double total_iv = 0.0;
    int call_count = 0;
    int put_count = 0;
    int net_short_put = 0;
    int net_short_call = 0;

    for (size_t i = 0; i < n_options; ++i) {
        const double s = static_cast<double>(signs[i]);
        const OptionData& opt = *options[i];
        total_premium += s * opt.premium;
        total_delta += s * opt.delta;
        total_average_pnl += s * opt.average_pnl;
        total_roll += s * opt.roll;
        total_iv += s * opt.implied_volatility;

        if (opt.is_call) {
            ++call_count;
            net_short_call += (signs[i] < 0) ? 1 : -1;
        } else {
            ++put_count;
            net_short_put += (signs[i] < 0) ? 1 : -1;
        }
    }

    // Filtre 4: Put/Call open
    if (net_short_put > ouvert_gauche || net_short_call > ouvert_droite) {
        return std::nullopt;
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
    
    // ========== P&L total via raw pointers (zéro-copie) ==========
    // Optimisation: première ligne = assignment direct (évite memset),
    // lignes suivantes = accumulation. __restrict pour auto-vectorisation.
    
    {
        const double s0 = static_cast<double>(signs[0]);
        const double* __restrict row0 = pnl_rows[0];
        for (size_t j = 0; j < pnl_length; ++j) {
            total_pnl[j] = s0 * row0[j];
        }
    }
    for (size_t i = 1; i < n_options; ++i) {
        const double s = static_cast<double>(signs[i]);
        const double* __restrict row = pnl_rows[i];
        for (size_t j = 0; j < pnl_length; ++j) {
            total_pnl[j] += s * row[j];
        }
    }

    double avg_pnl_lvg = avg_pnl_levrage(total_average_pnl, total_premium);
    
    // ========== FILTRES DE PERTE + BREAKEVEN + PROFIT ZONE en une seule passe ==========
    
    double max_loss_left = 0.0;
    double max_loss_right = 0.0;
    double max_profit = total_pnl[0];
    double max_loss = total_pnl[0];
    const double abs_premium = std::abs(total_premium);
    const double neg_abs_premium = -abs_premium;
    
    // Breakeven avec buffer inline (pas d'allocation heap)
    std::array<double, StrategyMetrics::MAX_BREAKEVEN> breakeven_buf;
    int breakeven_count = 0;
    double min_profit_price = 0.0;
    double max_profit_price = 0.0;
    bool found_profit = false;
    double prev_pnl = total_pnl[0];
    
    for (size_t i = 0; i < pnl_length; ++i) {
        const double price = prices[i];
        const double pnl = total_pnl[i];
        
        // Track global min/max
        if (pnl > max_profit) max_profit = pnl;
        if (pnl < max_loss) max_loss = pnl;
        
        // Breakeven: changement de signe entre i-1 et i
        if (i > 0 && pnl * prev_pnl < 0.0) {
            if (breakeven_count < StrategyMetrics::MAX_BREAKEVEN) {
                double t = -prev_pnl / (pnl - prev_pnl);
                breakeven_buf[breakeven_count++] = prices[i - 1] + (prices[i] - prices[i - 1]) * t;
            }
        }
        prev_pnl = pnl;
        
        // Profit zone tracking
        if (pnl > 0.0) {
            if (!found_profit) {
                min_profit_price = price;
                max_profit_price = price;
                found_profit = true;
            } else {
                if (price > max_profit_price) max_profit_price = price;
            }
        }
        
        // Filtres de perte
        if (price < limit_left) {
            if (pnl < max_loss_left) max_loss_left = pnl;
            if (premium_only_left) {
                if (pnl < neg_abs_premium) return std::nullopt;
            } else {
                if (pnl < -max_loss_left_param) return std::nullopt;
            }
        } else if (price > limit_right) {
            if (pnl < max_loss_right) max_loss_right = pnl;
            if (premium_only_right) {
                if (pnl < neg_abs_premium) return std::nullopt;
            } else {
                if (pnl < -max_loss_right_param) return std::nullopt;
            }
        } else {
            if (pnl < neg_abs_premium) return std::nullopt;
        }
    }
    
    double profit_zone_width = found_profit ? (max_profit_price - min_profit_price) : 0.0;
    
    // Filtre premium_only: |max_loss| doit être < |premium|
    if (premium_only && std::abs(max_loss) > abs_premium) {
        return std::nullopt;
    }
    
    // Calcul des prix intra-vie et P&L de la stratégie
    std::array<double, N_INTRA_DATES> strategy_intra_life_prices;
    std::array<double, N_INTRA_DATES> strategy_intra_life_pnl;
    double sum_intra_pnl = 0.0;
    for (int t = 0; t < N_INTRA_DATES; ++t) {
        double total_value = 0.0;
        double total_pnl_t = 0.0;
        for (size_t i = 0; i < n_options; ++i) {
            const int s = signs[i];
            total_value += s * options[i]->intra_life_prices[t];
            total_pnl_t += s * options[i]->intra_life_pnl[t];
        }
        strategy_intra_life_prices[t] = total_value;
        strategy_intra_life_pnl[t] = total_pnl_t;
        sum_intra_pnl += total_pnl_t;
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
    // Breakeven inline: copie depuis le buffer stack
    result.breakeven_count = breakeven_count;
    for (int b = 0; b < breakeven_count; ++b) {
        result.breakeven_points[b] = breakeven_buf[b];
    }
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
