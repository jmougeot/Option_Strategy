/**
 * Système de Scoring et Ranking des Stratégies - Header
 * Implémentation C++ du système de comparaison multi-critères
 */

#pragma once

#include <vector>
#include <string>
#include <algorithm>
#include <cmath>
#include <limits>

namespace strategy {

// ============================================================================
// ENUMS ET TYPES
// ============================================================================

enum class ScorerType {
    HIGHER_BETTER,      // Plus élevé = meilleur
    LOWER_BETTER,       // Plus bas = meilleur
    MODERATE_BETTER,    // Valeur modérée = meilleur (autour de 0.5)
    POSITIVE_BETTER     // Valeur positive = meilleur
};

enum class NormalizerType {
    MAX,                // Normalisation par maximum
    MIN_MAX,           // Normalisation min-max
    COUNT              // Normalisation pour compteurs
};

/**
 * Identifiant numérique des métriques (évite les comparaisons de strings dans le hot path)
 */
enum class MetricId : int {
    PREMIUM = 0,
    AVERAGE_PNL,
    ROLL,
    AVG_PNL_LEVRAGE,
    TAIL_PENALTY,
    AVG_INTRA_LIFE_PNL,
    METRIC_COUNT  // Nombre total de métriques
};

/**
 * Configuration d'une métrique de scoring
 */
struct MetricConfig {
    std::string name;
    MetricId id;        // Identifiant numérique pour accès rapide
    double weight;
    NormalizerType normalizer;
    ScorerType scorer;
    
    MetricConfig(const std::string& n, MetricId mid, double w, NormalizerType norm, ScorerType sc)
        : name(n), id(mid), weight(w), normalizer(norm), scorer(sc) {}
};

/**
 * Résultat d'une stratégie avec score et rang
 */
struct ScoredStrategy {
    // Métriques de la stratégie
    double total_premium;
    double total_delta;
    double total_iv;
    double average_pnl;
    double roll;
    double sigma_pnl;
    double max_profit;
    double max_loss;
    double max_loss_left;
    double max_loss_right;
    double min_profit_price;
    double max_profit_price;
    double profit_zone_width;
    double delta_levrage;
    double avg_pnl_levrage;
    int call_count;
    int put_count;

    std::vector<double> breakeven_points;
    
    // P&L array pour la stratégie complète
    std::vector<double> total_pnl_array;
    
    // Prix intra-vie (valeur de la stratégie à dates intermédiaires)
    std::array<double, 5> intra_life_prices;  // [V_t1, V_t2, V_t3, V_t4, V_t5]
    std::array<double, 5> intra_life_pnl;     // P&L moyen à chaque date
    double avg_intra_life_pnl;                // Moyenne des P&L intra-vie
    
    // Indices des options et signes
    std::vector<int> option_indices;
    std::vector<int> signs;
    
    // Strikes et types (pour détection de doublons)
    std::vector<double> strikes;
    std::vector<bool> is_calls;
    
    // Score et rang
    double score;
    int rank;
    
    ScoredStrategy() 
        : total_premium(0), total_delta(0), total_iv(0), average_pnl(0),
                    roll(0), max_profit(0), max_loss(0),
          max_loss_left(0), max_loss_right(0),
          min_profit_price(0), max_profit_price(0), profit_zone_width(0),
          delta_levrage(0), avg_pnl_levrage(0), call_count(0), put_count(0),
          intra_life_prices{}, intra_life_pnl{}, avg_intra_life_pnl(0), score(0), rank(0) {}
};

// ============================================================================
// CLASSE PRINCIPALE
// ============================================================================

class StrategyScorer {
public:
    static std::vector<MetricConfig> create_default_metrics();
    
    static void normalize_weights(std::vector<MetricConfig>& metrics);

    static std::vector<double> extract_metric_values(
        const std::vector<ScoredStrategy>& strategies,
        const std::string& metric_name
    );
    
    static std::pair<double, double> normalize_values(
        const std::vector<double>& values,
        NormalizerType normalizer
    );
    
    static double calculate_score(
        double value,
        double min_val,
        double max_val,
        ScorerType scorer
    );
    
    /**
     * Filtre les stratégies doublons (même profil P&L)
     */
    static std::vector<ScoredStrategy> remove_duplicates(
        const std::vector<ScoredStrategy>& strategies,
        int decimals = 4,
        int max_unique = 0
    );
    
    /**
     * Multi-weight scoring : normalise une seule fois, score N jeux de poids.
     *
     * @param strategies      Toutes les stratégies candidates (modifié in-place pour score)
     * @param weight_sets     Liste de vecteurs de MetricConfig (un par weight set)
     * @param top_n           Nombre de résultats par set
     * @return                Pair : (per-set top_n lists, consensus top_n)
     */
    static std::pair<
        std::vector<std::vector<ScoredStrategy>>,  // per-set results
        std::vector<ScoredStrategy>                 // consensus
    > multi_score_and_rank(
        std::vector<ScoredStrategy>& strategies,
        const std::vector<std::vector<MetricConfig>>& weight_sets,
        int top_n = 10
    );

private:
    static bool are_same_payoff(
        const ScoredStrategy& s1,
        const ScoredStrategy& s2
    );
};

} // namespace strategy
