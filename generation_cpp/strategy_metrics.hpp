/**
 * Calculs Optimisés des Métriques de Stratégies d'Option
 * Header C++ pour les calculs "hot path"
 */

#pragma once

#include <vector>
#include <array>
#include <cmath>
#include <algorithm>
#include <optional>

namespace strategy {

/**
 * Structure légère retournée par les calculs C++
 * Contient toutes les métriques calculées
 */
struct StrategyMetrics {
    // Greeks agrégés
    double total_premium;
    double total_delta;
    double total_gamma;
    double total_theta;
    double total_iv;
    
    // P&L metrics
    double max_profit;
    double max_loss;
    double max_loss_left;   // Max loss à gauche de average_mix
    double max_loss_right;  // Max loss à droite de average_mix
    double total_average_pnl;
    
    // Profit zone
    double min_profit_price;
    double max_profit_price;
    double profit_zone_width;
    
    // Counts
    int call_count;
    int put_count;
    
    // Roll
    double total_roll;

    // Levrage
    double avg_pnl_levrage;
        
    // Breakeven points (inline buffer — évite allocation dynamique dans le hot path)
    static constexpr int MAX_BREAKEVEN = 10;
    std::array<double, MAX_BREAKEVEN> breakeven_points;
    int breakeven_count = 0;
    
    // P&L array complet
    std::vector<double> total_pnl_array;
};


/**
 * Données d'entrée pour une option (structure plate pour performance)
 */
struct OptionData {
    double premium;
    double delta;
    double gamma;
    double theta;
    double implied_volatility;
    double average_pnl;
    double strike;
    double roll;            // Roll moyen (normalisé)
    bool is_call;
    // pnl_array sera passé séparément comme matrice
};


/**
 * Classe principale pour les calculs de stratégie
 */
class StrategyCalculator {
public:

    /**
     * Calcule les métriques d'une stratégie.
     * Interface optimisée : pointeurs vers OptionData (zéro-copie depuis le cache).
     */
    static std::optional<StrategyMetrics> calculate(
        const OptionData* const* options,
        const int* signs,
        size_t n_options,
        const double* const* pnl_rows,
        size_t pnl_length,
        const double* prices,
        double average_mix,
        double max_loss_left,
        double max_loss_right,
        double max_premium_params,
        int ouvert_gauche,
        int ouvert_droite,
        double min_premium_sell,
        double delta_min,
        double delta_max,
        double limit_left,
        double limit_right,
        double* __restrict total_pnl_buf,
        bool premium_only = false,
        bool premium_only_left = false,
        bool premium_only_right = false,
        double leg_penalty = 0.0
    );

    static bool next_combination(
        std::vector<int>& c,
        const int N
    );



private:
    // Filtres (retourne false si la stratégie doit être rejetée)
    // Interface pointer pour zéro-copie

    static bool filter_useless_sell(
        const OptionData* const* options,
        const int* signs,
        size_t n_options,
        double min_premium_sell
    );
    
    static bool filter_same_option_buy_sell(
        const OptionData* const* options,
        const int* signs,
        size_t n_options
    );
    
    static double avg_pnl_levrage(
        const double total_average_pnl, 
        const double premium
    );
};

} // namespace strategy
