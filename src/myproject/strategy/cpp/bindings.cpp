/**
 * Bindings pybind11 pour les calculs de stratégies
 * Expose les fonctions C++ à Python
 */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include "strategy_metrics.hpp"
#include "strategy_scoring.hpp"
#include <vector>
#include <array>
#include <iostream>
#include <map>
#include <mutex>

#ifdef _OPENMP
#include <omp.h>
#endif

namespace py = pybind11;

using namespace strategy;


// Structure pour stocker le cache des options côté C++
struct OptionsCache {
    std::vector<OptionData> options;
    std::vector<std::vector<double>> pnl_matrix;
    std::vector<double> prices;
    std::vector<double> mixture;  // Distribution de probabilité du sous-jacent
    double average_mix;  // Point de séparation left/right
    size_t n_options;
    size_t pnl_length;
    bool valid;
};

// Cache global (sera initialisé par Python)
static OptionsCache g_cache;

/**
 * Initialise le cache avec toutes les données des options
 */
void init_options_cache(      
    py::array_t<double> premiums,
    py::array_t<double> deltas,
    py::array_t<double> gammas,
    py::array_t<double> vegas,
    py::array_t<double> thetas,
    py::array_t<double> ivs,
    py::array_t<double> average_pnls,
    py::array_t<double> sigma_pnls,
    py::array_t<double> strikes,
    py::array_t<bool> is_calls,
    py::array_t<double> rolls,
    py::array_t<double> rolls_quarterly,
    py::array_t<double> rolls_sum,
    py::array_t<double> pnl_matrix,
    py::array_t<double> prices,
    py::array_t<double> mixture,
    double average_mix
) {
    auto prem_buf = premiums.unchecked<1>();
    auto delta_buf = deltas.unchecked<1>();
    auto gamma_buf = gammas.unchecked<1>();
    auto vega_buf = vegas.unchecked<1>();
    auto theta_buf = thetas.unchecked<1>();
    auto iv_buf = ivs.unchecked<1>();
    auto avg_pnl_buf = average_pnls.unchecked<1>();
    auto sigma_buf = sigma_pnls.unchecked<1>();
    auto strike_buf = strikes.unchecked<1>();
    auto is_call_buf = is_calls.unchecked<1>();
    auto rolls_buf = rolls.unchecked<1>();
    auto rolls_q_buf = rolls_quarterly.unchecked<1>();
    auto rolls_sum_buf = rolls_sum.unchecked<1>();
    auto pnl_buf = pnl_matrix.unchecked<2>();
    auto prices_buf = prices.unchecked<1>();
    auto mixture_buf = mixture.unchecked<1>();
    
    g_cache.n_options = prem_buf.shape(0);
    g_cache.pnl_length = prices_buf.shape(0);
    g_cache.average_mix = average_mix;
    
    g_cache.options.resize(g_cache.n_options);
    g_cache.pnl_matrix.resize(g_cache.n_options);
    g_cache.prices.resize(g_cache.pnl_length);
    
    for (size_t i = 0; i < g_cache.n_options; ++i) {
        g_cache.options[i].premium = prem_buf(i);
        g_cache.options[i].delta = delta_buf(i);
        g_cache.options[i].gamma = gamma_buf(i);
        g_cache.options[i].vega = vega_buf(i);
        g_cache.options[i].theta = theta_buf(i);
        g_cache.options[i].implied_volatility = iv_buf(i);
        g_cache.options[i].average_pnl = avg_pnl_buf(i);
        g_cache.options[i].sigma_pnl = sigma_buf(i);
        g_cache.options[i].strike = strike_buf(i);
        g_cache.options[i].is_call = is_call_buf(i);
        g_cache.options[i].roll = rolls_buf(i);
        g_cache.options[i].roll_quarterly = rolls_q_buf(i);
        g_cache.options[i].roll_sum = rolls_sum_buf(i);
        
        g_cache.pnl_matrix[i].resize(g_cache.pnl_length);
        for (size_t j = 0; j < g_cache.pnl_length; ++j) {
            g_cache.pnl_matrix[i][j] = pnl_buf(i, j);
        }
    }
    
    for (size_t i = 0; i < g_cache.pnl_length; ++i) {
        g_cache.prices[i] = prices_buf(i);
    }
    
    // Copier la mixture
    g_cache.mixture.resize(g_cache.pnl_length);
    for (size_t i = 0; i < g_cache.pnl_length; ++i) {
        g_cache.mixture[i] = mixture_buf(i);
    }
    
    g_cache.valid = true;
}

