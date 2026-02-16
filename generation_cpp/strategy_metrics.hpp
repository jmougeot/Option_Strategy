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

// Nombre de dates intermédiaires pour le pricing intra-vie
constexpr int N_INTRA_DATES = 5;

/**
 * Structure légère retournée par les calculs C++
 * Contient toutes les métriques calculées
 */
struct StrategyMetrics {
    // Greeks agrégés
    double total_premium;
    double total_delta;
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
        
    // Intra-vie pricing (prix à dates intermédiaires avec tilt terminal)
    std::array<double, N_INTRA_DATES> intra_life_prices;  // [V_t1, V_t2, V_t3, V_t4, V_t5]
    std::array<double, N_INTRA_DATES> intra_life_pnl;     // P&L moyen à chaque date
    double avg_intra_life_pnl;                            // Moyenne des P&L intra-vie
    
    // Breakeven points (max 10 pour éviter allocation dynamique)
    std::vector<double> breakeven_points;
    
    // P&L array complet
    std::vector<double> total_pnl_array;
};


/**
 * Données d'entrée pour une option (structure plate pour performance)
 */
struct OptionData {
    double premium;
    double delta;
    double implied_volatility;
    double average_pnl;
    double strike;
    double roll;            // Roll moyen (normalisé)
    bool is_call;
    // pnl_array sera passé séparément comme matrice
    
    // Intra-vie pricing (pré-calculé en Python)
    std::array<double, N_INTRA_DATES> intra_life_prices;  // Prix à dates intermédiaires
    std::array<double, N_INTRA_DATES> intra_life_pnl;     // P&L moyen à chaque date
};


/**
 * Classe principale pour les calculs de stratégie
 */
class StrategyCalculator {
public:

    static std::optional<StrategyMetrics> calculate(
        const std::vector<OptionData>& options,
        const std::vector<int>& signs,
        const std::vector<std::vector<double>>& pnl_matrix,
        const std::vector<double>& prices,
        const std::vector<double>& mixture,
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
        bool premium_only = false,
        bool premium_only_left = false,
        bool premium_only_right = false
    );

    static bool next_combination(
        std::vector<int>& c,
        const int N
    );

private:
    // Filtres (retourne false si la stratégie doit être rejetée)

    static bool filter_useless_sell(
        const std::vector<OptionData>& options,
        const std::vector<int>& signs,
        double min_premium_sell
    );
    
    static bool filter_same_option_buy_sell(
        const std::vector<OptionData>& options,
        const std::vector<int>& signs
    );
    
    static bool filter_put_open(
        const std::vector<OptionData>& options,
        const std::vector<int>& signs,
        int ouvert_gauche
    );
    
    static bool filter_call_open(
        const std::vector<OptionData>& options,
        const std::vector<int>& signs,
        int ouvert_droite
    );
    
    static bool filter_premium(
        const std::vector<OptionData>& options,
        const std::vector<int>& signs,
        double max_premium_params,
        double& total_premium
    );
    
    static bool filter_delta(
        const std::vector<OptionData>& options,
        const std::vector<int>& signs,
        double delta_min,
        double delta_max,
        double& total_delta
    );
    
    static bool filter_average_pnl(
        const std::vector<OptionData>& options,
        const std::vector<int>& signs,
        double& total_average_pnl
    );
    
    // Calculs
    static void calculate_greeks(
        const std::vector<OptionData>& options,
        const std::vector<int>& signs,
        double& total_iv
    );
    
    static std::vector<double> calculate_total_pnl(
        const std::vector<std::vector<double>>& pnl_matrix,
        const std::vector<int>& signs
    );
    
    static void calculate_profit_zone(
        const std::vector<double>& total_pnl,
        const std::vector<double>& prices,
        double& min_profit_price,
        double& max_profit_price,
        double& profit_zone_width
    );
    
    static std::vector<double> calculate_breakeven_points(
        const std::vector<double>& total_pnl,
        const std::vector<double>& prices
    );

    static double avg_pnl_levrage(
        const double total_average_pnl, 
        const double premium
    );
};

} // namespace strategy
