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
 * Configuration d'une métrique de scoring
 */
struct MetricConfig {
    std::string name;
    double weight;
    NormalizerType normalizer;
    ScorerType scorer;
    
    MetricConfig(const std::string& n, double w, NormalizerType norm, ScorerType sc)
        : name(n), weight(w), normalizer(norm), scorer(sc) {}
};

/**
 * Résultat d'une stratégie avec score et rang
 */
struct ScoredStrategy {
    // Métriques de la stratégie
    double total_premium;
    double total_delta;
    double total_gamma;
    double total_vega;
    double total_theta;
    double total_iv;  // Total IV (somme des IV)
    double avg_implied_volatility;
    double average_pnl;
    double roll;
    double roll_quarterly;
    double roll_sum;
    double sigma_pnl;
    double max_profit;
    double max_loss;
    double max_loss_left;
    double max_loss_right;
    double min_profit_price;
    double max_profit_price;
    double profit_zone_width;
    int call_count;
    int put_count;
    std::vector<double> breakeven_points;
    
    // P&L array pour la stratégie complète
    std::vector<double> total_pnl_array;
    
    // Indices des options et signes
    std::vector<int> option_indices;
    std::vector<int> signs;
    
    // Score et rang
    double score;
    int rank;
    
    ScoredStrategy() 
        : total_premium(0), total_delta(0), total_gamma(0), total_vega(0),
          total_theta(0), total_iv(0), avg_implied_volatility(0), average_pnl(0),
          roll(0), roll_quarterly(0), roll_sum(0), sigma_pnl(0),
          max_profit(0), max_loss(0), max_loss_left(0), max_loss_right(0),
          min_profit_price(0), max_profit_price(0), profit_zone_width(0),
          call_count(0), put_count(0), score(0), rank(0) {}
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
     * Vérifie si deux P&L arrays sont identiques (avec tolérance)
     * 
     * @param pnl1 Premier P&L array
     * @param pnl2 Deuxième P&L array
     * @param decimals Nombre de décimales pour la tolérance (défaut: 4)
     * @return true si les P&L sont identiques
     */
    static bool are_pnl_equal(
        const std::vector<double>& pnl1,
        const std::vector<double>& pnl2,
        int decimals = 4
    );
    
    /**
     * Filtre les stratégies doublons (même profil P&L)
     * 
     * @param strategies Vecteur de stratégies à filtrer
     * @param decimals Nombre de décimales pour la tolérance (défaut: 4)
     * @return Vecteur sans doublons (conserve la première occurrence)
     */
    static std::vector<ScoredStrategy> remove_duplicates(
        const std::vector<ScoredStrategy>& strategies,
        int decimals = 4
    );
    
    /**
     * Score et classe les stratégies selon les métriques configurées
     * 
     * @param strategies Vecteur de stratégies à scorer
     * @param metrics Configuration des métriques (optionnel, utilise défaut si vide)
     * @param top_n Nombre de meilleures stratégies à retourner
     * @return Vecteur de stratégies scorées et classées
     */
    static std::vector<ScoredStrategy> score_and_rank(
        std::vector<ScoredStrategy>& strategies,
        std::vector<MetricConfig> metrics = {},
        int top_n = 10
    );
};

} // namespace strategy