/**
 * Génère toutes les combinaisons inférieur à n_legs options, les score et retourne le top_n
 */
py::list process_combinations_batch_with_scoring(
    int max_legs,
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
    int top_n = 1000,
    py::dict custom_weights = py::dict()
) {
    if (!g_cache.valid || g_cache.n_options == 0) {
        throw std::runtime_error("Cache non initialisé. Appelez init_options_cache() d'abord.");
    }
    
    if (max_legs <= 0 || max_legs > static_cast<int>(g_cache.n_options)) {
        throw std::invalid_argument("n_legs invalide");
    }
    
    std::vector<ScoredStrategy> valid_strategies;
    valid_strategies.reserve(1000000); 
    
    for (int n_legs = 1; n_legs <= max_legs; ++n_legs) {
        size_t count_before = valid_strategies.size();''
        
        // ========== ÉTAPE 1: Pré-générer toutes les combinaisons d'indices ==========
        std::vector<std::vector<int>> all_combinations;
        all_combinations.reserve(10000);
        
        std::vector<int> c(n_legs, 0);
        do {
            all_combinations.push_back(c);
        } while (StrategyCalculator::next_combination(c, g_cache.n_options));
        
        const size_t n_combos = all_combinations.size();
        const int n_masks = 1 << n_legs;
        const size_t total_tasks = n_combos * n_masks;
        
        // ========== ÉTAPE 2: Traiter toutes les tâches EN PARALLÈLE ==========
        std::vector<ScoredStrategy> local_results;
        std::mutex mtx;
        const int64_t total_tasks_signed = static_cast<int64_t>(total_tasks);
        
        #pragma omp parallel
        {
            // Buffer local au thread pour collecter les résultats
            std::vector<ScoredStrategy> thread_results;
            thread_results.reserve(1000);
            
            #pragma omp for schedule(dynamic, 64) nowait
            for (int64_t task_id = 0; task_id < total_tasks_signed; ++task_id) {
                size_t combo_idx = static_cast<size_t>(task_id) / n_masks;
                int mask = static_cast<int>(task_id) % n_masks;
                
                const auto& indices = all_combinations[combo_idx];
                
                // Buffers locaux
                std::vector<OptionData> combo_options;
                std::vector<int> combo_signs;
                std::vector<std::vector<double>> combo_pnl;
                combo_options.reserve(n_legs);
                combo_signs.reserve(n_legs);
                combo_pnl.reserve(n_legs);

                // Construire la combinaison
                for (int i = 0; i < n_legs; ++i) {
                    int idx = indices[i];
                    int sgn = (mask & (1 << i)) ? 1 : -1;
                    combo_options.push_back(g_cache.options[idx]);
                    combo_signs.push_back(sgn);
                    combo_pnl.push_back(g_cache.pnl_matrix[idx]);
                }
            
                // Calculer les métriques
                auto result = StrategyCalculator::calculate(
                    combo_options, combo_signs, combo_pnl, g_cache.prices, g_cache.mixture,
                    g_cache.average_mix, max_loss_left, max_loss_right, max_premium_params,
                    ouvert_gauche, ouvert_droite, min_premium_sell, delta_min, delta_max, limit_left, limit_right
                );
                
                if (result.has_value()) {
                    const auto& metrics = result.value();
                    
                    ScoredStrategy strat;
                    strat.total_premium = metrics.total_premium;
                    strat.total_delta = metrics.total_delta;
                    strat.total_gamma = metrics.total_gamma;
                    strat.total_vega = metrics.total_vega;
                    strat.total_theta = metrics.total_theta;
                    strat.total_iv = metrics.total_iv;
                    strat.avg_implied_volatility = metrics.total_iv / n_legs;
                    strat.average_pnl = metrics.total_average_pnl;
                    strat.roll = metrics.total_roll;
                    strat.roll_quarterly = metrics.total_roll_quarterly;
                    strat.roll_sum = metrics.total_roll_sum;
                    strat.sigma_pnl = metrics.total_sigma_pnl;
                    strat.max_profit = metrics.max_profit;
                    strat.max_loss = std::min(metrics.max_loss_left, metrics.max_loss_right);
                    strat.max_loss_left = metrics.max_loss_left;
                    strat.max_loss_right = metrics.max_loss_right;
                    strat.min_profit_price = metrics.min_profit_price;
                    strat.max_profit_price = metrics.max_profit_price;
                    strat.profit_zone_width = metrics.profit_zone_width;
                    strat.call_count = metrics.call_count;
                    strat.put_count = metrics.put_count;
                    strat.breakeven_points = metrics.breakeven_points;
                    strat.total_pnl_array = metrics.total_pnl_array;
                    
                    strat.option_indices.reserve(n_legs);
                    strat.signs.reserve(n_legs);
                    for (int i = 0; i < n_legs; ++i) {
                        strat.option_indices.push_back(indices[i]);
                        strat.signs.push_back((mask & (1 << i)) ? 1 : -1);
                    }
                    
                    thread_results.push_back(std::move(strat));
                }
            }
            
            // Fusionner les résultats du thread (une seule fois par thread)
            {
                std::lock_guard<std::mutex> lock(mtx);
                valid_strategies.insert(valid_strategies.end(), 
                    std::make_move_iterator(thread_results.begin()),
                    std::make_move_iterator(thread_results.end()));
            }
        }
        
        size_t count_after = valid_strategies.size();
        std::cout << "n_legs=" << n_legs << " combos=" << n_combos 
                  << " tâches=" << total_tasks
                  << " valides=" << (count_after - count_before) << std::endl;
    }
    
    // ========== SCORING ET RANKING EN C++ ==========
    std::vector<MetricConfig> metrics;
    if (custom_weights.size() > 0) {

        metrics = StrategyScorer::create_default_metrics();
        for (auto& metric : metrics) {
            if (custom_weights.contains(metric.name.c_str())) {
                metric.weight = custom_weights[metric.name.c_str()].cast<double>();
            }
        }
    }
    
    std::vector<ScoredStrategy> ranked_strategies = StrategyScorer::score_and_rank(
        valid_strategies,  
        metrics,
        top_n
    );
    
    std::cout << "Scoring terminé" << ranked_strategies.size() << " top stratégies" << std::endl;
    
    // ========== FILTRE DES DOUBLONS EN C++ ==========
    std::cout << " Filtre doublons en cours (max " << top_n << " uniques)..." << std::endl;
    std::vector<ScoredStrategy> unique_strategies = StrategyScorer::remove_duplicates(ranked_strategies, 4, top_n);

    // ========== CONVERSION EN RÉSULTATS PYTHON ==========
    py::list results;

    
    for (const auto& strat : unique_strategies) {
        py::list indices_list;
        py::list signs_list;
        for (size_t i = 0; i < strat.option_indices.size(); ++i) {
            indices_list.append(strat.option_indices[i]);
            signs_list.append(strat.signs[i]);
        }
        
        py::dict metrics_dict;
        metrics_dict["total_premium"] = strat.total_premium;
        metrics_dict["total_delta"] = strat.total_delta;
        metrics_dict["total_gamma"] = strat.total_gamma;
        metrics_dict["total_vega"] = strat.total_vega;
        metrics_dict["total_theta"] = strat.total_theta;
        metrics_dict["total_iv"] = strat.total_iv;
        metrics_dict["avg_implied_volatility"] = strat.avg_implied_volatility;
        metrics_dict["average_pnl"] = strat.average_pnl;
        metrics_dict["total_average_pnl"] = strat.average_pnl;  // Alias pour compatibilité
        metrics_dict["total_roll"] = strat.roll;
        metrics_dict["total_roll_quarterly"] = strat.roll_quarterly;
        metrics_dict["total_roll_sum"] = strat.roll_sum;
        metrics_dict["sigma_pnl"] = strat.sigma_pnl;
        metrics_dict["total_sigma_pnl"] = strat.sigma_pnl;  // Alias pour compatibilité
        metrics_dict["max_profit"] = strat.max_profit;
        metrics_dict["max_loss"] = strat.max_loss;
        metrics_dict["max_loss_left"] = strat.max_loss_left;
        metrics_dict["max_loss_right"] = strat.max_loss_right;
        metrics_dict["min_profit_price"] = strat.min_profit_price;
        metrics_dict["max_profit_price"] = strat.max_profit_price;
        metrics_dict["profit_zone_width"] = strat.profit_zone_width;
        metrics_dict["call_count"] = strat.call_count;
        metrics_dict["put_count"] = strat.put_count;
        metrics_dict["breakeven_points"] = strat.breakeven_points;
        metrics_dict["score"] = strat.score;
        metrics_dict["rank"] = strat.rank;
        
        // Ajouter le pnl_array
        py::array_t<double> pnl_arr(strat.total_pnl_array.size());
        auto pnl_out = pnl_arr.mutable_unchecked<1>();
        for (size_t i = 0; i < strat.total_pnl_array.size(); ++i) {
            pnl_out(i) = strat.total_pnl_array[i];
        }
        metrics_dict["pnl_array"] = pnl_arr;
        
        results.append(py::make_tuple(indices_list, signs_list, metrics_dict));
    }
    
    return results;
}



