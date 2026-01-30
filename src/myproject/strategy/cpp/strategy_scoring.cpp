/**
 * Implémentation du système de scoring et ranking
 */

#include "strategy_scoring.hpp"
#include <numeric>
#include <cmath>
#include <algorithm>
#include <iostream>

namespace strategy {

// ============================================================================
// CONFIGURATION DES MÉTRIQUES PAR DÉFAUT
// ============================================================================

std::vector<MetricConfig> StrategyScorer::create_default_metrics() {
    std::vector<MetricConfig> metrics;
    
    // Greeks (optimisés pour neutralité)
    metrics.emplace_back("delta_neutral", 0.08, NormalizerType::MAX, ScorerType::LOWER_BETTER);
    metrics.emplace_back("gamma_low", 0.05, NormalizerType::MAX, ScorerType::LOWER_BETTER);
    metrics.emplace_back("vega_low", 0.05, NormalizerType::MAX, ScorerType::LOWER_BETTER);
    metrics.emplace_back("theta_positive", 0.05, NormalizerType::MIN_MAX, ScorerType::HIGHER_BETTER);
    
    // Volatilité
    metrics.emplace_back("implied_vol_moderate", 0.04, NormalizerType::MIN_MAX, ScorerType::MODERATE_BETTER);
    
    // Métriques gaussiennes (mixture)
    metrics.emplace_back("average_pnl", 0.20, NormalizerType::MIN_MAX, ScorerType::HIGHER_BETTER);
    metrics.emplace_back("roll", 0.06, NormalizerType::MIN_MAX, ScorerType::HIGHER_BETTER);
    metrics.emplace_back("roll_quarterly", 0.06, NormalizerType::MIN_MAX, ScorerType::HIGHER_BETTER);
    metrics.emplace_back("sigma_pnl", 0.05, NormalizerType::MAX, ScorerType::LOWER_BETTER);
    
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
        
        if (metric_name == "delta_neutral") {
            value = std::abs(strat.total_delta);
        } else if (metric_name == "gamma_low") {
            value = std::abs(strat.total_gamma);
        } else if (metric_name == "vega_low") {
            value = std::abs(strat.total_vega);
        } else if (metric_name == "theta_positive") {
            value = strat.total_theta;
        } else if (metric_name == "implied_vol_moderate") {
            value = strat.avg_implied_volatility;
        } else if (metric_name == "average_pnl") {
            value = strat.average_pnl;
        } else if (metric_name == "roll") {
            value = strat.roll;
        } else if (metric_name == "roll_quarterly") {
            value = strat.roll_quarterly;
        } else if (metric_name == "sigma_pnl") {
            value = strat.sigma_pnl;
        }
        
        // Filtrer les valeurs non finies
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
        
        case NormalizerType::COUNT: {
            auto minmax = std::minmax_element(valid_values.begin(), valid_values.end());
            double min_val = *minmax.first;
            double max_val = *minmax.second;
            if (max_val == min_val) {
                return {min_val, min_val + 1.0};
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
            // Plus élevé = meilleur
            if (max_val > 0.0) {
                return std::clamp(value / max_val, 0.0, 1.0);
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
        
        case ScorerType::MODERATE_BETTER: {
            // Valeur modérée = meilleur (autour de 0.5)
            if (max_val > 0.0) {
                double normalized = value / max_val;
                double score = 1.0 - std::abs(normalized - 0.5) * 2.0;
                return std::max(0.0, score);
            }
            return 0.0;
        }
        
        case ScorerType::POSITIVE_BETTER: {
            // Valeur positive = meilleur
            if (value >= 0.0 && max_val > min_val) {
                return std::clamp((value - min_val) / (max_val - min_val), 0.0, 1.0);
            }
            return 0.0;
        }
        
        default:
            return 0.0;
    }
}

// ============================================================================
// FILTRE DE DOUBLONS
// ============================================================================

bool StrategyScorer::are_pnl_equal(
    const std::vector<double>& pnl1,
    const std::vector<double>& pnl2,
    int decimals
) {
    // Vérifier la taille
    if (pnl1.size() != pnl2.size()) {
        return false;
    }
    
    // Calculer le facteur de multiplication pour l'arrondi
    double factor = std::pow(10.0, decimals);
    
    // Comparer chaque valeur avec tolérance
    for (size_t i = 0; i < pnl1.size(); ++i) {
        double rounded1 = std::round(pnl1[i] * factor) / factor;
        double rounded2 = std::round(pnl2[i] * factor) / factor;
        
        if (std::abs(rounded1 - rounded2) > 1e-10) {
            return false;
        }
    }
    
    return true;
}

std::vector<ScoredStrategy> StrategyScorer::remove_duplicates(
    const std::vector<ScoredStrategy>& strategies,
    int decimals
) {
    if (strategies.empty()) {
        return {};
    }
    
    std::vector<ScoredStrategy> uniques;
    uniques.reserve(strategies.size());
    
    int duplicates_count = 0;
    
    // Pour chaque stratégie
    for (const auto& strat : strategies) {
        bool is_duplicate = false;
        
        // Vérifier si elle existe déjà dans uniques
        for (const auto& unique : uniques) {
            if (are_pnl_equal(strat.total_pnl_array, unique.total_pnl_array, decimals)) {
                is_duplicate = true;
                duplicates_count++;
                break;
            }
        }
        
        // Si pas un doublon, l'ajouter
        if (!is_duplicate) {
            uniques.push_back(strat);
        }
    }
    
    if (duplicates_count > 0) {
        std::cout << "  🔍 C++ filtre doublons: " << duplicates_count 
                  << " stratégies dupliquées éliminées (même profil P&L)" << std::endl;
        std::cout << "  ✅ " << uniques.size() << " stratégies uniques conservées" << std::endl;
    }
    
    return uniques;
}

// ============================================================================
// SCORING ET RANKING PRINCIPAL
// ============================================================================

std::vector<ScoredStrategy> StrategyScorer::score_and_rank(
    std::vector<ScoredStrategy>& strategies,
    std::vector<MetricConfig> metrics,
    int top_n
) {
    if (strategies.empty()) {
        return {};
    }
    
    // Utiliser métriques par défaut si non fournies
    if (metrics.empty()) {
        metrics = create_default_metrics();
    }
    
    // Normaliser les poids
    normalize_weights(metrics);
    
    const size_t n_strategies = strategies.size();
    const size_t n_metrics = metrics.size();
    
    // Matrice des scores: [n_strategies x n_metrics]
    std::vector<std::vector<double>> scores_matrix(
        n_strategies,
        std::vector<double>(n_metrics, 0.0)
    );
    
    // Pour chaque métrique
    for (size_t j = 0; j < n_metrics; ++j) {
        const auto& metric = metrics[j];
        
        // Extraire les valeurs de la métrique
        std::vector<double> values = extract_metric_values(strategies, metric.name);
        
        // Normaliser
        auto [min_val, max_val] = normalize_values(values, metric.normalizer);
        
        // Calculer les scores
        if (max_val > min_val || (max_val == min_val && max_val != 0.0)) {
            for (size_t i = 0; i < n_strategies; ++i) {
                scores_matrix[i][j] = calculate_score(
                    values[i],
                    min_val,
                    max_val,
                    metric.scorer
                );
            }
        }
    }
    
    // Calculer le score final pondéré pour chaque stratégie
    for (size_t i = 0; i < n_strategies; ++i) {
        double final_score = 0.0;
        for (size_t j = 0; j < n_metrics; ++j) {
            final_score += scores_matrix[i][j] * metrics[j].weight;
        }
        strategies[i].score = final_score;
    }
    
    // Trier par score décroissant
    std::sort(strategies.begin(), strategies.end(),
        [](const ScoredStrategy& a, const ScoredStrategy& b) {
            return a.score > b.score;
        }
    );
    
    // Limiter au top_n et assigner les rangs
    size_t result_size = std::min(static_cast<size_t>(top_n), n_strategies);
    std::vector<ScoredStrategy> result(strategies.begin(), strategies.begin() + result_size);
    
    for (size_t i = 0; i < result.size(); ++i) {
        result[i].rank = static_cast<int>(i + 1);
    }
    
    return result;
}

} // namespace strategy
