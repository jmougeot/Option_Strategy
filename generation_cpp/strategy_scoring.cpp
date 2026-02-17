/**
 * Implémentation du système de scoring et ranking
 */

#include "strategy_scoring.hpp"
#include <numeric>
#include <cmath>
#include <algorithm>
#include <iostream>
#include <unordered_map>
#include <queue>
#include <limits>

namespace strategy {

// ============================================================================
// CONFIGURATION DES MÉTRIQUES PAR DÉFAUT
// ============================================================================

std::vector<MetricConfig> StrategyScorer::create_default_metrics() {
    std::vector<MetricConfig> metrics;
    metrics.emplace_back("premium", MetricId::PREMIUM, 0.0, NormalizerType::MAX, ScorerType::LOWER_BETTER); 
    metrics.emplace_back("average_pnl", MetricId::AVERAGE_PNL, 0.00 , NormalizerType::MIN_MAX, ScorerType::HIGHER_BETTER);
    metrics.emplace_back("roll", MetricId::ROLL, 0.00, NormalizerType::MIN_MAX, ScorerType::HIGHER_BETTER);
    metrics.emplace_back("avg_pnl_levrage", MetricId::AVG_PNL_LEVRAGE, 0.0, NormalizerType::MAX, ScorerType::HIGHER_BETTER);    
    metrics.emplace_back("tail_penalty", MetricId::TAIL_PENALTY, 0.0, NormalizerType::MIN_MAX, ScorerType::LOWER_BETTER);
    metrics.emplace_back("avg_intra_life_pnl", MetricId::AVG_INTRA_LIFE_PNL, 0.0, NormalizerType::MIN_MAX, ScorerType::HIGHER_BETTER);
    
    return metrics;
}

// ============================================================================
// NORMALISATION DES POIDS
// ============================================================================

void StrategyScorer::normalize_weights(std::vector<MetricConfig>& metrics) {
    double total_weight = 0.0;
    for (const auto& metric : metrics) {
        total_weight += metric.weight;
    }  
    if (total_weight > 0.0) {
        for (auto& metric : metrics) {
            metric.weight /= total_weight;
        }
    }
}

// ============================================================================
// EXTRACTION DES VALEURS
// ============================================================================

std::vector<double> StrategyScorer::extract_metric_values(
    const std::vector<ScoredStrategy>& strategies,
    const std::string& metric_name
) {
    std::vector<double> values;
    values.reserve(strategies.size());
    
    for (const auto& strat : strategies) {
        double value = 0.0;
        if (metric_name == "average_pnl") {
            value = strat.average_pnl;
        } else if (metric_name == "roll") {
            value = strat.roll;
        } else if (metric_name == "delta_levrage") {
            value = strat.avg_pnl_levrage;
        } else if (metric_name == "premium") {
            value = std::abs(strat.total_premium);
        } else if (metric_name == "avg_intra_life_pnl") {
            value = strat.avg_intra_life_pnl;
        }
        if (std::isfinite(value)) {
            values.push_back(value);
        } else {
            values.push_back(0.0);
        }
    }
    
    return values;
}

// ============================================================================
// NORMALISATION
// ============================================================================

std::pair<double, double> StrategyScorer::normalize_values(
    const std::vector<double>& values,
    NormalizerType normalizer
) {
    if (values.empty()) {
        return {0.0, 1.0};
    }
    
    // Filtrer les valeurs valides (finies)
    std::vector<double> valid_values;
    for (double v : values) {
        if (std::isfinite(v)) {
            valid_values.push_back(v);
        }
    }
    if (valid_values.empty()) {
        return {0.0, 1.0};
    }
    switch (normalizer) {
        case NormalizerType::MAX: {
            double max_val = *std::max_element(valid_values.begin(), valid_values.end());
            return {0.0, max_val != 0.0 ? max_val : 1.0};
        }
        
        case NormalizerType::MIN_MAX: {
            auto minmax = std::minmax_element(valid_values.begin(), valid_values.end());
            double min_val = *minmax.first;
            double max_val = *minmax.second;
            if (max_val == min_val) {
                return {min_val, min_val + 1.0};  // Éviter division par zéro
            }
            return {min_val, max_val};
        }  
        default:
            return {0.0, 1.0};
    }
}

// ============================================================================
// SCORING
// ============================================================================

double StrategyScorer::calculate_score(
    double value,
    double min_val,
    double max_val,
    ScorerType scorer
) {
    if (!std::isfinite(value)) {
        return 0.0;
    }
    
    switch (scorer) {
        case ScorerType::HIGHER_BETTER: {
            // Plus élevé = meilleur — normalisé sur [min, max]
            if (max_val > min_val) {
                double normalized = (value - min_val) / (max_val - min_val);
                return std::clamp(normalized, 0.0, 1.0);
            }
            return 0.0;
        }
        case ScorerType::LOWER_BETTER: {
            // Plus bas = meilleur
            if (max_val > min_val) {
                double normalized = (value - min_val) / (max_val - min_val);
                return std::clamp(1.0 - normalized, 0.0, 1.0);
            }
            return 0.0;
        }
        
        default:
            return 0.0;
    }
}

bool StrategyScorer::are_same_payoff(
    const ScoredStrategy& s1,
    const ScoredStrategy& s2
) {
    // 1. Vérifier que les tailles sont identiques
    if (s1.strikes.size() != s2.strikes.size()) {
        return false;
    }
    
    const size_t n = s1.strikes.size();
    
    // 2. Créer des triplets (strike, sign, is_call) triés par (strike, sign)
    struct Leg {
        double strike;
        int sign;
        bool is_call;
    };
    
    std::vector<Leg> legs1(n), legs2(n);
    for (size_t i = 0; i < n; i++) {
        legs1[i] = {s1.strikes[i], s1.signs[i], s1.is_calls[i]};
        legs2[i] = {s2.strikes[i], s2.signs[i], s2.is_calls[i]};
    }
    
    // Trier par (strike, sign)
    auto cmp = [](const Leg& a, const Leg& b) {
        if (std::abs(a.strike - b.strike) > 1e-6) return a.strike < b.strike;
        return a.sign < b.sign;
    };
    std::sort(legs1.begin(), legs1.end(), cmp);
    std::sort(legs2.begin(), legs2.end(), cmp);
    
    // 3. Vérifier que les strikes et signs sont identiques
    for (size_t i = 0; i < n; i++) {
        if (std::abs(legs1[i].strike - legs2[i].strike) > 1e-6 || legs1[i].sign != legs2[i].sign) {
            return false;
        }
    }

    // 4. Compter le nombre de différences call/put pour chaque (strike, sign)
    int diff_count = 0;
    for (size_t i = 0; i < n; i++) {
        if (legs1[i].is_call != legs2[i].is_call) {
            diff_count++;
        }
    }
    
    // 5. Si nombre pair de différences → vérifier le max_loss pour confirmer
    if (diff_count % 2 != 0) {
        return false; 
    }
    
    double max_loss_diff = std::abs(s1.max_loss - s2.max_loss);
    
    if (max_loss_diff > 0.05) {
            return false; 
        }
    
    return true;  // Même payoff confirmé
}

std::vector<ScoredStrategy> StrategyScorer::remove_duplicates(
    const std::vector<ScoredStrategy>& strategies,
    int decimals,
    int max_unique
) {
    if (strategies.empty()) {
        return {};
    }
    
    std::vector<ScoredStrategy> uniques;
    uniques.reserve(max_unique > 0 ? max_unique : strategies.size());
    
    int duplicates_count = 0;
    
    // Pour chaque stratégie
    for (size_t idx = 0; idx < strategies.size(); ++idx) {
        // Arrêter dès qu'on a assez de stratégies uniques
        if (max_unique > 0 && static_cast<int>(uniques.size()) >= max_unique) {
            break;
        }
        const auto& strat = strategies[idx];
        bool is_duplicate = false;

        for (size_t i = 0; i < uniques.size(); i++) {
            const auto& unique = uniques[i];
            if (are_same_payoff(strat, unique)) {
                is_duplicate = true;
                duplicates_count++;
                break;
            }
        }
        if (!is_duplicate) {
            uniques.push_back(strat);
        }
    }
    
    if (duplicates_count > 0) {
        std::cout << " C++ filtre doublons: " << duplicates_count << " strat en double elimine" << std::endl;
    }
    
    return uniques;
}

// ============================================================================
// EXTRACTION DE VALEUR PAR MÉTRIQUE
// ============================================================================

static double extract_single_metric_value(const ScoredStrategy& strat, const std::string& metric_name) {
    if (metric_name == "average_pnl") {
        return strat.average_pnl;
    } else if (metric_name == "roll") {
        return strat.roll;
    } else if (metric_name == "avg_pnl_levrage") {
        return strat.avg_pnl_levrage;
    } else if (metric_name == "premium") {
        return std::abs(strat.total_premium);
    } else if (metric_name == "avg_intra_life_pnl") {
        return strat.avg_intra_life_pnl;
    }
    return 0.0;
}

/**
 * Version rapide par MetricId — évite les comparaisons de std::string 
 * dans les boucles chaudes du scoring (appelée N_strats × N_metrics fois)
 */
static inline double extract_metric_by_id(const ScoredStrategy& strat, MetricId id) {
    switch (id) {
        case MetricId::PREMIUM:           return std::abs(strat.total_premium);
        case MetricId::AVERAGE_PNL:       return strat.average_pnl;
        case MetricId::ROLL:              return strat.roll;
        case MetricId::AVG_PNL_LEVRAGE:   return strat.avg_pnl_levrage;
        case MetricId::TAIL_PENALTY:      return 0.0; // placeholder
        case MetricId::AVG_INTRA_LIFE_PNL: return strat.avg_intra_life_pnl;
        default:                          return 0.0;
    }
}

// ============================================================================
// MULTI-WEIGHT SCORING — normalisation commune, N rankings
// ============================================================================

std::pair<
    std::vector<std::vector<ScoredStrategy>>,
    std::vector<ScoredStrategy>
> StrategyScorer::multi_score_and_rank(
    std::vector<ScoredStrategy>& strategies,
    const std::vector<std::vector<MetricConfig>>& weight_sets,
    int top_n
) {
    std::vector<std::vector<ScoredStrategy>> per_set_results;

    if (strategies.empty() || weight_sets.empty()) {
        return {per_set_results, {}};
    }

    const size_t n_strats = strategies.size();
    const size_t n_sets = weight_sets.size();

    // ====== 1. Collect ALL metric IDs across every weight set ======
    // Utiliser MetricId (enum int) au lieu de strings pour les lookups
    std::vector<MetricId> all_metric_ids;
    {
        bool seen[static_cast<int>(MetricId::METRIC_COUNT)] = {};
        for (const auto& ws : weight_sets) {
            for (const auto& mc : ws) {
                int mid = static_cast<int>(mc.id);
                if (mid < static_cast<int>(MetricId::METRIC_COUNT) && !seen[mid]) {
                    seen[mid] = true;
                    all_metric_ids.push_back(mc.id);
                }
            }
        }
    }
    const size_t n_metrics = all_metric_ids.size();

    // ====== 2. Common normalisation: compute min/max for every metric ======
    struct NormInfo {
        NormalizerType normalizer;
        ScorerType scorer;
        double min_val;
        double max_val;
    };
    // Tableau fixe indexé par MetricId (pas de hash map)
    NormInfo norm_table[static_cast<int>(MetricId::METRIC_COUNT)];
    
    // First pass: figure out normalizer / scorer from the default metrics
    auto defaults = create_default_metrics();
    for (auto& d : defaults) {
        int mid = static_cast<int>(d.id);
        norm_table[mid] = {d.normalizer, d.scorer,
                           std::numeric_limits<double>::max(),
                           std::numeric_limits<double>::lowest()};
    }

    // Second pass: scan ALL strategies to find global min/max
    for (const auto& strat : strategies) {
        for (auto mid : all_metric_ids) {
            double v = extract_metric_by_id(strat, mid);
            if (std::isfinite(v)) {
                auto& ni = norm_table[static_cast<int>(mid)];
                if (v < ni.min_val) ni.min_val = v;
                if (v > ni.max_val) ni.max_val = v;
            }
        }
    }

    // Fix degenerate ranges
    for (auto mid : all_metric_ids) {
        auto& ni = norm_table[static_cast<int>(mid)];
        if (ni.min_val == std::numeric_limits<double>::max()) {
            ni.min_val = 0.0;
            ni.max_val = 1.0;
        }
        if (ni.min_val == ni.max_val) {
            ni.max_val = ni.min_val + 1.0;
        }
    }

    // ====== 3. Pre-compute normalised metric scores per strategy ======
    // Tableau contigu [MetricId][strat] — pas de hash map
    constexpr int N_METRIC_IDS = static_cast<int>(MetricId::METRIC_COUNT);
    std::vector<std::vector<double>> metric_scores_table(N_METRIC_IDS);
    for (auto mid : all_metric_ids) {
        int midx = static_cast<int>(mid);
        auto& ni = norm_table[midx];
        auto& scores = metric_scores_table[midx];
        scores.resize(n_strats);
        for (size_t i = 0; i < n_strats; ++i) {
            double v = extract_metric_by_id(strategies[i], mid);
            scores[i] = calculate_score(v, ni.min_val, ni.max_val, ni.scorer);
        }
    }

    // ====== 4. For each weight set, score all strategies & keep top N ======
    std::vector<std::vector<double>> all_set_scores(n_sets); // [set][strat]

    for (size_t s = 0; s < n_sets; ++s) {
        const auto& ws = weight_sets[s];

        // Normalise weights for this set
        double total_w = 0.0;
        for (const auto& mc : ws) total_w += mc.weight;
        if (total_w <= 0.0) total_w = 1.0;

        all_set_scores[s].resize(n_strats);

        for (size_t i = 0; i < n_strats; ++i) {
            // Geometric mean scoring
            constexpr double epsilon = 1e-6;
            double log_sum = 0.0;

            for (const auto& mc : ws) {
                if (mc.weight <= 0.0) continue;
                double w_norm = mc.weight / total_w;
                int midx = static_cast<int>(mc.id);
                double ms = 0.0;
                if (midx < N_METRIC_IDS && !metric_scores_table[midx].empty()) {
                    ms = metric_scores_table[midx][i];
                }
                log_sum += w_norm * std::log(epsilon + ms);
            }

            all_set_scores[s][i] = std::exp(log_sum);
        }

        // Build top_n for this set using min-heap of indices
        using SI = std::pair<double, size_t>;
        auto cmp = [](const SI& a, const SI& b) { return a.first > b.first; };
        std::priority_queue<SI, std::vector<SI>, decltype(cmp)> heap(cmp);

        for (size_t i = 0; i < n_strats; ++i) {
            double sc = all_set_scores[s][i];
            if (static_cast<int>(heap.size()) < top_n) {
                heap.push({sc, i});
            } else if (sc > heap.top().first) {
                heap.pop();
                heap.push({sc, i});
            }
        }
        
        // Extract, sort, remove duplicates
        std::vector<size_t> top_idx;
        top_idx.reserve(heap.size());
        while (!heap.empty()) {
            top_idx.push_back(heap.top().second);
            heap.pop();
        }

        std::vector<ScoredStrategy> set_result;
        set_result.reserve(top_idx.size());
        for (size_t idx : top_idx) {
            ScoredStrategy copy = strategies[idx]; // copy for per-set result
            copy.score = all_set_scores[s][idx];
            set_result.push_back(std::move(copy));
        }

        std::sort(set_result.begin(), set_result.end(),
            [](const ScoredStrategy& a, const ScoredStrategy& b) {
                return a.score > b.score;
            });

        for (size_t i = 0; i < set_result.size(); ++i) {
            set_result[i].rank = static_cast<int>(i + 1);
        }

        // Deduplicate
        auto unique = remove_duplicates(set_result, 4, top_n);
        per_set_results.push_back(std::move(unique));
    }

    // ====== 5. Meta ranking via total score (sum of per-set scores) ======
    std::vector<double> total_score(n_strats, 0.0);
    for (size_t i = 0; i < n_strats; ++i) {
        for (size_t s = 0; s < n_sets; ++s) {
            total_score[i] += all_set_scores[s][i];
        }
    }

    // Top_n by highest total score (use min-heap)
    using ARI = std::pair<double, size_t>; // (total_score, idx) — higher is better
    auto cmp_ar = [](const ARI& a, const ARI& b) { return a.first > b.first; }; // min-heap = worst at top
    std::priority_queue<ARI, std::vector<ARI>, decltype(cmp_ar)> cons_heap(cmp_ar);

    for (size_t i = 0; i < n_strats; ++i) {
        if (static_cast<int>(cons_heap.size()) < top_n) {
            cons_heap.push({total_score[i], i});
        } else if (total_score[i] > cons_heap.top().first) {
            cons_heap.pop();
            cons_heap.push({total_score[i], i});
        }
    }

    std::vector<ScoredStrategy> consensus;
    consensus.reserve(cons_heap.size());
    while (!cons_heap.empty()) {
        size_t idx = cons_heap.top().second;
        ScoredStrategy copy = strategies[idx];
        copy.score = total_score[idx];
        cons_heap.pop();
        consensus.push_back(std::move(copy));
    }

    std::sort(consensus.begin(), consensus.end(),
        [](const ScoredStrategy& a, const ScoredStrategy& b) {
            return a.score > b.score;
        });

    for (size_t i = 0; i < consensus.size(); ++i) {
        consensus[i].rank = static_cast<int>(i + 1);
    }

    auto unique_consensus = remove_duplicates(consensus, 4, top_n);

    return {per_set_results, unique_consensus};
}

} // namespace strategy