/**
 * Wrapper Python-friendly pour calculate()
 * Convertit les arrays NumPy en structures C++
 */
py::object calculate_strategy_metrics(
    py::array_t<double> premiums,
    py::array_t<double> deltas,
    py::array_t<double> gammas,
    py::array_t<double> vegas,
    py::array_t<double> thetas,
    py::array_t<double> ivs,
    py::array_t<double> average_pnls,
    py::array_t<double> sigma_pnls,
    py::array_t<double> strikes,
    py::array_t<bool> is_calls,
    py::array_t<double> rolls,
    py::array_t<double> rolls_quarterly,
    py::array_t<double> rolls_sum,
    py::array_t<int> signs,
    py::array_t<double> pnl_matrix,  // 2D array (n_options x pnl_length)
    py::array_t<double> prices,
    py::array_t<double> mixture,
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
) {
    // Accès aux buffers
    auto prem_buf = premiums.unchecked<1>();
    auto delta_buf = deltas.unchecked<1>();
    auto gamma_buf = gammas.unchecked<1>();
    auto vega_buf = vegas.unchecked<1>();
    auto theta_buf = thetas.unchecked<1>();
    auto iv_buf = ivs.unchecked<1>();
    auto avg_pnl_buf = average_pnls.unchecked<1>();
    auto sigma_buf = sigma_pnls.unchecked<1>();
    auto strike_buf = strikes.unchecked<1>();
    auto is_call_buf = is_calls.unchecked<1>();
    auto rolls_buf = rolls.unchecked<1>();
    auto rolls_q_buf = rolls_quarterly.unchecked<1>();
    auto rolls_sum_buf = rolls_sum.unchecked<1>();
    auto signs_buf = signs.unchecked<1>();
    auto pnl_buf = pnl_matrix.unchecked<2>();
    auto prices_buf = prices.unchecked<1>();
    auto mixture_buf = mixture.unchecked<1>();
    
    const size_t n_options = prem_buf.shape(0);
    const size_t pnl_length = prices_buf.shape(0);
    
    // Construire les vecteurs C++
    std::vector<OptionData> options(n_options);
    std::vector<int> signs_vec(n_options);
    std::vector<std::vector<double>> pnl_matrix_vec(n_options);
    std::vector<double> prices_vec(pnl_length);
    std::vector<double> mixture_vec(pnl_length);
    
    for (size_t i = 0; i < n_options; ++i) {
        options[i].premium = prem_buf(i);
        options[i].delta = delta_buf(i);
        options[i].gamma = gamma_buf(i);
        options[i].vega = vega_buf(i);
        options[i].theta = theta_buf(i);
        options[i].implied_volatility = iv_buf(i);
        options[i].average_pnl = avg_pnl_buf(i);
        options[i].sigma_pnl = sigma_buf(i);
        options[i].strike = strike_buf(i);
        options[i].is_call = is_call_buf(i);
        options[i].roll = rolls_buf(i);
        options[i].roll_quarterly = rolls_q_buf(i);
        options[i].roll_sum = rolls_sum_buf(i);
        signs_vec[i] = signs_buf(i);
        
        pnl_matrix_vec[i].resize(pnl_length);
        for (size_t j = 0; j < pnl_length; ++j) {
            pnl_matrix_vec[i][j] = pnl_buf(i, j);
        }
    }
    
    for (size_t i = 0; i < pnl_length; ++i) {
        prices_vec[i] = prices_buf(i);
        mixture_vec[i] = mixture_buf(i);
    }
    
    auto result = StrategyCalculator::calculate(
        options, signs_vec, pnl_matrix_vec, prices_vec, mixture_vec,
        average_mix, max_loss_left, max_loss_right, max_premium_params,
        ouvert_gauche, ouvert_droite, min_premium_sell, delta_min, delta_max, limit_left, limit_right
    );
    
    if (!result.has_value()) {
        return py::none();
    }
    
    const auto& metrics = result.value();
    
    // Convertir en dictionnaire Python
    py::dict output;
    output["total_premium"] = metrics.total_premium;
    output["total_delta"] = metrics.total_delta;
    output["total_gamma"] = metrics.total_gamma;
    output["total_vega"] = metrics.total_vega;
    output["total_theta"] = metrics.total_theta;
    output["total_iv"] = metrics.total_iv;
    output["max_profit"] = metrics.max_profit;
    output["max_loss"] = metrics.max_loss;
    output["max_loss_left"] = metrics.max_loss_left;
    output["max_loss_right"] = metrics.max_loss_right;
    output["total_average_pnl"] = metrics.total_average_pnl;
    output["total_sigma_pnl"] = metrics.total_sigma_pnl;
    output["min_profit_price"] = metrics.min_profit_price;
    output["max_profit_price"] = metrics.max_profit_price;
    output["profit_zone_width"] = metrics.profit_zone_width;
    output["call_count"] = metrics.call_count;
    output["put_count"] = metrics.put_count;
    output["breakeven_points"] = metrics.breakeven_points;
    output["total_roll"] = metrics.total_roll;
    output["total_roll_quarterly"] = metrics.total_roll_quarterly;
    output["total_roll_sum"] = metrics.total_roll_sum;
    
    // Convertir le P&L array en NumPy
    py::array_t<double> pnl_arr(metrics.total_pnl_array.size());
    auto pnl_out = pnl_arr.mutable_unchecked<1>();
    for (size_t i = 0; i < metrics.total_pnl_array.size(); ++i) {
        pnl_out(i) = metrics.total_pnl_array[i];
    }
    output["pnl_array"] = pnl_arr;
    
    return output;
}


