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
    
    // Greeks (optimisés pour neutralité)
    metrics.emplace_back("delta_neutral", 0.0, NormalizerType::MAX, ScorerType::LOWER_BETTER);
    metrics.emplace_back("gamma_low", 0.00, NormalizerType::MAX, ScorerType::LOWER_BETTER);
    metrics.emplace_back("vega_low", 0.00, NormalizerType::MAX, ScorerType::LOWER_BETTER);
    metrics.emplace_back("theta_positive", 0.0, NormalizerType::MIN_MAX, ScorerType::HIGHER_BETTER);
    metrics.emplace_back("premium", 0.0, NormalizerType::MAX, ScorerType::LOWER_BETTER);  // Plus proche de 0 = meilleur (poids augmenté)
    // Volatilité
    metrics.emplace_back("implied_vol_moderate", 0.00, NormalizerType::MIN_MAX, ScorerType::MODERATE_BETTER);
    
    // Métriques gaussiennes (mixture)
    metrics.emplace_back("average_pnl", 0.00 , NormalizerType::MIN_MAX, ScorerType::HIGHER_BETTER);
    metrics.emplace_back("roll", 0.00, NormalizerType::MIN_MAX, ScorerType::HIGHER_BETTER);
    metrics.emplace_back("roll_quarterly", 0.00, NormalizerType::MIN_MAX, ScorerType::HIGHER_BETTER);
    metrics.emplace_back("sigma_pnl", 0.0, NormalizerType::MAX, ScorerType::LOWER_BETTER);
    
    // Métriques de levier (valeur absolue élevée = meilleur)
    metrics.emplace_back("delta_levrage", 0.00, NormalizerType::MAX, ScorerType::HIGHER_BETTER);
    metrics.emplace_back("avg_pnl_levrage", 0.0, NormalizerType::MAX, ScorerType::HIGHER_BETTER);
    
    // Métrique de risque
    metrics.emplace_back("max_loss", 0.0, NormalizerType::MAX, ScorerType::LOWER_BETTER);  // Perte plus faible = meilleur
    
    // Tail penalty (risque de perte - plus faible = meilleur)
    // MIN_MAX pour mieux différencier les valeurs dans une plage étroite
    metrics.emplace_back("tail_penalty", 0.0, NormalizerType::MIN_MAX, ScorerType::LOWER_BETTER);
    
    // Moyenne des P&L intra-vie (plus élevé = meilleur)
    metrics.emplace_back("avg_intra_life_pnl", 0.0, NormalizerType::MIN_MAX, ScorerType::HIGHER_BETTER);
    
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
        } else if (metric_name == "delta_levrage") {
            value = strat.delta_levrage;
        } else if (metric_name == "avg_pnl_levrage") {
            value = strat.avg_pnl_levrage;
        } else if (metric_name == "premium") {
            value = std::abs(strat.total_premium);  // Valeur absolue pour centrer autour de 0
        } else if (metric_name == "max_loss") {
            value = std::abs(strat.max_loss);  // Valeur absolue de la perte max
        } else if (metric_name == "tail_penalty") {
            // Valeur brute - MIN_MAX normalisera automatiquement
            value = std::abs(strat.tail_penalty);
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
// FILTRE DE DOUBLONS - OPTIMISÉ AVEC HASH
// ============================================================================

// Fonction de hash pour un vecteur de P&L arrondi
static size_t hash_pnl_array(const std::vector<double>& pnl, int decimals) {
    double factor = std::pow(10.0, decimals);
    size_t hash = 0;
    
    // Échantillonner quelques points pour le hash (début, milieu, fin)
    std::vector<size_t> sample_indices;
    if (pnl.size() > 0) sample_indices.push_back(0);
    if (pnl.size() > 10) sample_indices.push_back(pnl.size() / 4);
    if (pnl.size() > 5) sample_indices.push_back(pnl.size() / 2);
    if (pnl.size() > 10) sample_indices.push_back(3 * pnl.size() / 4);
    if (pnl.size() > 1) sample_indices.push_back(pnl.size() - 1);
    
    for (size_t idx : sample_indices) {
        long long rounded = static_cast<long long>(std::round(pnl[idx] * factor));
        hash ^= std::hash<long long>{}(rounded) + 0x9e3779b9 + (hash << 6) + (hash >> 2);
    }
    return hash;
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

        // Vérifier si cette stratégie est un doublon d'une stratégie déjà dans uniques
        // Utilise la logique: même strikes + même signs + nombre pair de diff call/put
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
// SCORING ET RANKING PRINCIPAL - OPTIMISÉ AVEC MIN-HEAP
// ============================================================================

static double extract_single_metric_value(const ScoredStrategy& strat, const std::string& metric_name) {
    if (metric_name == "delta_neutral") {
        return std::abs(strat.total_delta);
    } else if (metric_name == "gamma_low") {
        return std::abs(strat.total_gamma);
    } else if (metric_name == "vega_low") {
        return std::abs(strat.total_vega);
    } else if (metric_name == "theta_positive") {
        return strat.total_theta;
    } else if (metric_name == "implied_vol_moderate") {
        return strat.avg_implied_volatility;
    } else if (metric_name == "average_pnl") {
        return strat.average_pnl;
    } else if (metric_name == "roll") {
        return strat.roll;
    } else if (metric_name == "roll_quarterly") {
        return strat.roll_quarterly;
    } else if (metric_name == "sigma_pnl") {
        return strat.sigma_pnl;
    } else if (metric_name == "delta_levrage") {
        return strat.delta_levrage;
    } else if (metric_name == "avg_pnl_levrage") {
        return strat.avg_pnl_levrage;
    } else if (metric_name == "premium") {
        return std::abs(strat.total_premium);
    } else if (metric_name == "max_loss") {
        return std::abs(strat.max_loss);
    } else if (metric_name == "tail_penalty") {
        // Valeur brute - MIN_MAX normalisera automatiquement
        return std::abs(strat.tail_penalty);
    }
    return 0.0;
}

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
    
    // ========== ÉTAPE 1: Calculer min/max pour TOUTES les métriques en un seul passage ==========
    std::vector<double> metric_mins(n_metrics, std::numeric_limits<double>::max());
    std::vector<double> metric_maxs(n_metrics, std::numeric_limits<double>::lowest());
    
    for (const auto& strat : strategies) {
        for (size_t j = 0; j < n_metrics; ++j) {
            double value = extract_single_metric_value(strat, metrics[j].name);
            if (std::isfinite(value)) {
                metric_mins[j] = std::min(metric_mins[j], value);
                metric_maxs[j] = std::max(metric_maxs[j], value);
            }
        }
    }
    
    // Corriger les cas où min == max
    for (size_t j = 0; j < n_metrics; ++j) {
        if (metric_mins[j] == metric_maxs[j]) {
            metric_maxs[j] = metric_mins[j] + 1.0;
        }
        if (metric_mins[j] == std::numeric_limits<double>::max()) {
            metric_mins[j] = 0.0;
            metric_maxs[j] = 1.0;
        }
    }
    
    // ========== ÉTAPE 2: Scorer et maintenir top_n avec un min-heap d'INDICES ==========
    // Stocker (score, index) pour éviter de copier les gros objets ScoredStrategy
    using ScoreIndex = std::pair<double, size_t>;
    auto cmp = [](const ScoreIndex& a, const ScoreIndex& b) {
        return a.first > b.first;  // Min-heap: plus petit score en haut
    };
    std::priority_queue<ScoreIndex, std::vector<ScoreIndex>, decltype(cmp)> min_heap(cmp);
    
    for (size_t idx = 0; idx < strategies.size(); ++idx) {
        auto& strat = strategies[idx];
        
        // ========== MOYENNE GÉOMÉTRIQUE PONDÉRÉE AVEC PLANCHER ==========
        // S = exp(Σ wᵢ × log(ε + xᵢ))
        // Équivalent à: S = ∏(ε + xᵢ)^wᵢ
        
        constexpr double epsilon = 1e-6;  // Plancher pour éviter log(0)
        double log_sum = 0.0;
        double total_weight = 0.0;
        
        for (size_t j = 0; j < n_metrics; ++j) {
            if (metrics[j].weight <= 0.0) continue;  // Skip poids nuls
            
            double value = extract_single_metric_value(strat, metrics[j].name);
            double min_val = metric_mins[j];
            double max_val = metric_maxs[j];
            
            // xᵢ ∈ [0,1] - score normalisé
            double metric_score = calculate_score(value, min_val, max_val, metrics[j].scorer);
            
            // log(ε + xᵢ) pondéré par wᵢ
            log_sum += metrics[j].weight * std::log(epsilon + metric_score);
            total_weight += metrics[j].weight;
        }
        
        // S = exp(log_sum / total_weight) si on veut normaliser les poids
        // Ou S = exp(log_sum) si les poids sont déjà normalisés
        double final_score = (total_weight > 0.0) ? std::exp(log_sum) : 0.0;
        
        strat.score = final_score;
        
        // Ajouter l'index au heap (pas l'objet complet!)
        if (static_cast<int>(min_heap.size()) < top_n) {
            min_heap.push({final_score, idx});
        } else if (final_score > min_heap.top().first) {
            min_heap.pop();
            min_heap.push({final_score, idx});
        }
    }
    
    // ========== ÉTAPE 3: Extraire les indices et construire le résultat ==========
    std::vector<size_t> top_indices;
    top_indices.reserve(min_heap.size());
    
    while (!min_heap.empty()) {
        top_indices.push_back(min_heap.top().second);
        min_heap.pop();
    }
    
    // Construire le résultat en utilisant std::move pour éviter les copies
    std::vector<ScoredStrategy> result;
    result.reserve(top_indices.size());
    
    for (size_t idx : top_indices) {
        result.push_back(std::move(strategies[idx]));
    }
    
    std::sort(result.begin(), result.end(),
        [](const ScoredStrategy& a, const ScoredStrategy& b) {
            return a.score > b.score;
        }
    );
    
    // Assigner les rangs
    for (size_t i = 0; i < result.size(); ++i) {
        result[i].rank = static_cast<int>(i + 1);
    }
    
    return result;
}

} // namespace strategy
