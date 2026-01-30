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
    double total_vega;
    double total_theta;
    double total_iv;
    
    // P&L metrics
    double max_profit;
    double max_loss;
    double max_loss_left;   // Max loss à gauche de average_mix
    double max_loss_right;  // Max loss à droite de average_mix
    double total_average_pnl;
    double total_sigma_pnl;
    
    // Profit zone
    double min_profit_price;
    double max_profit_price;
    double profit_zone_width;
    
    // Counts
    int call_count;
    int put_count;
    
    // Roll
    double total_roll;
    double total_roll_quarterly;
    double total_roll_sum;
    
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
    double gamma;
    double vega;
    double theta;
    double implied_volatility;
    double average_pnl;
    double sigma_pnl;
    double strike;
    double roll;            // Roll moyen (normalisé)
    double roll_quarterly;  // Roll Q-1 (trimestre précédent)
    double roll_sum;        // Roll brut (non normalisé)
    bool is_call;
    // pnl_array sera passé séparément comme matrice
};


/**
 * Classe principale pour les calculs de stratégie
 */
class StrategyCalculator {
public:
    /**
     * Calcule toutes les métriques d'une stratégie
     * 
     * @param options Vecteur de données d'options (structure plate)
     * @param signs Signes (+1 long, -1 short)
     * @param pnl_matrix Matrice des P&L (n_options x pnl_length)
     * @param prices Array des prix du sous-jacent
     * @param mixture Distribution de probabilité
     * @param average_mix Moyenne de la mixture (point de séparation left/right)
     * @param max_loss_left Perte max autorisée à gauche de average_mix
     * @param max_loss_right Perte max autorisée à droite de average_mix
     * @param max_premium_params Premium max autorisé
     * @param ouvert_gauche Nombre de puts shorts non couverts autorisés
     * @param ouvert_droite Nombre de calls shorts non couverts autorisés
     * @param min_premium_sell Premium minimum pour une vente
     * @param delta_min Delta minimum autorisé
     * @param delta_max Delta maximum autorisé
     * @param limit_left Left limit we accept to loose max loss left
     * @param limit_right Right limit where we accept to loose max loss right
     * @return std::optional<StrategyMetrics> - nullopt si invalide
     */
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
        double limit_right
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
        double& total_gamma,
        double& total_vega,
        double& total_theta,
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
    
    static void calculate_surfaces(
        const std::vector<double>& total_pnl,
        const std::vector<OptionData>& options,
        const std::vector<int>& signs,
        double dx,
        double& total_sigma_pnl
    );
};

} // namespace strategy