PYBIND11_MODULE(strategy_metrics_cpp, m) {
    m.doc() = "Module C++ optimisé pour les calculs de métriques de stratégies d'options";
    
    m.def("init_options_cache", &init_options_cache,
          R"pbdoc(
              Initialise le cache global avec toutes les données des options.
              Doit être appelé une seule fois avant process_combinations_batch.
          )pbdoc",
          py::arg("premiums"),
          py::arg("deltas"),
          py::arg("gammas"),
          py::arg("vegas"),
          py::arg("thetas"),
          py::arg("ivs"),
          py::arg("average_pnls"),
          py::arg("sigma_pnls"),
          py::arg("strikes"),
          py::arg("is_calls"),
          py::arg("rolls"),
          py::arg("rolls_quarterly"),
          py::arg("rolls_sum"),
          py::arg("pnl_matrix"),
          py::arg("prices"),
          py::arg("mixture"),
          py::arg("average_mix")
    );
    
    m.def("process_combinations_batch_with_scoring", &process_combinations_batch_with_scoring,
          R"pbdoc(
              Génère toutes les combinaisons de n_legs options avec SCORING et RANKING en C++.
              
              Retourne le top_n des meilleures stratégies selon un système de scoring multi-critères.
              Cette fonction est BEAUCOUP plus rapide que la version Python car tout le scoring
              est fait en C++ (pas de conversion Python pour chaque stratégie).
              
              Arguments:
                  n_legs: Nombre de legs par stratégie
                  max_loss_left: Perte max autorisée à gauche
                  max_loss_right: Perte max autorisée à droite
                  max_premium_params: Premium maximum autorisé
                  ouvert_gauche: Nombre de puts shorts non couverts autorisé
                  ouvert_droite: Nombre de calls shorts non couverts autorisé
                  min_premium_sell: Premium minimum pour vendre une option
                  delta_min: Delta minimum autorisé
                  delta_max: Delta maximum autorisé
                  limit_left: Prix limite gauche
                  limit_right: Prix limite droite
                  top_n: Nombre de meilleures stratégies à retourner (défaut: 10)
                  custom_weights: Dict optionnel de poids personnalisés (ex: {"average_pnl": 0.3})
                  
              Retourne:
                  Liste de tuples (indices, signs, metrics_dict) pour les top_n stratégies
                  metrics_dict contient maintenant 'score' et 'rank'
          )pbdoc",
          py::arg("n_legs"),
          py::arg("max_loss_left"),
          py::arg("max_loss_right"),
          py::arg("max_premium_params"),
          py::arg("ouvert_gauche"),
          py::arg("ouvert_droite"),
          py::arg("min_premium_sell"),
          py::arg("delta_min"),
          py::arg("delta_max"),
          py::arg("limit_left"),
          py::arg("limit_right"),
          py::arg("top_n") = 10,
          py::arg("custom_weights") = py::dict()
    );
    
    m.def("calculate_strategy_metrics", &calculate_strategy_metrics,
          R"pbdoc(
              Calcule toutes les métriques d'une stratégie d'options.
              
              Retourne None si la stratégie est invalide (ne passe pas les filtres),
              sinon retourne un dictionnaire avec toutes les métriques.
              
              Arguments:
                  premiums: Array des primes
                  deltas: Array des deltas
                  gammas: Array des gammas
                  vegas: Array des vegas
                  thetas: Array des thetas
                  ivs: Array des volatilités implicites
                  average_pnls: Array des P&L moyens
                  sigma_pnls: Array des écarts-types P&L
                  strikes: Array des strikes
                  is_calls: Array boolean (True=call, False=put)
                  rolls: Array des rolls moyens
                  rolls_quarterly: Array des rolls Q-1
                  rolls_sum: Array des rolls bruts
                  signs: Array des signes (+1=long, -1=short)
                  pnl_matrix: Matrice 2D des P&L (n_options x pnl_length)
                  prices: Array des prix du sous-jacent
                  mixture: Array de la mixture (densité de probabilité)
                  average_mix: Point de séparation left/right
                  max_loss_left: Perte max à gauche de average_mix
                  max_loss_right: Perte max à droite de average_mix
                  max_premium_params: Premium maximum autorisé
                  ouvert_gauche: Nombre de short puts - long puts autorisé
                  ouvert_droite: Nombre de short calls - long calls autorisé
                  min_premium_sell: Premium minimum pour vendre une option
                  delta_min: Delta minimum autorisé
                  delta_max: Delta maximum autorisé
                  
              Retourne:
                  None si invalide, dict des métriques sinon
          )pbdoc",
          py::arg("premiums"),
          py::arg("deltas"),
          py::arg("gammas"),
          py::arg("vegas"),
          py::arg("thetas"),
          py::arg("ivs"),
          py::arg("average_pnls"),
          py::arg("sigma_pnls"),
          py::arg("strikes"),
          py::arg("is_calls"),
          py::arg("rolls"),
          py::arg("rolls_quarterly"),
          py::arg("rolls_sum"),
          py::arg("signs"),
          py::arg("pnl_matrix"),
          py::arg("prices"),
          py::arg("mixture"),
          py::arg("average_mix"),
          py::arg("max_loss_left"),
          py::arg("max_loss_right"),
          py::arg("max_premium_params"),
          py::arg("ouvert_gauche"),
          py::arg("ouvert_droite"),
          py::arg("min_premium_sell"),
          py::arg("delta_min"),
          py::arg("delta_max"),
          py::arg("limit_left"),
          py::arg("limit_right")
    );
}
