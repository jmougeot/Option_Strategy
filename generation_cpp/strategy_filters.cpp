/**
* Definiton of filter — interface pointeur (zéro-copie)
 */

#include "strategy_metrics.hpp"
#include <numeric>
#include <cmath>

// ============================================================================
// FILTRES
// ============================================================================

namespace strategy {

bool StrategyCalculator::filter_useless_sell(
    const OptionData* const* options,
    const int* signs,
    size_t n_options,
    double min_premium_sell
) {
    // Éliminer la vente d'un put ou d'un call qui ne rapporte rien
    for (size_t i = 0; i < n_options; ++i) {
        if (signs[i] < 0 && options[i]->premium < min_premium_sell) {
            return false;  // Stratégie invalide
        }
    }
    return true;  // OK
}

bool StrategyCalculator::filter_same_option_buy_sell(
    const OptionData* const* options,
    const int* signs,
    size_t n_options
) {
    for (size_t i = 0; i < n_options; ++i) {
        for (size_t j = i + 1; j < n_options; ++j) {
            // Même type (call/put) et même strike mais signes opposés = inutile
            if (options[i]->is_call == options[j]->is_call &&
                options[i]->strike == options[j]->strike &&
                signs[i] != signs[j]) {
                return false;
            }
        }
    }
    return true;
}


bool StrategyCalculator::filter_put_open(
    const OptionData* const* options,
    const int* signs,
    size_t n_options,
    int ouvert_gauche
) {
    int long_put_count = 0;
    int short_put_count = 0;
    
    for (size_t i = 0; i < n_options; ++i) {
        if (!options[i]->is_call) {
            if (signs[i] > 0) {
                ++long_put_count;
            } else {
                ++short_put_count;
            }
        }
    }
    return (short_put_count - long_put_count) <= ouvert_gauche;
}

bool StrategyCalculator::filter_call_open(
    const OptionData* const* options,
    const int* signs,
    size_t n_options,
    int ouvert_droite
) {
    int long_call_count = 0;
    int short_call_count = 0;

    for (size_t i = 0; i < n_options; ++i) {
        if (options[i]->is_call) {
            if (signs[i] > 0) {
                ++long_call_count;
            } else {
                ++short_call_count;
            }
        }
    }
    return (short_call_count - long_call_count) <= ouvert_droite;
}


bool StrategyCalculator::filter_premium(
    const OptionData* const* options,
    const int* signs,
    size_t n_options,
    double max_premium_params,
    double& total_premium
) {
    total_premium = 0.0;
    for (size_t i = 0; i < n_options; ++i) {
        total_premium += signs[i] * options[i]->premium;
    }
    return std::abs(total_premium) <= max_premium_params;
}


bool StrategyCalculator::filter_delta(
    const OptionData* const* options,
    const int* signs,
    size_t n_options,
    double delta_min,
    double delta_max,
    double& total_delta
) {
    total_delta = 0.0;
    for (size_t i = 0; i < n_options; ++i) {
        total_delta += signs[i] * options[i]->delta;
    }
    return total_delta >= delta_min && total_delta <= delta_max;
}


bool StrategyCalculator::filter_average_pnl(
    const OptionData* const* options,
    const int* signs,
    size_t n_options,
    double& total_average_pnl
) {
    total_average_pnl = 0.0;
    for (size_t i = 0; i < n_options; ++i) {
        total_average_pnl += signs[i] * options[i]->average_pnl;
    }
    return total_average_pnl >= 0.0;
}

} // namespace strategy