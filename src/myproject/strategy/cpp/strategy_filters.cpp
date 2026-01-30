/**
* Definiton of filter
 */

#include "strategy_metrics.hpp"
#include <numeric>
#include <cmath>

// ============================================================================
// FILTRES
// ============================================================================

namespace strategy {

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


bool StrategyCalculator::filter_put_open(
    const std::vector<OptionData>& options,
    const std::vector<int>& signs,
    int ouvert_gauche
) {
    int long_put_count = 0;
    int short_put_count = 0;
    int put_count= 0;
    
    for (size_t i = 0; i < options.size(); ++i) {
        if (!options[i].is_call) {
            if (signs[i] > 0) {
                ++long_put_count;
            } else {
                ++short_put_count;
            }
        }
    }
    put_count = short_put_count - long_put_count;

    if (put_count > ouvert_gauche) {
        return false;
    }
    return true;
}

bool StrategyCalculator::filter_call_open(
    const std::vector<OptionData>& options,
    const std::vector<int>& signs,
    int ouvert_droite
) {
    int long_call_count = 0;
    int short_call_count = 0;
    int call_count = 0;

    for (size_t i = 0; i < options.size(); ++i) {
        if (options[i].is_call) {
            if (signs[i] > 0) {
                ++long_call_count;
            } else {
                ++short_call_count;
            }
        }
    }
    
    call_count = short_call_count - long_call_count;
    
    if (call_count > ouvert_droite) {
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
    double delta_min,
    double delta_max,
    double& total_delta
) {
    total_delta = 0.0;
    for (size_t i = 0; i < options.size(); ++i) {
        total_delta += signs[i] * options[i].delta;
    }
    return total_delta >= delta_min && total_delta <= delta_max;
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

} // namespace strategy