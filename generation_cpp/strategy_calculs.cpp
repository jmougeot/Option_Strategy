#include "strategy_metrics.hpp"
#include <numeric>
#include <cmath>

// ============================================================================
// CALCULS
// ============================================================================

namespace strategy {

double StrategyCalculator::avg_pnl_levrage(
    const double total_average_pnl,
    const double premium
) {
    return total_average_pnl /(std::max(std::abs(premium) , 0.005));
}

} // namespace strategy
