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

} // namespace strategy